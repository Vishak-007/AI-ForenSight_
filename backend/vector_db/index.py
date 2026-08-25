"""Build/refresh the Qdrant semantic-search index from the pipeline's JSON outputs.

Usage (from the project root):
    python -m backend.vector_db.index
    python -m backend.vector_db.index --case-id DEV001

Reads parsed_output.json / ocr_output.json / transcripts_output.json /
image_analysis_output.json from backend/, embeds the searchable text fields
locally, and upserts them into Qdrant. Safe to re-run: point IDs are
deterministic (case_ref + source_type + business_id), so re-indexing the same
data overwrites the same points instead of duplicating them.

Does NOT require PostgreSQL. The payload carries the UFDR business IDs
(case_ref / media_id / business_id) needed to trace a result back to its
source record. The internal PostgreSQL row ids (cases.id, media.id,
messages.id, ...) only exist once this data has been imported into
PostgreSQL, so postgres_case_id / postgres_media_id / postgres_row_id are
left null here for a later enrichment step to fill in once the shared DB is
reachable.
"""

import argparse
import json
from typing import Optional

from qdrant_client.http import models as qmodels

from .config import QDRANT_COLLECTION
from .embedder import embed_texts, embedding_dimension
from .extractor import BACKEND_DIR, extract_records, load_case_ref
from .qdrant_store import ensure_collection, get_client, make_point_id


def run_indexing(case_id: Optional[str] = None) -> int:
    """Embeds and upserts all searchable records. Returns the point count."""

    with (BACKEND_DIR / "parsed_output.json").open("r", encoding="utf-8") as f:
        parsed = json.load(f)
    case_ref = load_case_ref(parsed, case_id)
    print(f"Case reference: {case_ref}")

    records = extract_records()
    print(f"Found {len(records)} searchable text record(s) across messages/OCR/transcripts/image analysis.")
    if not records:
        print("Nothing to index.")
        return 0

    print("Generating embeddings locally...")
    vectors = embed_texts([r.text for r in records])
    dim = embedding_dimension()

    client = get_client()
    ensure_collection(client, dim)

    points = [
        qmodels.PointStruct(
            id=make_point_id(case_ref, record.source_type, record.business_id),
            vector=vector,
            payload={
                "case_ref": case_ref,
                "postgres_case_id": None,
                "source_type": record.source_type,
                "source_table": record.source_table,
                "business_id": record.business_id,
                "media_id": record.media_id,
                "postgres_media_id": None,
                "postgres_row_id": None,
                "text": record.text,
                **record.metadata,
            },
        )
        for record, vector in zip(records, vectors)
    ]

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"Upserted {len(points)} point(s) into '{QDRANT_COLLECTION}'.")

    by_type: dict[str, int] = {}
    for r in records:
        by_type[r.source_type] = by_type.get(r.source_type, 0) + 1
    for source_type, count in by_type.items():
        print(f"  - {source_type}: {count}")

    return len(points)


def main() -> None:
    parser = argparse.ArgumentParser(description="Index forensic JSON outputs into Qdrant")
    parser.add_argument(
        "--case-id",
        help="Case reference to tag every point with "
             "(defaults to parsed_output.json's device_info.device_id)",
    )
    args = parser.parse_args()
    run_indexing(args.case_id)


if __name__ == "__main__":
    main()
