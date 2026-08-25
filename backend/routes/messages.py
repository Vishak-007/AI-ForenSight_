"""
Messages API Route Endpoint for AI-ForenSight.

Provides endpoints to query message records from the PostgreSQL database.
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


router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def get_messages(
    request: Request,
    case_id: Optional[int] = Query(None, description="Optional case ID to filter messages"),
):
    """
    Retrieve message records from the PostgreSQL database.
    Optionally filter by case_id.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                if case_id is not None:
                    cursor.execute(
                        "SELECT id, case_id, message_id, sender, receiver, timestamp, text "
                        "FROM messages WHERE case_id = %s ORDER BY id ASC;",
                        (case_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, case_id, message_id, sender, receiver, timestamp, text "
                        "FROM messages ORDER BY id ASC;"
                    )
                messages = cursor.fetchall()
                
                log_audit_event(
                    case_id=case_id,
                    action="MESSAGES_VIEWED",
                    resource_type="message",
                    details={"messages_returned": len(messages)},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return messages
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message records from database.",
        )
