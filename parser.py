"""
UFDR parser module.

Input:  a UFDR-style XML export (report.xml) + its media/ folder.
Output: a single normalized JSON file containing every record type,
        with media records enriched by type-specific metadata and a
        SHA-256 hash (for evidentiary integrity).

Supported media types: image, audio, document.
Document records may be an image (jpg/png/etc.) or a PDF; text extraction
for both happens later in ocr_transcribe.py.
"""

import xmltodict
import json
import hashlib
import wave
import os
from PIL import Image
from pypdf import PdfReader

BASE_DIR = "sample_ufdr"
XML_PATH = os.path.join(BASE_DIR, "report.xml")
OUTPUT_PATH = "parsed_output.json"


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


def read_pdf_metadata(path):
    reader = PdfReader(path)
    return {"format": "PDF", "page_count": len(reader.pages)}


PDF_EXTENSIONS = (".pdf",)


def as_list(x):
    """xmltodict returns a dict for a single child and a list for multiple
    children with the same tag - this normalizes both cases to a list."""
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
        if file_path.lower().endswith(PDF_EXTENSIONS):
            record["metadata"] = read_pdf_metadata(file_path)
        else:
            record["metadata"] = read_image_metadata(file_path)
        record["status"] = "PARSED"
    elif item["type"] == "video":
        record["status"] = "SKIPPED_VIDEO_NOT_IMPLEMENTED"
    else:
        record["status"] = f"UNKNOWN_TYPE:{item['type']}"

    return record


def main():
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
