"""
Contacts API Route Endpoint for AI-ForenSight.

Provides endpoints to query contact records from the PostgreSQL database.
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


router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_contacts(
    request: Request,
    case_id: Optional[int] = Query(None, description="Optional case ID to filter contacts"),
):
    """
    Retrieve contact records from the PostgreSQL database.
    Optionally filter by case_id.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                if case_id is not None:
                    cursor.execute(
                        "SELECT id, case_id, contact_id, name, phone "
                        "FROM contacts WHERE case_id = %s ORDER BY id ASC;",
                        (case_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, case_id, contact_id, name, phone "
                        "FROM contacts ORDER BY id ASC;"
                    )
                contacts = cursor.fetchall()
                
                log_audit_event(
                    case_id=case_id,
                    action="CONTACTS_VIEWED",
                    resource_type="contact",
                    details={"contacts_returned": len(contacts)},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return contacts
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve contact records from database.",
        )
