"""
Calls API Route Endpoint for AI-ForenSight.

Provides endpoints to query call records from the PostgreSQL database.
Supports filtering by case_id.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from psycopg.rows import dict_row

try:
    from ..database.connection import get_connection
except ImportError:
    from database.connection import get_connection


router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_calls(case_id: Optional[int] = Query(None, description="Optional case ID to filter calls")):
    """
    Retrieve call records from the PostgreSQL database.
    Optionally filter by case_id.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                if case_id is not None:
                    cursor.execute(
                        "SELECT id, case_id, call_id, caller, callee, timestamp, duration_seconds, type "
                        "FROM calls WHERE case_id = %s ORDER BY id ASC;",
                        (case_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, case_id, call_id, caller, callee, timestamp, duration_seconds, type "
                        "FROM calls ORDER BY id ASC;"
                    )
                calls = cursor.fetchall()
                return calls
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve call records from database.",
        )
