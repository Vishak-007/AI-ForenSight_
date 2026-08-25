"""
Media API Route Endpoint for AI-ForenSight.

Provides read-only endpoints to query media item records from the PostgreSQL database.
Supports filtering by case_id.
"""

import mimetypes
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from psycopg.rows import dict_row

try:
    from ..database.connection import get_connection
except ImportError:
    from database.connection import get_connection


router = APIRouter(prefix="/api/media", tags=["media"])


def _is_within_directory(base_dir: Path, target: Path) -> bool:
    """Ensure target resolves within base_dir to prevent storage_path traversal."""
    try:
        target.resolve().relative_to(base_dir.resolve())
        return True
    except ValueError:
        return False


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_media(case_id: Optional[int] = Query(None, description="Optional case ID to filter media items")):
    """
    Retrieve media item records from the PostgreSQL database.
    Optionally filter by case_id.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                if case_id is not None:
                    cursor.execute(
                        "SELECT id, case_id, media_id, type, timestamp, filename, storage_path, sha256, "
                        "file_size_bytes, associated_message_id, associated_call_id, status "
                        "FROM media WHERE case_id = %s ORDER BY id ASC;",
                        (case_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, case_id, media_id, type, timestamp, filename, storage_path, sha256, "
                        "file_size_bytes, associated_message_id, associated_call_id, status "
                        "FROM media ORDER BY id ASC;"
                    )
                media_items = cursor.fetchall()
                return media_items
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve media records from database.",
        )


@router.get("/{media_id}/file", status_code=status.HTTP_200_OK)
def get_media_file(media_id: int):
    """
    Stream the raw bytes of a media item's file from disk.

    Resolves the on-disk path as Path(case.source_file).parent / media.storage_path,
    validates it stays within the case's extracted directory, and returns it via
    FileResponse with a best-effort content-type guess.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT media.storage_path, media.filename, cases.source_file "
                    "FROM media JOIN cases ON cases.id = media.case_id "
                    "WHERE media.id = %s;",
                    (media_id,),
                )
                row = cursor.fetchone()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query media record from database.",
        )

    if row is None or not row.get("source_file") or not row.get("storage_path"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.")

    case_dir = Path(row["source_file"]).resolve().parent
    file_path = case_dir / row["storage_path"]

    if not _is_within_directory(case_dir, file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.")

    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.")

    content_type, _ = mimetypes.guess_type(row["filename"] or file_path.name)
    return FileResponse(path=file_path, media_type=content_type or "application/octet-stream")
