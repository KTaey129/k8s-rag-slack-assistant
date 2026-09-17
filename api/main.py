from fastapi import Depends, FastAPI
from pydantic import BaseModel

from api.queue import enqueue_question
from api.security import require_internal_secret

app = FastAPI(title="k8s-rag-slack-assistant")


class SlackCommandPayload(BaseModel):
    text: str
    response_url: str
    user_id: str
    channel_id: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest", dependencies=[Depends(require_internal_secret)])
def ingest(payload: SlackCommandPayload) -> dict:
    """Called by n8n after it receives Slack's slash command webhook.

    Must respond within Slack's 3-second ack window. The actual RAG work
    happens asynchronously in the worker; this just enqueues it and returns
    an immediate ephemeral acknowledgement for n8n to relay back to Slack.
    """
    if not payload.text.strip():
        return {
            "response_type": "ephemeral",
            "text": "Ask me something about Kubernetes, e.g. `/k8s how do liveness probes work?`",
        }

    enqueue_question(payload.text, payload.response_url)

    return {
        "response_type": "ephemeral",
        "text": f"🔎 Looking into the Kubernetes docs for: _{payload.text}_",
    }
