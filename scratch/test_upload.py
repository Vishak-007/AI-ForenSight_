import json
import time
import zipfile
from io import BytesIO
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path("c:/Development/AI-ForenSight_")
API_BASE = "http://127.0.0.1:8000"


def send_multipart_form(url: str, fields: dict, files: dict):
    boundary = "----TestBoundary123456789"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))

    for name, (filename, content, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    return req


def test_invalid_file_type():
    print("\n--- Test 1: Invalid File Type ---")
    req = send_multipart_form(
        f"{API_BASE}/api/cases/upload",
        {"case_name": "Invalid File Case"},
        {"file": ("test.txt", b"not a zip", "text/plain")}
    )
    try:
        urllib.request.urlopen(req)
        print("FAIL: Expected HTTP 400 for non-zip upload")
    except urllib.error.HTTPError as e:
        print(f"PASS: Rejection HTTP status {e.code}, response: {e.read().decode('utf-8')}")


def test_path_traversal():
    print("\n--- Test 2: Path Traversal Security ---")
    mem_zip = BytesIO()
    with zipfile.ZipFile(mem_zip, "w") as zf:
        zf.writestr("../../malicious.txt", "path traversal payload")
    mem_zip.seek(0)

    req = send_multipart_form(
        f"{API_BASE}/api/cases/upload",
        {"case_name": "Path Traversal Case"},
        {"file": ("malicious.zip", mem_zip.getvalue(), "application/zip")}
    )
    try:
        urllib.request.urlopen(req)
        print("FAIL: Expected HTTP 400 for path traversal ZIP")
    except urllib.error.HTTPError as e:
        print(f"PASS: Path traversal blocked with HTTP status {e.code}, response: {e.read().decode('utf-8')}")


def test_valid_upload():
    print("\n--- Test 3: Valid UFDR ZIP Upload ---")
    zip_path = ROOT / "scratch" / "sample_ufdr.zip"
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    case_name = f"Uploaded Step4B Case {int(time.time())}"
    req = send_multipart_form(
        f"{API_BASE}/api/cases/upload",
        {"case_name": case_name},
        {"file": ("sample_ufdr.zip", zip_bytes, "application/zip")}
    )

    resp = urllib.request.urlopen(req)
    print(f"Upload Response Status Code: {resp.status}")
    resp_data = json.loads(resp.read().decode("utf-8"))
    print(f"Upload Response Data: {json.dumps(resp_data, indent=2)}")

    job_id = resp_data["job_id"]
    print(f"\nMonitoring Job ID: {job_id} ...")

    # Initial status check
    status_url = f"{API_BASE}/api/cases/upload/status/{job_id}"
    status_resp = json.loads(urllib.request.urlopen(status_url).read().decode("utf-8"))
    print(f"Initial Status Response: {json.dumps(status_resp, indent=2)}")

    # Poll status until finished
    start_time = time.time()
    while time.time() - start_time < 60:
        time.sleep(2)
        status_resp = json.loads(urllib.request.urlopen(status_url).read().decode("utf-8"))
        current_status = status_resp.get("status")
        print(f"Current Status: {current_status}")
        if current_status in ("completed", "failed"):
            break

    print(f"\nFinal Job Status Response: {json.dumps(status_resp, indent=2)}")

    # Verify Database Case Created
    cases_resp = json.loads(urllib.request.urlopen(f"{API_BASE}/api/cases").read().decode("utf-8"))
    new_case = next((c for c in cases_resp if c["case_name"] == case_name), None)
    print(f"\nNew Case in Database: {json.dumps(new_case, indent=2)}")

    if new_case:
        new_case_id = new_case["id"]
        # Verify filtered endpoints with new_case_id
        devs = json.loads(urllib.request.urlopen(f"{API_BASE}/api/devices?case_id={new_case_id}").read().decode("utf-8"))
        msgs = json.loads(urllib.request.urlopen(f"{API_BASE}/api/messages?case_id={new_case_id}").read().decode("utf-8"))
        media = json.loads(urllib.request.urlopen(f"{API_BASE}/api/media?case_id={new_case_id}").read().decode("utf-8"))
        ocr = json.loads(urllib.request.urlopen(f"{API_BASE}/api/ocr-results?case_id={new_case_id}").read().decode("utf-8"))
        print(f"New Case ({new_case_id}) Records -> Devices: {len(devs)}, Messages: {len(msgs)}, Media: {len(media)}, OCR Results: {len(ocr)}")


if __name__ == "__main__":
    test_invalid_file_type()
    test_path_traversal()
    test_valid_upload()
