"""
Cases API Route Endpoint for AI-ForenSight.

Provides endpoints to query forensic cases from the PostgreSQL database.
Reuses existing backend database connection implementation.
"""

from fastapi import APIRouter, HTTPException, Request, status
from psycopg.rows import dict_row

try:
    from ..database.connection import get_connection
except ImportError:
    from database.connection import get_connection

try:
    from ..database.audit import log_audit_event
except ImportError:
    from database.audit import log_audit_event


router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_cases(request: Request):
    """Retrieve all forensic case records from the PostgreSQL database."""
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT id, case_name, source_file, created_at FROM cases ORDER BY id ASC;"
                )
                cases = cursor.fetchall()
                
                # Record forensic access event
                log_audit_event(
                    action="CASES_LIST_VIEW",
                    resource_type="case",
                    details={"total_cases_returned": len(cases)},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return cases
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cases from database.",
        )
