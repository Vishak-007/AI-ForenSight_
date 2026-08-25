"""
Image Tags API Route Endpoint for AI-ForenSight.

Provides read-only endpoints to query image evidentiary tags from the PostgreSQL database.
Supports filtering by case_id via JOIN with media.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from psycopg.rows import dict_row

try:
    from ..database.connection import get_connection
except ImportError:
    from database.connection import get_connection


router = APIRouter(prefix="/api/image-tags", tags=["image-tags"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_image_tags(case_id: Optional[int] = Query(None, description="Optional case ID to filter image tags")):
    """
    Retrieve image evidentiary tag records from the PostgreSQL database.
    Optionally filter by case_id via JOIN with media table.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                if case_id is not None:
                    cursor.execute(
                        "SELECT image_tags.id, image_tags.media_id, image_tags.tag, image_tags.confidence "
                        "FROM image_tags JOIN media ON media.id = image_tags.media_id "
                        "WHERE media.case_id = %s ORDER BY image_tags.id ASC;",
                        (case_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, media_id, tag, confidence FROM image_tags ORDER BY id ASC;"
                    )
                tags = cursor.fetchall()
                return tags
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve image tags from database.",
        )
