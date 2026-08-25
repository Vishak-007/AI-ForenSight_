"""
Devices API Route Endpoint for AI-ForenSight.

Provides endpoints to query device records from the PostgreSQL database.
Supports filtering by case_id.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from psycopg.rows import dict_row

try:
    from ..database.connection import get_connection
except ImportError:
    from database.connection import get_connection


router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_devices(case_id: Optional[int] = Query(None, description="Optional case ID to filter devices")):
    """
    Retrieve device records from the PostgreSQL database.
    Optionally filter by case_id.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                if case_id is not None:
                    cursor.execute(
                        "SELECT id, case_id, device_id, imei, extraction_date "
                        "FROM devices WHERE case_id = %s ORDER BY id ASC;",
                        (case_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, case_id, device_id, imei, extraction_date "
                        "FROM devices ORDER BY id ASC;"
                    )
                devices = cursor.fetchall()
                return devices
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device records from database.",
        )
