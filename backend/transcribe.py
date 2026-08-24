"""
AI-ForenSight — Module: Audio Transcription (Whisper)

Reads parsed_output.json (produced by parser.py), finds every media record
of type "audio" that was successfully parsed, transcribes it locally with
faster-whisper, and writes transcripts_output.json.

No cloud calls. No internet needed after the model is downloaded once.

Run from inside the ufdr_prototype/ folder:
    python transcribe.py
"""

import json
import os
import sys

# Windows fix: onnxruntime and faster-whisper's av/ctranslate2 dependency
# both bundle their own copy of the Intel OpenMP runtime (libiomp5md.dll).
# Loading both triggers "OMP: Error #15: Initializing libiomp5md.dll, but
# found libiomp5md.dll already initialized." This must be set BEFORE those
# libraries are imported.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from faster_whisper import WhisperModel

# ---- Config ---------------------------------------------------------------

PARSED_INPUT_PATH = "parsed_output.json"
OUTPUT_PATH = "transcripts_output.json"
MEDIA_DIR = "sample_ufdr"          # audio files live under here, per parser.py
WHISPER_MODEL_SIZE = "base"        # "tiny" is faster/rougher if you need speed
WHISPER_DEVICE = "cpu"             # change to "cuda" if you have a GPU set up
WHISPER_COMPUTE_TYPE = "int8"      # good speed/accuracy tradeoff on CPU


def load_parsed_data(path):
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run parser.py first to generate it.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_audio_records(parsed_data):
    """Filter parsed media records down to successfully-parsed audio files."""
    media_records = parsed_data.get("media", [])
    audio_records = [
        m for m in media_records
        if m.get("type") == "audio" and m.get("status") == "PARSED"
    ]
    return audio_records


def resolve_media_path(record):
    """
    parser.py stores a filename/relative path per record — adjust the key
    below if your parsed_output.json uses a different field name
    (e.g. "path" instead of "filename").
    """
    filename = record.get("filename") or record.get("path")
    if filename is None:
        return None
    # If parser.py already stored a full relative path, don't double it up.
    if filename.startswith(MEDIA_DIR):
        return filename
    return os.path.join(MEDIA_DIR, filename)


def transcribe_all(audio_records, model):
    transcripts = []
    total = len(audio_records)

    for i, record in enumerate(audio_records, start=1):
        media_id = record.get("id")
        file_path = resolve_media_path(record)

        print(f"[{i}/{total}] Transcribing {media_id} ({file_path}) ...")

        if not file_path or not os.path.exists(file_path):
            print(f"  -> SKIPPED: file not found at {file_path}")
            continue

        segments, info = model.transcribe(file_path, beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments).strip()

        transcripts.append({
            "media_id": media_id,
            "text": text,
            "language": info.language,
        })

    return transcripts


def main():
    print("Loading parsed data...")
    parsed_data = load_parsed_data(PARSED_INPUT_PATH)

    audio_records = get_audio_records(parsed_data)
    print(f"Found {len(audio_records)} audio record(s) to transcribe.")

    if not audio_records:
        print("Nothing to transcribe. Writing empty output file.")
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump({"transcripts": []}, f, indent=2)
        return

    print(f"Loading Whisper model '{WHISPER_MODEL_SIZE}' "
          f"(device={WHISPER_DEVICE}, compute_type={WHISPER_COMPUTE_TYPE})...")
    model = WhisperModel(
        WHISPER_MODEL_SIZE,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
    )

    transcripts = transcribe_all(audio_records, model)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"transcripts": transcripts}, f, indent=2)

    print(f"\nDone. Wrote {len(transcripts)} transcript(s) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()