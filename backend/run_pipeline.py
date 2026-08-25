"""
Automated end-to-end pipeline runner for AI-ForenSight.

Sequentially executes:
  1. parser.py           -> parsed_output.json
  2. ocr_transcribe.py   -> ocr_output.json
  3. translate.py        -> translated_output.json (Tanglish -> English, best-effort)
  4. transcribe.py       -> transcripts_output.json
  5. image_extractor.py  -> image_analysis_output.json
  6. import_data.py      -> PostgreSQL Database Import
  7. vector_db.index     -> Qdrant semantic-search index (best-effort)

Ensures database import is ONLY invoked if all extraction JSON outputs
are generated successfully. Stages 1-4 all read from --source-file's
parent directory (report.xml + its media/ folder), so pointing
--source-file at an uploaded case's extracted report.xml makes the whole
pipeline operate on that case instead of the bundled sample_ufdr data.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automated UFDR Extraction & PostgreSQL Import Pipeline"
    )
    parser.add_argument(
        "--case-name",
        default="Sample Case",
        help="Case name for database import (default: 'Sample Case')",
    )
    parser.add_argument(
        "--source-file",
        default="sample_ufdr/report.xml",
        help="Path to source UFDR XML file (default: 'sample_ufdr/report.xml')",
    )
    parser.add_argument(
        "--parsed-output",
        default="parsed_output.json",
        help="Output path for UFDR parsed JSON (default: 'parsed_output.json')",
    )
    parser.add_argument(
        "--ocr-output",
        default="ocr_output.json",
        help="Output path for OCR JSON (default: 'ocr_output.json')",
    )
    parser.add_argument(
        "--translated-output",
        default="translated_output.json",
        help="Output path for Tanglish->English translation JSON (default: 'translated_output.json')",
    )
    parser.add_argument(
        "--transcripts-output",
        default="transcripts_output.json",
        help="Output path for transcripts JSON (default: 'transcripts_output.json')",
    )
    parser.add_argument(
        "--image-analysis-output",
        default="image_analysis_output.json",
        help="Output path for image analysis JSON (default: 'image_analysis_output.json')",
    )
    parser.add_argument(
        "--video-analysis-output",
        default="video_analysis_output.json",
        help="Output path for video analysis JSON (default: 'video_analysis_output.json')",
    )
    return parser.parse_args()


def run_stage(
    stage_name: str,
    cmd: list[str],
    expected_output: Path | None = None,
    cwd: Path = BACKEND_DIR,
    capture: bool = False,
    fatal: bool = True,
) -> str | None:
    print(f"\n==================================================")
    print(f"  STARTING STAGE: {stage_name}")
    print(f"==================================================")
    print(f"Running command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True if capture else None)
    if capture:
        # Still surface the subprocess's own output on the parent's stdout,
        # since capture_output otherwise swallows it silently.
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)

    if result.returncode != 0:
        print(f"\nERROR: Stage '{stage_name}' failed with return code {result.returncode}.")
        if fatal:
            print("Pipeline execution halted.")
            sys.exit(result.returncode)
        print("Continuing anyway -- this stage is best-effort, not required for case data to be usable.")
        return result.stdout if capture else None

    if expected_output:
        resolved_output = BACKEND_DIR / expected_output if not expected_output.is_absolute() else expected_output
        if not resolved_output.exists() or resolved_output.stat().st_size == 0:
            print(f"\nERROR: Expected output file '{resolved_output}' was not created or is empty.")
            print("Pipeline execution halted. Database import will NOT be executed.")
            sys.exit(1)
        print(f"Verified output generated: {resolved_output.name} ({resolved_output.stat().st_size} bytes)")

    print(f"STAGE COMPLETED SUCCESSFULLY: {stage_name}\n")
    return result.stdout if capture else None


def main():
    args = parse_args()

    parsed_path = Path(args.parsed_output)
    ocr_path = Path(args.ocr_output)
    translated_path = Path(args.translated_output)
    transcripts_path = Path(args.transcripts_output)
    image_analysis_path = Path(args.image_analysis_output)
    video_analysis_path = Path(args.video_analysis_output)

    py_exe = sys.executable

    # Every extraction stage reads report.xml/media from this directory --
    # defaults to sample_ufdr/, but points at an uploaded case's extracted
    # folder when --source-file was given one (see upload.py).
    input_dir = str(Path(args.source_file).resolve().parent)

    # 1. Parse UFDR XML
    run_stage(
        stage_name="1/7 UFDR XML Parsing (parser.py)",
        cmd=[py_exe, "parser.py", "--input-dir", input_dir],
        expected_output=parsed_path,
    )

    # 2. Document OCR
    run_stage(
        stage_name="2/7 Document OCR (ocr_transcribe.py)",
        cmd=[py_exe, "ocr_transcribe.py", "--input-dir", input_dir],
        expected_output=ocr_path,
    )

    # 3. Audio Transcription
    run_stage(
        stage_name="3/7 Audio Transcription (transcribe.py)",
        cmd=[py_exe, "transcribe.py", "--input-dir", input_dir],
        expected_output=transcripts_path,
    )

    # 4. Image Analysis & Tagging
    run_stage(
        stage_name="4/7 Image Analysis (image_extractor.py)",
        cmd=[py_exe, "image_extractor.py", "--input-dir", input_dir],
        expected_output=image_analysis_path,
    )

    # 5. Video Analysis & Timeline
    run_stage(
        stage_name="5/7 Forensic Video Analysis (process_video.py)",
        cmd=[py_exe, "process_video.py", "--input-dir", input_dir, "--output-file", str(video_analysis_path)],
        expected_output=video_analysis_path,
        fatal=False,
    )

    # 6. PostgreSQL Database Importer
    # Run backend.import_data module from project root
    import_cmd = [
        py_exe,
        "-m",
        "backend.import_data",
        "--case-name", args.case_name,
        "--source-file", args.source_file,
        "--parsed", str(BACKEND_DIR / parsed_path),
        "--ocr", str(BACKEND_DIR / ocr_path),
        "--transcripts", str(BACKEND_DIR / transcripts_path),
        "--image-analysis", str(BACKEND_DIR / image_analysis_path),
    ]

    import_output = run_stage(
        stage_name="6/7 PostgreSQL Database Import (import_data.py)",
        cmd=import_cmd,
        expected_output=None,
        cwd=PROJECT_ROOT,
        capture=True,
    )

    case_id_match = re.search(r"^CASE_ID=(\d+)$", import_output or "", re.MULTILINE)
    case_id = case_id_match.group(1) if case_id_match else None

    # 7. Qdrant semantic-search indexing -- best-effort: the case data is
    # already safely committed to Postgres by this point, so a failure here
    # (e.g. Qdrant not running) shouldn't be treated as a pipeline failure.
    run_stage(
        stage_name="7/7 Semantic Search Indexing (vector_db.index)",
        cmd=[py_exe, "-m", "backend.vector_db.index"],
        expected_output=None,
        cwd=PROJECT_ROOT,
        fatal=False,
    )

    print("\n==================================================")
    print("  AUTOMATED PIPELINE COMPLETED SUCCESSFULLY!")
    print("==================================================")
    print(f"Case Name:       {args.case_name}")
    print(f"Source File:     {args.source_file}")
    print(f"Input Dir:       {input_dir}")
    print(f"Parsed JSON:     {parsed_path}")
    print(f"OCR JSON:        {ocr_path}")
    print(f"Transcripts JSON:{transcripts_path}")
    print(f"Image JSON:      {image_analysis_path}")
    print("All outputs generated and imported into PostgreSQL database.")
    if case_id:
        print(f"CASE_ID={case_id}")
    else:
        print("WARNING: could not determine the Postgres case id from import_data.py's output.")


if __name__ == "__main__":
    main()
