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
    with wave.open(path, "rb") as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return {
            "duration_seconds": round(frames / float(rate), 2),
            "channels": f.getnchannels(),
            "sample_rate": rate,
        }


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
        # Not implemented yet — deliberately skipped for today's scope.
        record["status"] = "SKIPPED_VIDEO_NOT_IMPLEMENTED"
    else:
        record["status"] = f"UNKNOWN_TYPE:{item['type']}"

    return record


def main():
    global BASE_DIR, XML_PATH
    args = parse_args()
    BASE_DIR = args.input_dir
    XML_PATH = os.path.join(BASE_DIR, "report.xml")

    with open(XML_PATH, "r", encoding="utf-8") as f:
        raw = xmltodict.parse(f.read())

    report = raw["ufdr_report"]

    parsed = {
        "device_info": report.get("device_info", {}),
        "messages": as_list(report.get("messages", {}).get("message")),
        "calls": as_list(report.get("calls", {}).get("call")),
        "contacts": as_list(report.get("contacts", {}).get("contact")),
        "media": [
            parse_media_item(item)
            for item in as_list(report.get("media", {}).get("media_item"))
        ],
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
