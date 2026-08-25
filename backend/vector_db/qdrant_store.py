"""Qdrant connection, collection management, and the deterministic point-ID scheme."""

import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from .config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION

# Fixed namespace so uuid5(...) is stable across processes/runs.
POINT_NAMESPACE = uuid.UUID("6f6a1e2d-6b8a-4f0e-9f1a-1a2b3c4d5e6f")


def get_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection(client: QdrantClient, vector_size: int, collection_name: str = QDRANT_COLLECTION) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        return
    print(f"Creating Qdrant collection '{collection_name}' (dim={vector_size})...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
    )


def make_point_id(case_ref: str, source_type: str, business_id: str) -> str:
    """Deterministic UUID5 so re-indexing the same source record upserts the
    same point instead of creating a duplicate."""
    key = f"{case_ref}|{source_type}|{business_id}"
    return str(uuid.uuid5(POINT_NAMESPACE, key))
