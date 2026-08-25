# AI-ForenSight

A pipeline for pulling structured data out of UFDR (Universal Forensic Data Extraction Report) exports — messages, calls, contacts, media — running local analysis on top of it, and serving the result through an API a frontend can actually use. Everything analysis-related runs on your machine; nothing gets uploaded to a third party.

## How the pieces fit together

Everything under `backend/` is one pipeline, each stage reading the previous stage's JSON and writing its own:

1. `parser.py` — turns `report.xml` + its `media/` folder into `parsed_output.json` (messages, calls, contacts, and a per-media record with a SHA-256 hash for tamper detection).
2. `ocr_transcribe.py` — OCRs any document/PDF media with Tesseract, writes `ocr_output.json`.
3. `transcribe.py` — transcribes any audio media locally with Whisper, writes `transcripts_output.json`.
4. `image_extractor.py` — face detection/clustering (YuNet + SFace) and CLIP-based evidence tagging on image media, writes `image_analysis_output.json`.
5. `import_data.py` — upserts all of the above into Postgres.
6. `backend/vector_db` — embeds the case's free text (messages, OCR text, transcripts, image tags/context) with a local sentence-transformer and indexes it into Qdrant, so `python -m backend.vector_db.search "some query"` does real semantic search over a case.

`run_pipeline.py` runs stages 1–4, 5, and 6 in order, and only imports into Postgres if every extraction stage actually produced output.

Sitting on top of that, `main.py` is a FastAPI app (`backend/routes/`) exposing the Postgres data over REST — cases, devices, contacts, messages, calls, media, OCR results, transcriptions, image analysis, image tags — plus an upload endpoint that accepts a UFDR zip, extracts it, and runs the whole pipeline against it in the background.

`frontend/forensics-workflow-main` is a React/Vite app that talks to that API: upload a case, poll its processing status, and once it's done, browse the assembled report.

There's also a `translate.py` at the repo root (with its `translation/` package) that converts Tanglish/code-mixed Tamil OCR text into fluent English via a local NLP pipeline (NER protection, transliteration, NLLB, grammar correction). Worth flagging: it isn't wired into `run_pipeline.py`, `import_data.py`, or the vector index yet — it's a standalone script you run by hand, and it lives at the project root while the JSON it reads (`ocr_output.json`) lives in `backend/`, so you currently have to run it with `backend/` as your working directory despite the script itself sitting one level up. That's a real gap, not a design choice — happy to wire it into the pipeline properly if it's needed.

## Setup

**Python dependencies** (from the repo root):
```bash
pip install -r requirements.txt
```

**Tesseract OCR** — install it and make sure it's on your PATH, or at the default Windows location `C:\Program Files\Tesseract-OCR\tesseract.exe`. Without it, `ocr_transcribe.py` still runs but writes a placeholder string instead of real text.

**spaCy's English model** (only needed for `translate.py`'s entity protection step):
```bash
python -m spacy download en_core_web_sm
```

**Postgres and Qdrant.** Easiest is Docker:
```bash
docker run -d --name ufdr-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=ufdr_forensics -p 5432:5432 postgres:16
docker run -d --name ufdr-qdrant -p 6333:6333 qdrant/qdrant
```
Then put the Postgres connection details in a `.env` file (repo root, or `backend/.env` — either is read) defining `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. Qdrant defaults to `localhost:6333` and doesn't need any env vars unless you're pointing it somewhere else. The database schema (`cases`, `messages`, `media`, etc.) creates itself automatically the first time `main.py` starts — no manual migration step.

`image_extractor.py` also downloads a couple of small ONNX face models and the CLIP checkpoint the first time it needs them, and `translate.py` downloads its NLLB/grammar-correction models the first time too — all cached locally after that first run, no further network needed.

## Running it

**Through the API (the real path):** start the backend, then either use the frontend or curl the upload endpoint directly.
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
```bash
curl -X POST http://127.0.0.1:8000/api/cases/upload -F "case_name=My Case" -F "file=@case.zip"
curl http://127.0.0.1:8000/api/cases/upload/status/<job_id>   # poll until status is "completed"
```
The status response includes the Postgres `case_id` once the pipeline finishes, and every `/api/*` endpoint takes `?case_id=` to fetch that case's data.

**Frontend:**
```bash
cd frontend/forensics-workflow-main
npm install
npm run dev
```
It expects the API at `http://127.0.0.1:8000` by default (`VITE_API_BASE_URL` in its `.env`).

**By hand, stage by stage** (useful for debugging one stage without the others). The four extraction scripts use relative paths and expect to run from inside `backend/`; `import_data` and `vector_db.index` are invoked as packages (`-m backend...`) so they need the repo root as your working directory instead:
```bash
cd backend
python parser.py --input-dir sample_ufdr
python ocr_transcribe.py --input-dir sample_ufdr
python transcribe.py --input-dir sample_ufdr
python image_extractor.py --input-dir sample_ufdr
cd ..
python -m backend.import_data --case-name "My Case" --source-file backend/sample_ufdr/report.xml --parsed backend/parsed_output.json --ocr backend/ocr_output.json --transcripts backend/transcripts_output.json --image-analysis backend/image_analysis_output.json
python -m backend.vector_db.index
```

## Where things stand

Video isn't handled yet — `parser.py` records it as seen-but-skipped. `translate.py` works but isn't part of the automated pipeline, as noted above. The CLIP confidence threshold in `image_extractor.py` hasn't been calibrated against real evidentiary photos, so treat those tags as a starting point for review, not a verdict. The frontend's login is a local-only mock with no real backend auth — don't rely on it for anything sensitive. And the pipeline processes one case at a time by design: concurrent uploads would race on the same intermediate JSON files rather than each getting isolated output.
