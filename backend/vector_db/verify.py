"""Verification checklist for the Qdrant vector DB phase.

Runs read-only/idempotent checks. It does NOT re-run parser.py /
ocr_transcribe.py / transcribe.py / image_extractor.py (that would
regenerate and overwrite the existing JSON outputs) -- pipeline-safety is
checked statically instead, by confirming those four files were not touched
by the vector_db integration.

Usage (from the project root):
    python -m backend.vector_db.verify
"""

from pathlib import Path

from .config import QDRANT_COLLECTION
from .index import run_indexing
from .qdrant_store import get_client
from .search import semantic_search

BACKEND_DIR = Path(__file__).resolve().parents[1]
PIPELINE_FILES = ["parser.py", "ocr_transcribe.py", "transcribe.py", "image_extractor.py"]


def check_connection():
    client = get_client()
    client.get_collections()
    print("[OK] Qdrant connection works.")
    return client


def check_collection_exists(client) -> None:
    names = {c.name for c in client.get_collections().collections}
    assert QDRANT_COLLECTION in names, f"Collection '{QDRANT_COLLECTION}' not found -- run index.py first."
    print(f"[OK] Collection '{QDRANT_COLLECTION}' exists.")


def check_vectors_present(client) -> int:
    count = client.count(collection_name=QDRANT_COLLECTION, exact=True).count
    assert count > 0, "Collection has zero points -- run index.py first."
    print(f"[OK] Collection has {count} point(s).")
    return count


def check_no_duplicates_on_reindex(client) -> None:
    before = client.count(collection_name=QDRANT_COLLECTION, exact=True).count
    run_indexing()
    after = client.count(collection_name=QDRANT_COLLECTION, exact=True).count
    assert before == after, f"Point count changed on re-index ({before} -> {after}); point IDs aren't stable."
    print(f"[OK] Re-indexing is idempotent ({after} point(s), unchanged).")


def check_search_returns_linked_results() -> None:
    results = semantic_search("suspicious activity", top_k=3)
    assert results, "Semantic search returned no results."
    required_keys = {"source_type", "source_table", "case_ref", "media_id", "business_id", "text"}
    for r in results:
        missing = required_keys - r.keys()
        assert not missing, f"Result missing linking fields: {missing}"
    print(f"[OK] Semantic search returned {len(results)} result(s) with PostgreSQL-linking metadata.")
    for r in results:
        print(f"     score={r['score']:.4f} {r['source_type']} ({r['source_table']}) business_id={r['business_id']}")


def check_pipeline_untouched() -> None:
    for name in PIPELINE_FILES:
        content = (BACKEND_DIR / name).read_text(encoding="utf-8")
        assert "vector_db" not in content, f"{name} references vector_db -- it should stay independent."
    print("[OK] Extraction pipeline files are untouched/independent of vector_db.")


def main() -> None:
    print("== Vector DB verification ==")
    client = check_connection()
    check_collection_exists(client)
    check_vectors_present(client)
    check_no_duplicates_on_reindex(client)
    check_search_returns_linked_results()
    check_pipeline_untouched()
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
