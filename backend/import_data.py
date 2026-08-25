"""Import existing UFDR JSON outputs into PostgreSQL."""

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .database.connection import get_connection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def resolve_path(value: str) -> Path:
    """Resolve paths from either the current directory or project root."""

    path = Path(value).expanduser()
    if path.is_absolute() and path.exists():
        return path
    candidates = [path, PROJECT_ROOT / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise ValueError(f"JSON file not found: {value}")


def load_json(value: str) -> dict[str, Any]:
    path = resolve_path(value)
    with path.open("r", encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def required_text(record: dict[str, Any], key: str, record_type: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{record_type} requires a non-empty {key}")
    return value.strip()


def parse_timestamp(value: Any, field: str, required: bool = False) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ValueError(f"{field} is required")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} is not a valid ISO timestamp: {value}") from error


def parse_nonnegative_int(value: Any, field: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
        if not math.isfinite(number) or number < 0 or not number.is_integer():
            raise ValueError
        return int(number)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a non-negative integer") from error


def parse_confidence(value: Any) -> float:
    try:
        number = float(value)
        if not math.isfinite(number) or not 0 <= number <= 1:
            raise ValueError
        return number
    except (TypeError, ValueError) as error:
        raise ValueError("confidence must be a number between 0 and 1") from error


def validate_sha256(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValueError("sha256 must be exactly 64 hexadecimal characters")
    return value.lower()


def rows(data: Any, name: str) -> list[dict[str, Any]]:
    if data is None:
        return []
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"{name} must be an array of objects")
    return data


def find_case(cursor: Any, case_name: str, source_file: str) -> tuple[int, bool]:
    cursor.execute(
        """
        SELECT id FROM cases
        WHERE case_name = %s AND source_file IS NOT DISTINCT FROM %s
        """,
        (case_name, source_file),
    )
    existing = cursor.fetchone()
    if existing:
        return existing[0], False
    cursor.execute(
        """
        INSERT INTO cases (case_name, source_file)
        VALUES (%s, %s) RETURNING id
        """,
        (case_name, source_file),
    )
    return cursor.fetchone()[0], True


def import_data(
    case_name: str,
    source_file: str,
    parsed_path: str,
    ocr_path: str | None = None,
    transcripts_path: str | None = None,
    image_analysis_path: str | None = None,
) -> tuple[int, dict[str, int], list[str]]:
    parsed = load_json(parsed_path)
    ocr = load_json(ocr_path) if ocr_path else {}
    transcripts = load_json(transcripts_path) if transcripts_path else {}
    image_analysis = load_json(image_analysis_path) if image_analysis_path else {}
    counts = {
        "Cases": 0,
        "Devices": 0,
        "Contacts": 0,
        "Messages": 0,
        "Calls": 0,
        "Media": 0,
        "OCR results": 0,
        "Transcriptions": 0,
        "Image analyses": 0,
        "Image tags": 0,
    }
    skipped: list[str] = []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            case_id, case_created = find_case(cursor, case_name, source_file)
            counts["Cases"] = int(case_created)

            device = parsed.get("device_info")
            if device is not None:
                device_id = required_text(device, "device_id", "device_info")
                extraction_date = parse_timestamp(device.get("extraction_date"), "extraction_date")
                cursor.execute(
                    """
                    INSERT INTO devices (case_id, device_id, imei, extraction_date)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (case_id, device_id) DO UPDATE SET
                        imei = EXCLUDED.imei, extraction_date = EXCLUDED.extraction_date
                    """,
                    (case_id, device_id, device.get("imei"), extraction_date),
                )
                counts["Devices"] += 1

            for item in rows(parsed.get("contacts", []), "contacts"):
                contact_id = required_text(item, "id", "contact")
                cursor.execute(
                    """
                    INSERT INTO contacts (case_id, contact_id, name, phone)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (case_id, contact_id) DO UPDATE SET
                        name = EXCLUDED.name, phone = EXCLUDED.phone
                    """,
                    (case_id, contact_id, item.get("name"), item.get("phone")),
                )
                counts["Contacts"] += 1

            for item in rows(parsed.get("messages", []), "messages"):
                message_id = required_text(item, "id", "message")
                cursor.execute(
                    """
                    INSERT INTO messages (case_id, message_id, sender, receiver, timestamp, text)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (case_id, message_id) DO UPDATE SET
                        sender = EXCLUDED.sender, receiver = EXCLUDED.receiver,
                        timestamp = EXCLUDED.timestamp, text = EXCLUDED.text
                    """,
                    (case_id, message_id, item.get("sender"), item.get("receiver"),
                     parse_timestamp(item.get("timestamp"), "message timestamp"), item.get("text")),
                )
                counts["Messages"] += 1

            for item in rows(parsed.get("calls", []), "calls"):
                call_id = required_text(item, "id", "call")
                cursor.execute(
                    """
                    INSERT INTO calls (case_id, call_id, caller, callee, timestamp,
                                       duration_seconds, type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (case_id, call_id) DO UPDATE SET
                        caller = EXCLUDED.caller, callee = EXCLUDED.callee,
                        timestamp = EXCLUDED.timestamp, duration_seconds = EXCLUDED.duration_seconds,
                        type = EXCLUDED.type
                    """,
                    (case_id, call_id, item.get("caller"), item.get("callee"),
                     parse_timestamp(item.get("timestamp"), "call timestamp"),
                     parse_nonnegative_int(item.get("duration_seconds"), "duration_seconds"),
                     item.get("type")),
                )
                counts["Calls"] += 1

            media_ids: dict[str, int] = {}
            for item in rows(parsed.get("media", []), "media"):
                media_id = required_text(item, "id", "media")
                associated_message_id = item.get("associated_message_id") or None
                associated_call_id = item.get("associated_call_id") or None
                if associated_message_id:
                    cursor.execute("SELECT 1 FROM messages WHERE case_id = %s AND message_id = %s",
                                   (case_id, associated_message_id))
                    if cursor.fetchone() is None:
                        skipped.append(f"media {media_id}: unresolved message {associated_message_id}; association cleared")
                        associated_message_id = None
                if associated_call_id:
                    cursor.execute("SELECT 1 FROM calls WHERE case_id = %s AND call_id = %s",
                                   (case_id, associated_call_id))
                    if cursor.fetchone() is None:
                        skipped.append(f"media {media_id}: unresolved call {associated_call_id}; association cleared")
                        associated_call_id = None
                cursor.execute(
                    """
                    INSERT INTO media (case_id, media_id, type, timestamp, filename, storage_path,
                                       sha256, file_size_bytes, associated_message_id,
                                       associated_call_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (case_id, media_id) DO UPDATE SET
                        type = EXCLUDED.type, timestamp = EXCLUDED.timestamp,
                        filename = EXCLUDED.filename, storage_path = EXCLUDED.storage_path,
                        sha256 = EXCLUDED.sha256, file_size_bytes = EXCLUDED.file_size_bytes,
                        associated_message_id = EXCLUDED.associated_message_id,
                        associated_call_id = EXCLUDED.associated_call_id, status = EXCLUDED.status
                    RETURNING id
                    """,
                    (case_id, media_id, item.get("type"), parse_timestamp(item.get("timestamp"), "media timestamp"),
                     item.get("filename"), required_text(item, "filename", "media"),
                     validate_sha256(item.get("sha256")), parse_nonnegative_int(item.get("file_size_bytes"), "file_size_bytes"),
                     associated_message_id, associated_call_id, item.get("status")),
                )
                media_ids[media_id] = cursor.fetchone()[0]
                counts["Media"] += 1

            def media_reference(media_id: Any, kind: str) -> int | None:
                if not isinstance(media_id, str) or not media_id.strip():
                    skipped.append(f"{kind}: missing media_id")
                    return None
                if media_id not in media_ids:
                    cursor.execute("SELECT id FROM media WHERE case_id = %s AND media_id = %s", (case_id, media_id))
                    found = cursor.fetchone()
                    if found is None:
                        skipped.append(f"{kind} {media_id}: unresolved media reference")
                        return None
                    media_ids[media_id] = found[0]
                return media_ids[media_id]

            for item in rows(ocr.get("documents", []), "documents"):
                media_pk = media_reference(item.get("media_id"), "OCR result")
                if media_pk is None:
                    continue
                text = item.get("transcript_text")
                if not isinstance(text, str):
                    skipped.append(f"OCR result {item.get('media_id')}: transcript_text is not text")
                    continue
                cursor.execute("SELECT id FROM ocr_results WHERE media_id = %s ORDER BY id LIMIT 1", (media_pk,))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("UPDATE ocr_results SET text = %s WHERE id = %s", (text, existing[0]))
                else:
                    cursor.execute("INSERT INTO ocr_results (media_id, text) VALUES (%s, %s)", (media_pk, text))
                counts["OCR results"] += 1

            for item in rows(transcripts.get("transcripts", []), "transcripts"):
                media_pk = media_reference(item.get("media_id"), "transcription")
                if media_pk is None:
                    continue
                text = item.get("text")
                if not isinstance(text, str):
                    skipped.append(f"transcription {item.get('media_id')}: text is not text")
                    continue
                language = item.get("language")
                cursor.execute(
                    "SELECT id FROM transcriptions WHERE media_id = %s AND language IS NOT DISTINCT FROM %s ORDER BY id LIMIT 1",
                    (media_pk, language),
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("UPDATE transcriptions SET text = %s WHERE id = %s", (text, existing[0]))
                else:
                    cursor.execute("INSERT INTO transcriptions (media_id, text, language) VALUES (%s, %s, %s)",
                                   (media_pk, text, language))
                counts["Transcriptions"] += 1

            for item in rows(image_analysis.get("images", []), "images"):
                media_pk = media_reference(item.get("media_id"), "image analysis")
                if media_pk is None:
                    continue
                metadata = item.get("metadata") or {}
                if not isinstance(metadata, dict):
                    skipped.append(f"image analysis {item.get('media_id')}: metadata is not an object")
                    continue
                width = parse_nonnegative_int(metadata.get("width"), "image width")
                height = parse_nonnegative_int(metadata.get("height"), "image height")
                face_count = parse_nonnegative_int(item.get("face_count"), "face_count")
                cursor.execute("""
                    INSERT INTO image_analysis (media_id, width, height, format, context, face_count)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (media_id) DO UPDATE SET width = EXCLUDED.width,
                        height = EXCLUDED.height, format = EXCLUDED.format,
                        context = EXCLUDED.context, face_count = EXCLUDED.face_count
                    """, (media_pk, width, height, metadata.get("format"), item.get("context"), face_count))
                counts["Image analyses"] += 1
                tags = item.get("tags") or {}
                if not isinstance(tags, dict):
                    skipped.append(f"image tags {item.get('media_id')}: tags is not an object")
                    continue
                for tag, confidence in tags.items():
                    if not isinstance(tag, str) or not tag.strip():
                        skipped.append(f"image tags {item.get('media_id')}: empty tag")
                        continue
                    try:
                        confidence_value = parse_confidence(confidence)
                    except ValueError as error:
                        skipped.append(f"image tag {tag} ({item.get('media_id')}): {error}")
                        continue
                    cursor.execute("""
                        INSERT INTO image_tags (media_id, tag, confidence) VALUES (%s, %s, %s)
                        ON CONFLICT (media_id, tag) DO UPDATE SET confidence = EXCLUDED.confidence
                        """, (media_pk, tag.strip(), confidence_value))
                    counts["Image tags"] += 1
    return case_id, counts, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import UFDR JSON outputs into PostgreSQL")
    parser.add_argument("--case-name", required=True)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--parsed", required=True)
    parser.add_argument("--ocr")
    parser.add_argument("--transcripts")
    parser.add_argument("--image-analysis")
    args = parser.parse_args()
    try:
        case_id, counts, skipped = import_data(args.case_name, args.source_file, args.parsed,
                                                args.ocr, args.transcripts, args.image_analysis)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(f"Import failed and was rolled back: {error}")
        raise SystemExit(1) from error
    print("Import successful.\n")
    print(f"Case: {args.case_name}\n")
    print(f"CASE_ID={case_id}")
    print("Inserted/updated:")
    for label, count in counts.items():
        print(f"{label}: {count}")
    if skipped:
        print("\nSkipped records:")
        for reason in skipped:
            print(f"- {reason}")


if __name__ == "__main__":
    main()