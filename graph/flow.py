"""LangGraph flow: retrieve -> (insufficient context | generate).

This is the "AI flow management" piece from the architecture note — LangGraph
isn't doing anything exotic here, it's just making the retrieve/decide/generate
sequence an explicit, inspectable graph instead of a chain of function calls
buried in the worker.
"""

from typing import TypedDict

import anthropic
from langgraph.graph import END, StateGraph

from rag.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from rag.retriever import retrieve

MIN_RELEVANCE_SCORE = 0.35

SYSTEM_PROMPT = """You are a Kubernetes documentation assistant. Answer the \
user's question using ONLY the provided context chunks from the official \
Kubernetes docs. If the context doesn't contain the answer, say so plainly \
instead of guessing. Cite the source file for each claim like [source.md]."""


class FlowState(TypedDict):
    question: str
    chunks: list[dict]
    answer: str


def retrieve_node(state: FlowState) -> FlowState:
    chunks = retrieve(state["question"])
    return {**state, "chunks": chunks}


def has_sufficient_context(state: FlowState) -> str:
    chunks = state["chunks"]
    if not chunks or chunks[0]["score"] < MIN_RELEVANCE_SCORE:
        return "insufficient"
    return "sufficient"


def insufficient_context_node(state: FlowState) -> FlowState:
    return {
        **state,
        "answer": (
            "I couldn't find anything in the Kubernetes docs that confidently "
            "answers that. Try rephrasing, or it might be out of scope for this assistant."
        ),
    }


def assemble_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[{c['source']}] ({c.get('heading') or 'top of doc'})\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def generate_node(state: FlowState) -> FlowState:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    context = assemble_context(state["chunks"])

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {state['question']}",
            }
        ],
    )
    answer = "".join(block.text for block in response.content if block.type == "text")
    return {**state, "answer": answer}


def build_graph():
    graph = StateGraph(FlowState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("insufficient_context", insufficient_context_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve")
    graph.add_conditional_edges(
        "retrieve",
        has_sufficient_context,
        {"insufficient": "insufficient_context", "sufficient": "generate"},
    )
    graph.add_edge("insufficient_context", END)
    graph.add_edge("generate", END)

    return graph.compile()


_compiled_graph = None


def answer_question(question: str) -> dict:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()

    result = _compiled_graph.invoke({"question": question, "chunks": [], "answer": ""})
    return {"answer": result["answer"], "sources": sorted({c["source"] for c in result["chunks"]})}
