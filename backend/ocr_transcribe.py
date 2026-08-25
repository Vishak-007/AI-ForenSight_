"""
AI-ForenSight - Module: Document OCR

Reads parsed_output.json (produced by parser.py), finds every media record
of type "document" that was successfully parsed, OCRs it locally with
Tesseract, and writes ocr_output.json containing each document's transcript
plus metadata about the folder the extraction came from.

No cloud calls. Everything runs offline once Tesseract OCR is installed.

Run from inside the project folder:
    python ocr_transcribe.py
"""

import argparse
import json
import os
import sys
import shutil

import pymupdf
import pytesseract
from PIL import Image

# ---- Config ---------------------------------------------------------------

PARSED_INPUT_PATH = "parsed_output.json"
OUTPUT_PATH = "ocr_output.json"
MEDIA_DIR = "sample_ufdr"          # document files live under here, per parser.py
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", default=MEDIA_DIR,
                    help=f"folder containing the media/ referenced by parsed_output.json (default: {MEDIA_DIR!r})")
    return p.parse_args()

if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
elif shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")


def load_parsed_data(path):
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run parser.py first to generate it.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_document_records(parsed_data):
    """Filter parsed media records down to successfully-parsed documents."""
    media_records = parsed_data.get("media", [])
    return [
        m for m in media_records
        if m.get("type") == "document" and m.get("status") == "PARSED"
    ]


def resolve_media_path(record):
    filename = record.get("filename") or record.get("path")
    if filename is None:
        return None
    if filename.startswith(MEDIA_DIR):
        return filename
    return os.path.join(MEDIA_DIR, filename)


def ocr_image_file(path):
    with Image.open(path) as img:
        return pytesseract.image_to_string(img).strip()


def ocr_pdf_file(path):
    """Render each PDF page to an image with PyMuPDF, then OCR each page."""
    page_texts = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            page_texts.append(pytesseract.image_to_string(img).strip())
    return "\n\n".join(page_texts).strip()


def ocr_document(path):
    try:
        if path.lower().endswith(".pdf"):
            return ocr_pdf_file(path)
        return ocr_image_file(path)
    except pytesseract.TesseractNotFoundError:
        print(f"  -> WARNING: Tesseract executable not found. Skipping OCR for {path}.")
        return "[OCR Skipped: Tesseract OCR not installed on host system]"


def compute_folder_metadata(folder_path):
    file_count = 0
    total_size_bytes = 0
    last_modified = 0.0

    for root, _dirs, files in os.walk(folder_path):
        for name in files:
            file_path = os.path.join(root, name)
            file_count += 1
            total_size_bytes += os.path.getsize(file_path)
            last_modified = max(last_modified, os.path.getmtime(file_path))

    return {
        "folder_path": folder_path,
        "file_count": file_count,
        "total_size_bytes": total_size_bytes,
        "last_modified": (
            __import__("datetime").datetime.fromtimestamp(last_modified).isoformat()
            if last_modified else None
        ),
    }


def transcribe_all(document_records):
    documents = []
    total = len(document_records)

    for i, record in enumerate(document_records, start=1):
        media_id = record.get("id")
        file_path = resolve_media_path(record)

        print(f"[{i}/{total}] OCR-ing {media_id} ({file_path}) ...")

        if not file_path or not os.path.exists(file_path):
            print(f"  -> SKIPPED: file not found at {file_path}")
            continue

        text = ocr_document(file_path)

        documents.append({
            "media_id": media_id,
            "filename": record.get("filename"),
            "transcript_text": text,
            "file_metadata": {
                "sha256": record.get("sha256"),
                "file_size_bytes": record.get("file_size_bytes"),
                **record.get("metadata", {}),
            },
        })

    return documents


def main():
    global MEDIA_DIR
    args = parse_args()
    MEDIA_DIR = args.input_dir

    print("Loading parsed data...")
    parsed_data = load_parsed_data(PARSED_INPUT_PATH)

    document_records = get_document_records(parsed_data)
    print(f"Found {len(document_records)} document record(s) to OCR.")

    folder_metadata = compute_folder_metadata(MEDIA_DIR)

    documents = transcribe_all(document_records)

    output = {
        "folder_metadata": folder_metadata,
        "documents": documents,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone. Wrote {len(documents)} document transcript(s) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
