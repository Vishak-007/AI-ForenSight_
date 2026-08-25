# AI-ForenSight: Multi-Modal Forensic Extraction & Video Analysis Pipeline

AI-ForenSight is an offline, local digital forensics analysis pipeline and investigation dashboard for UFDR (Universal Forensic Data Extraction Report) packages and multi-modal digital evidence (documents, images, audio, and video). Everything runs locally without uploading data to third-party services.

---

## Capabilities & Architecture

1. **UFDR Parsing & Integrity Hashing**: `parser.py` extracts messages, calls, contacts, and media with SHA-256 integrity hashing for tamper detection.
2. **Document OCR**: `ocr_transcribe.py` extracts embedded text across PDFs and images with Tesseract.
3. **Audio Transcription**: `transcribe.py` runs local Whisper speech-to-text with timestamping.
4. **Facial Detection & Visual Tagging**: `image_extractor.py` performs face detection/clustering (YuNet + SFace) and CLIP zero-shot forensic evidence tagging.
5. **Forensic Video Analysis**: `process_video.py` performs keyframe extraction, YOLOv8 object detection, EasyOCR on-screen text extraction, Faster-Whisper audio dialogue transcription, and contextual scene inference.
6. **Data Storage & Audit Trails**: `import_data.py` & `backend/database/` store structured data and immutable hash-chained audit logs in PostgreSQL.
7. **Semantic Vector Search**: `backend/vector_db` indexes extracted forensic data into Qdrant vector database for natural language semantic search.
8. **Interactive UI**: `frontend/forensics-workflow-main` React/Vite dashboard for case uploading, timeline exploration, media inspection, and audit history.

---

## Setup

**1. Install Python Dependencies** (from repo root):
```bash
pip install -r requirements.txt
```

**2. Tesseract OCR**
Make sure Tesseract is installed and on your PATH (or standard Windows location `C:\Program Files\Tesseract-OCR\tesseract.exe`).

**3. Postgres and Qdrant** (Docker recommended):
```bash
docker run -d --name ufdr-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=ufdr_forensics -p 5432:5432 postgres:16
docker run -d --name ufdr-qdrant -p 6333:6333 qdrant/qdrant
```

Configure `.env` with:
```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=ufdr_forensics
DB_USER=postgres
DB_PASSWORD=123456
```

---

## Running the Application

### Option A: Using Startup Scripts (Windows)
Double-click or run:
```bat
start-all.bat
```
Or start individually:
```bat
start-backend.bat
start-frontend.bat
```

### Option B: Manual CLI

**Start Backend (FastAPI):**
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Start Frontend:**
```bash
cd frontend/forensics-workflow-main
npm install
npm run dev
```

---

## Standalone Video Analysis

Analyze any video directly:
```bash
python process_video.py sample_ufdr/media/video.mp4 video_analysis_output.json
```

**CLI Arguments:**
- `video_path`: Path to input video file
- `-o, --output`: Path to output JSON file (default: `video_analysis_output.json`)
- `--sample_fps`: Frames per second to sample for visual detection and OCR (default: `1.0`)
- `--whisper_model`: Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`)
- `--yolo_model`: YOLO model weights (default: `yolov8n.pt`)
