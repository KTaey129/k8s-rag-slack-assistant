# k8s-rag-slack-assistant

A Slack-triggered RAG assistant that answers questions about Kubernetes,
built as a real backend system (queue, worker, vector store) rather than
a notebook demo.

**Status:** scaffolded, not yet deployed. Eval numbers and the live link
will be added once the retrieval pipeline is measured (see Roadmap).

## Architecture

```
Slack (/k8s slash command)
      │  HTTPS POST (Slack signs the request)
      ▼
n8n Webhook  ── verifies Slack signature, forwards payload ──▶  FastAPI /ingest
                                                                       │
                                                          enqueues job │ (internal shared-secret auth)
                                                                       ▼
                                                                 Redis queue
                                                                       │
                                                                       ▼
                                                              RQ Worker (consumer)
                                                                       │
                                                                       ▼
                                                        LangGraph flow: retrieve → decide → generate
                                                            │                              │
                                                            ▼                              ▼
                                              Qdrant (embedded k8s docs)          Claude (Anthropic)
                                                                       │
                                                     POST answer back to Slack response_url
```

**Why each piece is there, not just what it is:**

- **n8n** is the public-facing webhook + router. It's the layer that changes
  if the trigger changes (Slack today, a different source later) without
  touching the FastAPI service.
- **FastAPI `/ingest`** only enqueues work and acks immediately — Slack
  requires a response within 3 seconds, and the actual RAG pipeline
  (retrieval + LLM call) takes longer than that.
- **Redis + RQ** decouples the fast "acknowledge" path from the slow
  "answer" path, and means a burst of Slack requests queues up instead of
  taking the API down.
- **LangGraph** makes retrieve → decide → generate an explicit graph with a
  real branch (insufficient-context vs. generate), not a linear script.
- **Qdrant** is a dedicated vector store rather than an in-memory list, so
  it survives restarts and scales past a toy dataset.

## Design decision: signature verification happens at n8n, not FastAPI

Slack signs requests with an HMAC over the *raw* request body. Once n8n
receives that webhook and re-serializes the JSON before forwarding it,
the raw body Slack signed no longer matches what FastAPI receives — so
verifying Slack's signature has to happen in n8n, at the internet-facing
edge. FastAPI instead trusts a shared secret header (`INTERNAL_SHARED_SECRET`)
because `/ingest` is never exposed to the internet directly, only reachable
from n8n on the internal network. See [api/security.py](api/security.py).

## Setup

### 1. Environment

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY and generate INTERNAL_SHARED_SECRET:
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Fetch the dataset (Kubernetes docs)

```bash
uv run python scripts/fetch_k8s_docs.py
```

### 3. Start infra + services

```bash
docker compose up -d redis qdrant
uv run python -m rag.ingest        # chunk + embed + upsert into Qdrant
docker compose up                  # or run api/worker locally, see below
```

To run the API and worker outside Docker while iterating:

```bash
uv run uvicorn api.main:app --reload
uv run python -m worker.run_worker
```

### 4. Slack app (manual, one-time — do this yourself at api.slack.com)

1. Create an app at https://api.slack.com/apps → "From scratch".
2. **Slash Commands** → create `/k8s`, Request URL = your n8n webhook's
   public URL (`https://<your-n8n-host>/webhook/slack-k8s`). Use `ngrok`
   or similar while developing locally.
3. **Basic Information** → copy the **Signing Secret** into n8n's
   `INTERNAL_SHARED_SECRET`-adjacent Slack-verification step (see note
   above — verification lives in n8n, not this repo's env).
4. Install the app to your workspace, invite the bot to a channel, run
   `/k8s how do liveness probes work?`.

### 5. n8n workflow

Import [n8n/workflow.json](n8n/workflow.json) into your running n8n
instance (Workflows → Import from File). It defines: Slack Webhook →
Forward to FastAPI. You'll still need to add a Slack-signature-verification
step in n8n before the forward node (a Code node checking the HMAC) — not
included in the JSON yet, since it depends on your n8n version's crypto
node availability.

## Roadmap (per the study plan this project follows)

- [ ] Hand-written 100–200 question eval set over the Kubernetes docs
- [ ] Retrieval metrics (hit rate, MRR) + validated LLM-as-judge
- [ ] Baseline → change one thing → re-measure, 4-5 iterations, numbers in this README
- [ ] Agent-trajectory eval once tool-calling is added
- [ ] Kubernetes manifests (`infra/k8s/`) — deploying an assistant about
      Kubernetes, on Kubernetes, once the app is proven stable via
      docker-compose
- [ ] Public deployment + structured logging + rate limiting

## Repo layout

```
api/        FastAPI app — /ingest endpoint, internal-secret auth, queue enqueue
worker/     RQ worker + the task that runs the graph and replies to Slack
graph/      LangGraph flow: retrieve -> decide -> generate
rag/        chunking, embeddings, Qdrant client, ingestion script
scripts/    one-off scripts (fetching the k8s docs dataset)
n8n/        importable n8n workflow definition
data/       ingested docs (gitignored)
```
