"""
Media API Route Endpoint for AI-ForenSight.

Provides read-only endpoints to query media item records from the PostgreSQL database.
Supports filtering by case_id.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, status
from psycopg.rows import dict_row

try:
    from ..database.connection import get_connection
except ImportError:
    from database.connection import get_connection

try:
    from ..database.audit import log_audit_event
except ImportError:
    from database.audit import log_audit_event


router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_media(
    request: Request,
    case_id: Optional[int] = Query(None, description="Optional case ID to filter media items"),
):
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
                
                log_audit_event(
                    case_id=case_id,
                    action="MEDIA_VIEWED",
                    resource_type="media",
                    details={"media_items_returned": len(media_items)},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return media_items
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve media records from database.",
        )
