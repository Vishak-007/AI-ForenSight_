"""
UFDR Upload & Pipeline Status API Route Endpoint for AI-ForenSight.

Provides secure UFDR archive upload handling, path-traversal validation,
background pipeline invocation, and job status tracking.
Reuses backend/run_pipeline.py for full extraction and database import.
"""

import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
UPLOADS_DIR = BACKEND_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/cases/upload", tags=["upload"])

# In-memory status store for tracking background extraction jobs
JOBS: Dict[str, Dict[str, Any]] = {}


def sanitize_filename(name: str) -> str:
    """Sanitize user-provided strings for safe filesystem usage."""
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", name).strip()
    return clean[:50] if clean else "unnamed_case"


def is_safe_extract_path(target_folder: Path, dest_path: Path) -> bool:
    """Ensure destination path resolves within target folder to prevent ZIP path traversal."""
    try:
        dest_path.resolve().relative_to(target_folder.resolve())
        return True
    except ValueError:
        return False


def run_pipeline_background(job_id: str, case_name: str, report_xml_path: Path):
    """Execute the extraction pipeline in a background subprocess."""
    try:
        cmd = [
            sys.executable,
            str(BACKEND_DIR / "run_pipeline.py"),
            "--case-name", case_name,
            "--source-file", str(report_xml_path),
        ]

        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        else:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error_message"] = "UFDR extraction pipeline execution failed."
            JOBS[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error_message"] = "An error occurred while launching background pipeline."
        JOBS[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def upload_ufdr_case(
    background_tasks: BackgroundTasks,
    case_name: str = Form(..., description="Name for the forensic case"),
    file: UploadFile = File(..., description="ZIP archive containing UFDR package"),
):
    """
    Accept a UFDR ZIP upload, validate security rules, extract contents,
    and trigger background processing.
    """
    if not case_name or not case_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_name parameter is required and cannot be empty.",
        )

    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid .zip archive.",
        )

    job_id = str(uuid.uuid4())
    safe_folder_name = f"{job_id[:8]}_{sanitize_filename(case_name)}"
    job_dir = UPLOADS_DIR / safe_folder_name
    job_dir.mkdir(parents=True, exist_ok=True)

    zip_path = job_dir / "uploaded_package.zip"
    try:
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file to storage.",
        )

    # Validate and extract ZIP contents with path-traversal protection
    extracted_dir = job_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            for member in archive.infolist():
                dest_path = extracted_dir / member.filename
                if not is_safe_extract_path(extracted_dir, dest_path):
                    shutil.rmtree(job_dir, ignore_errors=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="ZIP archive contains invalid path traversal entries.",
                    )
            archive.extractall(extracted_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid ZIP archive.",
        )

    # Locate report.xml inside extracted package
    report_xml_path = extracted_dir / "report.xml"
    if not report_xml_path.exists():
        found = list(extracted_dir.rglob("report.xml"))
        if found:
            report_xml_path = found[0]
        else:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UFDR package: report.xml not found in archive.",
            )

    # Register job state
    JOBS[job_id] = {
        "job_id": job_id,
        "case_name": case_name.strip(),
        "status": "processing",
        "error_message": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Dispatch background extraction task
    background_tasks.add_task(
        run_pipeline_background,
        job_id,
        case_name.strip(),
        report_xml_path,
    )

    return {
        "job_id": job_id,
        "case_name": case_name.strip(),
        "status": "processing",
        "message": "UFDR upload received and processing started",
    }


@router.get("/status/{job_id}", status_code=status.HTTP_200_OK)
def get_upload_status(job_id: str):
    """Retrieve background processing status for a UFDR upload job."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload job ID not found.",
        )

    response = {
        "job_id": job["job_id"],
        "case_name": job["case_name"],
        "status": job["status"],
    }
    if job.get("error_message"):
        response["error_message"] = job["error_message"]
    return response
