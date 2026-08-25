"""
Cases API Route Endpoint for AI-ForenSight.

Provides endpoints to query forensic cases from the PostgreSQL database.
Reuses existing backend database connection implementation.
"""

from fastapi import APIRouter, HTTPException, status
from psycopg.rows import dict_row

try:
    from ..database.connection import get_connection
except ImportError:
    from database.connection import get_connection


router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_cases():
    """Retrieve all forensic case records from the PostgreSQL database."""
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT id, case_name, source_file, created_at FROM cases ORDER BY id ASC;"
                )
                cases = cursor.fetchall()
                return cases
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cases from database.",
        )
