"""
AI-ForenSight - Module: Tanglish -> English Translation (Step 3)

Reads ocr_output.json (produced by ocr_transcribe.py), translates each
document's transcript_text from Tanglish/code-mixed Tamil into fluent
English via the local translation/ pipeline, and writes
translated_output.json containing both the original transcript and the
final English sentence, plus a per-stage trace for audit.

No cloud calls. Model weights (spaCy, NLLB, grammar-correction) download
from Hugging Face/spaCy once on first run; everything after that runs
fully offline, same as ocr_transcribe.py and transcribe.py.

Run from inside the project folder:
    python translate.py
"""

import json
import logging
import os
import sys

from translation import translate_transcript_verbose
from translation.errors import TranslationDependencyError
from translation.logging_utils import configure_logging, get_logger

# ---- Config ---------------------------------------------------------------

OCR_INPUT_PATH = "ocr_output.json"
OUTPUT_PATH = "translated_output.json"

logger = get_logger(__name__)


def load_ocr_data(path):
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run ocr_transcribe.py first to generate it.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_translatable_documents(ocr_data):
    """Filter out documents with empty/whitespace-only transcripts."""
    documents = ocr_data.get("documents", [])
    return [d for d in documents if (d.get("transcript_text") or "").strip()]


def translate_all(documents):
    translated = []
    total = len(documents)

    for i, doc in enumerate(documents, start=1):
        media_id = doc.get("media_id")
        print(f"[{i}/{total}] Translating {media_id} ({doc.get('filename')}) ...")

        result = translate_transcript_verbose(doc["transcript_text"])

        translated.append({
            "media_id": media_id,
            "filename": doc.get("filename"),
            "raw_transcript": result.raw_transcript,
            "final_english": result.final_english,
            "translation_trace": [t.as_dict() for t in result.trace],
            "file_metadata": doc.get("file_metadata", {}),
        })

    return translated


def main():
    configure_logging(logging.INFO)

    print("Loading OCR data...")
    ocr_data = load_ocr_data(OCR_INPUT_PATH)

    documents = get_translatable_documents(ocr_data)
    skipped = len(ocr_data.get("documents", [])) - len(documents)
    print(f"Found {len(documents)} document(s) with transcript text to translate"
          + (f" ({skipped} skipped: empty transcript)." if skipped else "."))

    try:
        translated_documents = translate_all(documents)
    except TranslationDependencyError as exc:
        print(f"\n{exc}")
        sys.exit(1)

    output = {
        "folder_metadata": ocr_data.get("folder_metadata"),
        "documents": translated_documents,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Wrote {len(translated_documents)} translated document(s) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
