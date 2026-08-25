"""
Audit Logs API Route Endpoint for AI-ForenSight.

Provides endpoints to query the forensic audit trail and verify cryptographic chain integrity.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, status

try:
    from ..database.audit import get_audit_trail, verify_audit_trail_integrity
except ImportError:
    from database.audit import get_audit_trail, verify_audit_trail_integrity

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def list_audit_logs(
    case_id: Optional[int] = Query(None, description="Filter logs by case ID"),
    user_id: Optional[str] = Query(None, description="Filter logs by user ID"),
    action: Optional[str] = Query(None, description="Filter logs by action name"),
    limit: int = Query(100, ge=1, le=500, description="Max logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Retrieve filtered forensic audit logs."""
    try:
        logs = get_audit_trail(
            case_id=case_id,
            user_id=user_id,
            action=action,
            limit=limit,
            offset=offset,
        )
        return {"total": len(logs), "logs": logs}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch audit trail: {str(e)}",
        )


@router.get("/verify", status_code=status.HTTP_200_OK)
def verify_audit_log_chain():
    """
    Cryptographically verify the entire audit log chain.
    Ensures no records have been altered, added, or deleted since creation.
    """
    try:
        verification_result = verify_audit_trail_integrity()
        return verification_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit chain verification failed: {str(e)}",
        )
