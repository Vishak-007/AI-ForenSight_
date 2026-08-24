"""
Automated end-to-end pipeline runner for AI-ForenSight.

Sequentially executes:
  1. parser.py           -> parsed_output.json
  2. ocr_transcribe.py   -> ocr_output.json
  3. transcribe.py       -> transcripts_output.json
  4. image_extractor.py  -> image_analysis_output.json
  5. import_data.py      -> PostgreSQL Database Import

Ensures database import is ONLY invoked if all extraction JSON outputs
are generated successfully.
"""

import argparse
import os
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
        "--transcripts-output",
        default="transcripts_output.json",
        help="Output path for transcripts JSON (default: 'transcripts_output.json')",
    )
    parser.add_argument(
        "--image-analysis-output",
        default="image_analysis_output.json",
        help="Output path for image analysis JSON (default: 'image_analysis_output.json')",
    )
    return parser.parse_args()


def run_stage(stage_name: str, cmd: list[str], expected_output: Path | None = None, cwd: Path = BACKEND_DIR) -> None:
    print(f"\n==================================================")
    print(f"  STARTING STAGE: {stage_name}")
    print(f"==================================================")
    print(f"Running command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\nERROR: Stage '{stage_name}' failed with return code {result.returncode}.")
        print("Pipeline execution halted. Database import will NOT be executed.")
        sys.exit(result.returncode)

    if expected_output:
        resolved_output = BACKEND_DIR / expected_output if not expected_output.is_absolute() else expected_output
        if not resolved_output.exists() or resolved_output.stat().st_size == 0:
            print(f"\nERROR: Expected output file '{resolved_output}' was not created or is empty.")
            print("Pipeline execution halted. Database import will NOT be executed.")
            sys.exit(1)
        print(f"Verified output generated: {resolved_output.name} ({resolved_output.stat().st_size} bytes)")

    print(f"STAGE COMPLETED SUCCESSFULLY: {stage_name}\n")


def main():
    args = parse_args()

    parsed_path = Path(args.parsed_output)
    ocr_path = Path(args.ocr_output)
    transcripts_path = Path(args.transcripts_output)
    image_analysis_path = Path(args.image_analysis_output)

    py_exe = sys.executable

    # 1. Parse UFDR XML
    run_stage(
        stage_name="1/5 UFDR XML Parsing (parser.py)",
        cmd=[py_exe, "parser.py"],
        expected_output=parsed_path,
    )

    # 2. Document OCR
    run_stage(
        stage_name="2/5 Document OCR (ocr_transcribe.py)",
        cmd=[py_exe, "ocr_transcribe.py"],
        expected_output=ocr_path,
    )

    # 3. Audio Transcription
    run_stage(
        stage_name="3/5 Audio Transcription (transcribe.py)",
        cmd=[py_exe, "transcribe.py"],
        expected_output=transcripts_path,
    )

    # 4. Image Analysis & Tagging
    run_stage(
        stage_name="4/5 Image Analysis (image_extractor.py)",
        cmd=[py_exe, "image_extractor.py"],
        expected_output=image_analysis_path,
    )

    # 5. PostgreSQL Database Importer
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

    run_stage(
        stage_name="5/5 PostgreSQL Database Import (import_data.py)",
        cmd=import_cmd,
        expected_output=None,
        cwd=PROJECT_ROOT,
    )


    print("\n==================================================")
    print("  AUTOMATED PIPELINE COMPLETED SUCCESSFULLY!")
    print("==================================================")
    print(f"Case Name:       {args.case_name}")
    print(f"Source File:     {args.source_file}")
    print(f"Parsed JSON:     {parsed_path}")
    print(f"OCR JSON:        {ocr_path}")
    print(f"Transcripts JSON:{transcripts_path}")
    print(f"Image JSON:      {image_analysis_path}")
    print("All outputs generated and imported into PostgreSQL database.\n")


if __name__ == "__main__":
    main()
