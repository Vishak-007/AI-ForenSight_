"""
Immutable Forensic Audit Trail for AI-ForenSight.

Provides cryptographic hash-chained audit logging to ensure evidence chain-of-custody,
investigative accountability, and tamper detection.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from psycopg.rows import dict_row

try:
    from .connection import get_connection
except ImportError:
    from connection import get_connection

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def compute_entry_hash(
    prev_hash: str,
    timestamp: str,
    user_id: str,
    action: str,
    case_id: Optional[int],
    resource_type: Optional[str],
    resource_id: Optional[str],
    details_json: str,
) -> str:
    """Compute cryptographic SHA-256 hash for an audit log entry."""
    payload = f"{prev_hash}|{timestamp}|{user_id}|{action}|{case_id}|{resource_type}|{resource_id}|{details_json}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_audit_event(
    action: str,
    case_id: Optional[int] = None,
    user_id: str = "investigator",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[int]:
    """
    Append an immutable forensic audit record with cryptographic hash chaining.
    """
    try:
        details_json = json.dumps(details or {}, sort_keys=True)
        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT entry_hash FROM audit_logs ORDER BY id DESC LIMIT 1;")
                row = cursor.fetchone()
                prev_hash = row[0] if row and row[0] else GENESIS_HASH

                entry_hash = compute_entry_hash(
                    prev_hash=prev_hash,
                    timestamp=now,
                    user_id=user_id,
                    action=action,
                    case_id=case_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details_json=details_json,
                )

                cursor.execute(
                    """
                    INSERT INTO audit_logs (
                        case_id, user_id, action, resource_type, resource_id,
                        details, ip_address, user_agent, timestamp, prev_log_hash, entry_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        case_id,
                        user_id,
                        action,
                        resource_type,
                        resource_id,
                        details_json,
                        ip_address,
                        user_agent,
                        now,
                        prev_hash,
                        entry_hash,
                    ),
                )
                inserted_id = cursor.fetchone()[0]
                conn.commit()
                return inserted_id
    except Exception as e:
        print(f"[AUDIT LOG WARNING] Failed to record audit event '{action}': {e}")
        return None


def get_audit_trail(
    case_id: Optional[int] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve audit logs with optional filters."""
    query = (
        "SELECT id, case_id, user_id, action, resource_type, resource_id, "
        "details, ip_address, user_agent, timestamp, prev_log_hash, entry_hash "
        "FROM audit_logs WHERE 1=1"
    )
    params: List[Any] = []

    if case_id is not None:
        query += " AND case_id = %s"
        params.append(case_id)
    if user_id is not None:
        query += " AND user_id = %s"
        params.append(user_id)
    if action is not None:
        query += " AND action = %s"
        params.append(action)

    query += " ORDER BY id DESC LIMIT %s OFFSET %s;"
    params.extend([limit, offset])

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def verify_audit_trail_integrity() -> Dict[str, Any]:
    """
    Verify the cryptographic integrity of the entire audit log chain.
    Detects any unauthorized modification, insertion, or deletion of log rows.
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, case_id, user_id, action, resource_type, resource_id,
                       details, timestamp, prev_log_hash, entry_hash
                FROM audit_logs
                ORDER BY id ASC;
                """
            )
            rows = cursor.fetchall()

    if not rows:
        return {"status": "valid", "total_entries": 0, "message": "Audit trail is empty."}

    expected_prev_hash = GENESIS_HASH
    for row in rows:
        if row["prev_log_hash"] != expected_prev_hash:
            return {
                "status": "corrupted",
                "corrupted_at_id": row["id"],
                "reason": "Broken previous hash pointer (chain interrupted)",
                "expected_prev_hash": expected_prev_hash,
                "found_prev_hash": row["prev_log_hash"],
            }

        details_val = row["details"]
        if isinstance(details_val, str):
            details_json = details_val
        else:
            details_json = json.dumps(details_val or {}, sort_keys=True)

        ts_str = row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"])

        recomputed_hash = compute_entry_hash(
            prev_hash=row["prev_log_hash"],
            timestamp=ts_str,
            user_id=row["user_id"],
            action=row["action"],
            case_id=row["case_id"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            details_json=details_json,
        )

        if row["entry_hash"] != recomputed_hash:
            return {
                "status": "corrupted",
                "corrupted_at_id": row["id"],
                "reason": "Entry hash mismatch (data was tampered with)",
                "stored_hash": row["entry_hash"],
                "recomputed_hash": recomputed_hash,
            }

        expected_prev_hash = row["entry_hash"]

    return {
        "status": "verified",
        "total_entries": len(rows),
        "message": "All audit log entries are cryptographically intact and untampered.",
    }
