import json
import time
from pathlib import Path
import urllib.request

ROOT = Path("c:/Development/AI-ForenSight_")
API_BASE = "http://127.0.0.1:8000"


def test_real_upload():
    print("\n--- Step 5C Real Upload Test ---")
    case_name = f"Frontend Step 5C Case {int(time.time())}"
    zip_path = ROOT / "scratch" / "sample_ufdr.zip"

    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    boundary = "----FrontendBoundary987654"
    body = bytearray()

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="case_name"\r\n\r\n'.encode("utf-8"))
    body.extend(f"{case_name}\r\n".encode("utf-8"))

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="sample_ufdr.zip"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: application/zip\r\n\r\n")
    body.extend(zip_bytes)
    body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        f"{API_BASE}/api/cases/upload",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    resp = urllib.request.urlopen(req)
    print(f"POST /api/cases/upload -> Status: {resp.status}")
    resp_data = json.loads(resp.read().decode("utf-8"))
    print(f"Upload Response: {json.dumps(resp_data, indent=2)}")

    job_id = resp_data["job_id"]
    print(f"\nPolling Status for job_id: {job_id} every 2 seconds...")

    status_url = f"{API_BASE}/api/cases/upload/status/{job_id}"
    start_time = time.time()
    final_status = "processing"

    while time.time() - start_time < 60:
        time.sleep(2)
        s_resp = json.loads(urllib.request.urlopen(status_url).read().decode("utf-8"))
        final_status = s_resp.get("status")
        print(f"Status: {final_status}")
        if final_status in ("completed", "failed"):
            break

    print(f"\nFinal Status: {final_status}")

    cases = json.loads(urllib.request.urlopen(f"{API_BASE}/api/cases").read().decode("utf-8"))
    new_case = next((c for c in cases if c["case_name"] == case_name), None)
    print(f"\nVerified PostgreSQL Case: {json.dumps(new_case, indent=2)}")


if __name__ == "__main__":
    test_real_upload()
