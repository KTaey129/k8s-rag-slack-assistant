"""Ingest markdown docs into Qdrant: read -> chunk -> embed -> upsert.

Run with: uv run python -m rag.ingest
"""

import uuid
from pathlib import Path

from qdrant_client.models import PointStruct

from rag.chunking import chunk_markdown
from rag.config import DOCS_DIR
from rag.embeddings import embed_texts
from rag.vectorstore import ensure_collection, upsert_points

BATCH_SIZE = 64


def iter_chunks():
    docs_dir = Path(DOCS_DIR)
    if not docs_dir.exists():
        raise SystemExit(
            f"{docs_dir} not found — run `uv run python scripts/fetch_k8s_docs.py` first."
        )

    for path in docs_dir.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        source = str(path.relative_to(docs_dir))
        for chunk in chunk_markdown(text, source=source):
            if len(chunk.text) < 40:  # skip near-empty fragments (nav stubs, etc.)
                continue
            yield chunk


def main() -> None:
    ensure_collection()

    batch_texts: list[str] = []
    batch_payloads: list[dict] = []
    total = 0

    def flush():
        nonlocal total
        if not batch_texts:
            return
        vectors = embed_texts(batch_texts)
        points = [
            PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)
            for vector, payload in zip(vectors, batch_payloads)
        ]
        upsert_points(points)
        total += len(points)
        batch_texts.clear()
        batch_payloads.clear()

    for chunk in iter_chunks():
        batch_texts.append(chunk.text)
        batch_payloads.append(
            {"text": chunk.text, "source": chunk.source, "heading": chunk.heading}
        )
        if len(batch_texts) >= BATCH_SIZE:
            flush()
            print(f"  ...{total} chunks ingested")

    flush()
    print(f"Done. {total} chunks ingested into Qdrant collection.")


if __name__ == "__main__":
    main()
