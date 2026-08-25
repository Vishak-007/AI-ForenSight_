"""
OCR Results API Route Endpoint for AI-ForenSight.

Provides read-only endpoints to query OCR text extraction records from the PostgreSQL database.
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


router = APIRouter(prefix="/api/ocr-results", tags=["ocr-results"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_ocr_results(
    request: Request,
    case_id: Optional[int] = Query(None, description="Optional case ID to filter OCR results"),
):
    """
    Retrieve OCR text extraction records from the PostgreSQL database.
    Optionally filter by case_id via JOIN with media table.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                if case_id is not None:
                    cursor.execute(
                        "SELECT ocr_results.id, ocr_results.media_id, ocr_results.text "
                        "FROM ocr_results JOIN media ON media.id = ocr_results.media_id "
                        "WHERE media.case_id = %s ORDER BY ocr_results.id ASC;",
                        (case_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, media_id, text FROM ocr_results ORDER BY id ASC;"
                    )
                ocr_records = cursor.fetchall()
                
                log_audit_event(
                    case_id=case_id,
                    action="OCR_RESULTS_VIEWED",
                    resource_type="ocr",
                    details={"ocr_records_returned": len(ocr_records)},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return ocr_records
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OCR results from database.",
        )
