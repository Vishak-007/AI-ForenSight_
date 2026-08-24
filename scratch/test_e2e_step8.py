import json
import time
from pathlib import Path
import urllib.request

ROOT = Path("c:/Development/AI-ForenSight_")
API_BASE = "http://127.0.0.1:8000"

def run_step8_e2e_test():
    print("\n==========================================")
    print("STEP 8 END-TO-END INTEGRATION AUDIT TEST")
    print("==========================================\n")

    # 1. Health check
    h_resp = json.loads(urllib.request.urlopen(f"{API_BASE}/api/health").read().decode("utf-8"))
    print(f"1. API Health: {h_resp.get('status')} | DB: {h_resp.get('database_status')}")

    # 2. Upload Case
    case_name = f"Final E2E Integration Test {int(time.time())}"
    zip_path = ROOT / "scratch" / "sample_ufdr.zip"
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    boundary = "----Step8Boundary12345"
    body = bytearray()
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"case_name\"\r\n\r\n{case_name}\r\n".encode("utf-8"))
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"sample_ufdr.zip\"\r\nContent-Type: application/zip\r\n\r\n".encode("utf-8"))
    body.extend(zip_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        f"{API_BASE}/api/cases/upload",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    u_resp = urllib.request.urlopen(req)
    assert u_resp.status == 202
    u_data = json.loads(u_resp.read().decode("utf-8"))
    job_id = u_data["job_id"]
    print(f"2. Upload Accepted (HTTP 202) -> job_id: {job_id}")

    # 3. Status Polling
    status_url = f"{API_BASE}/api/cases/upload/status/{job_id}"
    start = time.time()
    final_status = "processing"
    while time.time() - start < 60:
        time.sleep(2)
        s_data = json.loads(urllib.request.urlopen(status_url).read().decode("utf-8"))
        final_status = s_data.get("status")
        if final_status in ("completed", "failed"):
            break

    print(f"3. Pipeline Execution Status: {final_status}")
    assert final_status == "completed"

    # 4. Fetch Cases
    cases = json.loads(urllib.request.urlopen(f"{API_BASE}/api/cases").read().decode("utf-8"))
    new_case = next((c for c in cases if c["case_name"] == case_name), None)
    print(f"4. Verified New Case in DB: ID={new_case['id']} | Name='{new_case['case_name']}'")
    cid = new_case["id"]

    # 5. Fetch all endpoints for new case
    endpoints = ['devices', 'contacts', 'messages', 'calls', 'media', 'ocr-results', 'transcriptions', 'image-analysis', 'image-tags']
    results = {}
    for ep in endpoints:
        data = json.loads(urllib.request.urlopen(f"{API_BASE}/api/{ep}?case_id={cid}").read().decode("utf-8"))
        results[ep] = len(data)

    print(f"5. Endpoints Verification for Case #{cid}:")
    for k, v in results.items():
        print(f"   - /api/{k}?case_id={cid} -> {v} records")

    print("\n==========================================")
    print("ALL STEP 8 END-TO-END TESTS PASSED SUCCESSFULLY!")
    print("==========================================\n")

if __name__ == "__main__":
    run_step8_e2e_test()
