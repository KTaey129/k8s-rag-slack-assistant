import httpx

from graph.flow import answer_question


def process_question(question: str, response_url: str) -> None:
    result = answer_question(question)

    text = result["answer"]
    if result["sources"]:
        text += "\n\n_Sources: " + ", ".join(result["sources"]) + "_"

    httpx.post(
        response_url,
        json={"response_type": "in_channel", "text": text},
        timeout=10,
    )
