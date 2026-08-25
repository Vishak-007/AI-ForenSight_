"""Semantic search CLI over the Qdrant forensic index.

Usage (from the project root):
    python -m backend.vector_db.search "messages discussing suspicious activity"
    python -m backend.vector_db.search "suspicious activity" --top 10 --case-id DEV001
"""

import argparse
from typing import Optional

from qdrant_client.http import models as qmodels

from .config import QDRANT_COLLECTION
from .embedder import embed_query
from .qdrant_store import get_client


def semantic_search(query: str, top_k: int = 5, case_ref: Optional[str] = None) -> list[dict]:
    client = get_client()
    query_vector = embed_query(query)

    query_filter = None
    if case_ref:
        query_filter = qmodels.Filter(
            must=[qmodels.FieldCondition(key="case_ref", match=qmodels.MatchValue(value=case_ref))]
        )

    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        query_filter=query_filter,
    )

    results = []
    for hit in response.points:
        payload = hit.payload or {}
        results.append({
            "score": hit.score,
            "source_type": payload.get("source_type"),
            "source_table": payload.get("source_table"),
            "case_ref": payload.get("case_ref"),
            "postgres_case_id": payload.get("postgres_case_id"),
            "media_id": payload.get("media_id"),
            "business_id": payload.get("business_id"),
            "postgres_row_id": payload.get("postgres_row_id"),
            "text": payload.get("text"),
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic search over the forensic Qdrant index")
    parser.add_argument("query")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--case-id", help="Restrict results to a single case_ref")
    args = parser.parse_args()

    results = semantic_search(args.query, top_k=args.top, case_ref=args.case_id)
    if not results:
        print("No results.")
        return

    for i, r in enumerate(results, start=1):
        print(f"\n[{i}] score={r['score']:.4f}  {r['source_type']} ({r['source_table']})")
        print(f"    case_ref={r['case_ref']}  media_id={r['media_id']}  business_id={r['business_id']}")
        print(f"    postgres_row_id={r['postgres_row_id']}")
        print(f"    text: {r['text'][:200]}")


if __name__ == "__main__":
    main()
