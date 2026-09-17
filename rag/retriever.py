from rag.config import RETRIEVAL_TOP_K
from rag.embeddings import embed_query
from rag.vectorstore import search


def retrieve(question: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
    vector = embed_query(question)
    return search(vector, top_k=top_k)
