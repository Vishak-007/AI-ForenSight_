"""
UFDR parser prototype.

Input:  a UFDR-style XML export (report.xml) + its media/ folder.
Output: a single normalized JSON file containing every record type,
        with media records enriched by type-specific metadata and a
        SHA-256 hash (so tampering can be detected later — this is the
        "evidentiary integrity" hook, cheap to add now, expensive to
        bolt on later).

Supported media types right now: image, audio, document.
Video is intentionally NOT handled yet — see the `video` branch below,
which just records that it was seen and skipped. Wiring it up later is
the same pattern as audio, just with a video-specific metadata reader
(e.g. moviepy or ffprobe) instead of `wave`.
"""

import argparse
import xmltodict
import json
import hashlib
import wave
import os
from PIL import Image

BASE_DIR = "sample_ufdr"
XML_PATH = os.path.join(BASE_DIR, "report.xml")
OUTPUT_PATH = "parsed_output.json"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", default=BASE_DIR,
                    help=f"folder containing report.xml and media/ (default: {BASE_DIR!r})")
    return p.parse_args()


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def read_image_metadata(path):
    with Image.open(path) as img:
        return {"width": img.width, "height": img.height, "format": img.format}


def read_audio_metadata(path):
    """Only raw WAV/RIFF is actually readable here (stdlib `wave` doesn't
    decode compressed formats). Real-world voice notes are very often mp4/
    m4a/aac containers (e.g. WhatsApp saves them as .mp4) -- for anything
    wave can't open, fall back to just the extension rather than crashing
    the whole parse over one file's sidecar metadata. transcribe.py (Whisper)
    is what actually reads the audio content later; this is best-effort."""
    try:
        with wave.open(path, "rb") as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return {
                "duration_seconds": round(frames / float(rate), 2),
                "channels": f.getnchannels(),
                "sample_rate": rate,
            }
    except (wave.Error, EOFError):
        return {"ext": os.path.splitext(path)[1].lower().lstrip(".")}


def read_document_metadata(path):
    """PNG/JPEG documents get image metadata; anything else (e.g. PDF)
    just gets its file extension recorded — no PDF page-count reader
    is wired up yet."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in ("png", "jpg", "jpeg"):
        try:
            with Image.open(path) as img:
                return {"width": img.width, "height": img.height, "format": img.format, "ext": ext}
        except Exception:
            pass
    return {"ext": ext}


def read_video_metadata(path):
    """Extract technical and playback metadata for video evidence."""
    try:
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {"ext": os.path.splitext(path)[1].lower().lstrip(".")}
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = round(total_frames / fps, 2) if fps > 0 else 0.0
        cap.release()
        return {
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "duration_seconds": duration,
            "total_frames": total_frames,
            "ext": os.path.splitext(path)[1].lower().lstrip("."),
        }
    except Exception:
        return {"ext": os.path.splitext(path)[1].lower().lstrip(".")}


def as_list(x):
    """xmltodict returns a dict for a single child and a list for multiple
    children with the same tag — this normalizes both cases to a list."""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def parse_media_item(item):
    file_path = os.path.join(BASE_DIR, item["filename"])
    record = {
        "id": item["id"],
        "type": item["type"],
        "timestamp": item.get("timestamp"),
        "filename": item["filename"],
        "associated_message_id": item.get("associated_message_id"),
        "associated_call_id": item.get("associated_call_id"),
    }

    if not os.path.exists(file_path):
        record["status"] = "MISSING_FILE"
        return record

    record["sha256"] = sha256_of_file(file_path)
    record["file_size_bytes"] = os.path.getsize(file_path)

    if item["type"] == "image":
        record["metadata"] = read_image_metadata(file_path)
        record["status"] = "PARSED"
    elif item["type"] == "audio":
        record["metadata"] = read_audio_metadata(file_path)
        record["status"] = "PARSED"
    elif item["type"] == "document":
        record["metadata"] = read_document_metadata(file_path)
        record["status"] = "PARSED"
    elif item["type"] == "video":
        record["metadata"] = read_video_metadata(file_path)
        record["status"] = "PARSED"
    else:
        record["status"] = f"UNKNOWN_TYPE:{item['type']}"

    return record


def extract_report_schema(report):
    metadata = report.get("metadata") or {}
    device_info = {
        "device_id": metadata.get("case_number") or metadata.get("device_name") or "UNKNOWN_DEVICE",
        "imei": None,
        "extraction_date": None,
    }

    contacts = [
        {"id": c.get("@id"), "name": c.get("name"), "phone": c.get("phone")}
        for c in as_list((report.get("contacts") or {}).get("contact"))
    ]

    calls = []
    for c in as_list((report.get("calls") or {}).get("call")):
        call_type = (c.get("@type") or "").lower()
        number = c.get("@number")
        calls.append({
            "id": c.get("@id"),
            "caller": number if call_type == "incoming" else None,
            "callee": number if call_type == "outgoing" else None,
            "timestamp": c.get("@timestamp"),
            "duration_seconds": c.get("@duration"),
            "type": call_type or None,
        })


    messages = []
    media_raw = []
    media_counter = 0

    for chat in as_list((report.get("chats") or {}).get("chat")):
        chat_messages = as_list(chat.get("message"))
        counterpart = next(
            (m.get("@sender") for m in chat_messages if m.get("@sender") and m.get("@sender") != "self"),
            None,
        )

        for m in chat_messages:
            sender = m.get("@sender")
            message_id = m.get("@id")
            timestamp = m.get("@timestamp")

            messages.append({
                "id": message_id,
                "sender": sender,
                "receiver": counterpart if sender == "self" else "self",
                "timestamp": timestamp,
                "text": m.get("body"),
            })

            for attachment in as_list(m.get("attachment")):
                media_counter += 1
                media_raw.append({
                    "id": f"MED{media_counter:03d}",
                    "type": attachment.get("@type"),
                    "timestamp": timestamp,
                    "filename": attachment.get("#text"),
                    "associated_message_id": message_id,
                    "associated_call_id": None,
                })

    return device_info, messages, calls, contacts, media_raw


def main():
    global BASE_DIR, XML_PATH
    args = parse_args()
    BASE_DIR = args.input_dir
    XML_PATH = os.path.join(BASE_DIR, "report.xml")

    with open(XML_PATH, "r", encoding="utf-8") as f:
        raw = xmltodict.parse(f.read())

    if "ufdr_report" in raw:
        report = raw["ufdr_report"]
        device_info = report.get("device_info", {})
        messages = as_list(report.get("messages", {}).get("message"))
        calls = as_list(report.get("calls", {}).get("call"))
        contacts = as_list(report.get("contacts", {}).get("contact"))
        media_raw = as_list(report.get("media", {}).get("media_item"))
    elif "report" in raw:
        device_info, messages, calls, contacts, media_raw = extract_report_schema(raw["report"])
    else:
        root_key = next(iter(raw), "<empty>")
        raise SystemExit(
            f"ERROR: unrecognized XML root element '<{root_key}>' in {XML_PATH} -- "
            f"expected '<ufdr_report>' or '<report>'."
        )

    parsed = {
        "device_info": device_info,
        "messages": messages,
        "calls": calls,
        "contacts": contacts,
        "media": [parse_media_item(item) for item in media_raw],
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)

    print(f"Parsed device: {parsed['device_info'].get('device_id')}")
    print(f"  Messages: {len(parsed['messages'])}")
    print(f"  Calls:    {len(parsed['calls'])}")
    print(f"  Contacts: {len(parsed['contacts'])}")
    print(f"  Media:    {len(parsed['media'])}")
    for m in parsed["media"]:
        print(f"    - {m['id']} ({m['type']}): {m['status']}")
        if m["status"] == "PARSED":
            print(f"        hash: {m['sha256'][:16]}...  metadata: {m['metadata']}")
    print(f"\nFull output written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
