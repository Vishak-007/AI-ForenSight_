"""
Devices API Route Endpoint for AI-ForenSight.

Provides endpoints to query device records from the PostgreSQL database.
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


router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_devices(
    request: Request,
    case_id: Optional[int] = Query(None, description="Optional case ID to filter devices"),
):
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
                
                log_audit_event(
                    case_id=case_id,
                    action="DEVICES_VIEWED",
                    resource_type="device",
                    details={"devices_returned": len(devices)},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return devices
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device records from database.",
        )
