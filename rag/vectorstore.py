from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from rag.config import EMBEDDING_DIM, QDRANT_COLLECTION, QDRANT_URL


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection() -> None:
    client = get_client()
    if client.collection_exists(QDRANT_COLLECTION):
        return
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )


def upsert_points(points: list[PointStruct]) -> None:
    client = get_client()
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)


def search(vector: list[float], top_k: int) -> list[dict]:
    client = get_client()
    results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector,
        limit=top_k,
        with_payload=True,
    ).points
    return [{"score": r.score, **(r.payload or {})} for r in results]
