"""
Image Analysis API Route Endpoint for AI-ForenSight.

Provides read-only endpoints to query image analysis records from the PostgreSQL database.
Supports filtering by case_id via JOIN with media.
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


router = APIRouter(prefix="/api/image-analysis", tags=["image-analysis"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_image_analysis(
    request: Request,
    case_id: Optional[int] = Query(None, description="Optional case ID to filter image analysis"),
):
    """
    Retrieve image analysis records from the PostgreSQL database.
    Optionally filter by case_id via JOIN with media table.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                if case_id is not None:
                    cursor.execute(
                        "SELECT image_analysis.id, image_analysis.media_id, image_analysis.width, "
                        "image_analysis.height, image_analysis.format, image_analysis.context, image_analysis.face_count "
                        "FROM image_analysis JOIN media ON media.id = image_analysis.media_id "
                        "WHERE media.case_id = %s ORDER BY image_analysis.id ASC;",
                        (case_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, media_id, width, height, format, context, face_count "
                        "FROM image_analysis ORDER BY id ASC;"
                    )
                analyses = cursor.fetchall()
                
                log_audit_event(
                    case_id=case_id,
                    action="IMAGE_ANALYSIS_VIEWED",
                    resource_type="image_analysis",
                    details={"analyses_returned": len(analyses)},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return analyses
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve image analysis records from database.",
        )
