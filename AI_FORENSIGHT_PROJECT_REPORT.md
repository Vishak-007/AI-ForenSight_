# AI-ForenSight — Full Project Report & Hackathon Prep

**Prepared:** 2026-08-25
**Scope:** Complete technical breakdown of every phase, module, and tool in the pipeline, plus a judge-question prep guide.
**Location note:** This file lives at the repo root (`AIForensight/`), outside `backend/` and `frontend/`, so it stays a standalone reference independent of either codebase.

---

## 1. What this project is

AI-ForenSight is an offline-first digital forensics pipeline that takes a **UFDR (Universal Forensic Data Extraction Report)** export — the kind of ZIP a tool like Cellebrite produces from a seized phone — and turns it into a structured, searchable, browsable case file.

It does three things a human forensic analyst would otherwise do by hand:

1. **Extracts** structured evidence (messages, calls, contacts, media) from the raw XML + media dump.
2. **Enriches** that evidence with local AI: OCR on documents, speech-to-text on audio, face detection/clustering and CLIP-based evidence tagging on images, and Tanglish (code-mixed Tamil-English) → English translation.
3. **Serves** it through a REST API and a React dashboard so an investigator can search, filter, timeline, and export a report — without any of the evidence ever leaving the machine.

**Core design principle: everything runs locally.** No OpenAI/cloud API calls anywhere in the analysis pipeline — Tesseract, Whisper, CLIP, YuNet/SFace, NLLB, and the sentence-transformer embedding model all run on-device. This matters enormously for a forensics tool: chain-of-custody and evidentiary integrity arguments get much harder the moment evidence touches a third-party server.

---

## 2. High-level architecture

```
                        ┌─────────────────────────────┐
                        │   UFDR ZIP (report.xml +     │
                        │   media/ folder)              │
                        └──────────────┬───────────────┘
                                       │  upload (FastAPI, multipart)
                                       ▼
                        ┌─────────────────────────────┐
                        │  routes/upload.py             │
                        │  - sanitize case name          │
                        │  - zip-slip / path-traversal   │
                        │    validation                  │
                        │  - extract to backend/uploads/ │
                        │  - kick off background job     │
                        └──────────────┬───────────────┘
                                       ▼
                        ┌─────────────────────────────┐
                        │   run_pipeline.py (orchestr.) │
                        │   7 sequential stages          │
                        └──────────────┬───────────────┘
        ┌───────────────┬──────────────┼──────────────┬───────────────┐
        ▼               ▼              ▼              ▼               ▼
   1. parser.py   2. ocr_transcribe 3. translate.py 4. transcribe.py 5. image_extractor.py
   (XML→JSON,     (Tesseract OCR    (Tanglish→Eng,  (faster-whisper  (YuNet+SFace faces,
   SHA-256 hash)  on documents)     NLLB, best-eff.)  audio→text)     CLIP evidence tags)
        │               │              │              │               │
        └───────────────┴──────────────┴──────────────┴───────────────┘
                                       ▼
                        ┌─────────────────────────────┐
                        │ 6. import_data.py             │
                        │    → PostgreSQL (source of     │
                        │      truth, structured)        │
                        └──────────────┬───────────────┘
                                       ▼
                        ┌─────────────────────────────┐
                        │ 7. vector_db/index.py         │
                        │    → Qdrant (semantic search   │
                        │      over free text, best-eff.)│
                        └──────────────┬───────────────┘
                                       ▼
                        ┌─────────────────────────────┐
                        │ main.py — FastAPI REST API    │
                        │ /api/cases /messages /calls    │
                        │ /media /ocr-results /...       │
                        └──────────────┬───────────────┘
                                       ▼
                        ┌─────────────────────────────┐
                        │ React/Vite frontend            │
                        │ Upload → Progress → Dashboard  │
                        │ → Timeline/Entities/Flags/Media │
                        │ → Report export (PDF)          │
                        └─────────────────────────────┘
```

Every stage reads the previous stage's JSON output and writes its own — the intermediate artifacts (`parsed_output.json`, `ocr_output.json`, `translated_output.json`, `transcripts_output.json`, `image_analysis_output.json`) are plain files, which makes each stage independently debuggable and re-runnable.

---

## 3. Phase-by-phase breakdown

### Phase 0 — Ingestion (`backend/routes/upload.py`)

| Aspect | Detail |
|---|---|
| Trigger | `POST /api/cases/upload` (multipart form: `case_name`, `file`) |
| Validation | Rejects non-`.zip` files; sanitizes `case_name` to `[a-zA-Z0-9_-]`, capped at 50 chars |
| Security | **Zip-slip protection** — every archive member's resolved destination path is checked with `Path.resolve().relative_to()` before extraction; any entry that would land outside the job folder aborts the whole upload |
| Storage | Each upload gets an isolated folder: `backend/uploads/<uuid8>_<sanitized_case_name>/` containing the raw zip and an `extracted/` subfolder |
| Report discovery | Looks for `report.xml` at the extracted root, falls back to a recursive `rglob` search |
| Execution model | Runs the whole pipeline as a **background `subprocess`**, tracked by an in-memory `JOBS` dict keyed by `job_id`; the client polls `GET /api/cases/upload/status/{job_id}` until `status == "completed"` |
| Known limitation | `JOBS` is in-memory — a server restart loses in-flight job status. One case processes at a time by design (concurrent uploads would race on shared intermediate JSON files). |

### Phase 1 — UFDR XML Parsing (`backend/parser.py`)

- Parses `report.xml` with `xmltodict`, and **recognizes two schemas transparently**:
  - This project's own `<ufdr_report>` schema (flat `<messages>`, `<calls>`, `<contacts>`, `<media>` lists).
  - A **Cellebrite-style** `<report version="...">` schema, where messages live nested per-app inside `<chats><chat><message>` with inline `<attachment>` tags, and calls carry `type`/`number` attributes instead of separate caller/callee fields. `extract_report_schema()` flattens both into the same normalized shape so nothing downstream needs to know which schema was used.
- For every media item, computes a **SHA-256 hash** and file size — this is the evidentiary-integrity hook: if the file is later re-hashed and the digest doesn't match, tampering is provable.
- Type-specific metadata readers: image dimensions (Pillow), WAV duration/channels/sample-rate (stdlib `wave`, with graceful fallback to just the extension for compressed formats like `.m4a`/`.mp4` voice notes, since real transcription is Whisper's job later, not this stage's), and document metadata (PNG/JPEG get image metadata, everything else just gets its extension recorded).
- **Video is explicitly out of scope** — recorded as `SKIPPED_VIDEO_NOT_IMPLEMENTED` rather than silently dropped, so the gap is visible in the output rather than hidden.
- Output: `parsed_output.json` — the canonical structured record every later stage reads from.

### Phase 2 — Document OCR (`backend/ocr_transcribe.py`)

- Filters `parsed_output.json`'s media list down to successfully-parsed `document` records.
- **Tesseract OCR** (via `pytesseract`) for images; **PyMuPDF** renders each PDF page to a 300-DPI bitmap first, then OCRs each page and joins the text.
- Fully offline once Tesseract is installed — auto-detects it at the default Windows install path or on `PATH`; if missing, doesn't crash, just writes a placeholder string (`"[OCR Skipped: Tesseract OCR not installed on host system]"`) so the pipeline still completes.
- Output: `ocr_output.json` (per-document transcript + file metadata + folder-level stats like total size/last-modified, useful for a report's "extraction summary" section).

### Phase 3 — Tanglish → English Translation (`translate.py` + `translation/` package)

This is the most linguistically sophisticated module in the project — a **from-scratch NLP pipeline** for code-mixed Tamil-English ("Tanglish") text, common in South Indian chat data and a real blind spot for off-the-shelf translation tools.

Pipeline stages (see `translation/pipeline.py`):

1. **NER / entity protection** (`ner.py`, spaCy `en_core_web_sm`) — masks names, numbers, times, etc. before translation so they aren't mangled or "translated" themselves.
2. **Tokenization** (`tokenizer.py`) — splits into words/whitespace/punctuation.
3. **Clause segmentation** — splits on punctuation and entity placeholders, then groups tokens into alternating English/Tanglish runs. A hard rule: **translation never happens per isolated word** — a short English word embedded in an otherwise-Tanglish clause (e.g. "work" in *"naan nalaiku vara maten enaku work iruku"*) is kept as an inline loanword rather than splitting the clause, so NLLB always sees the full clause in one call and can use context.
4. **Language identification** (`lang_id.py`) — uses `wordfreq` Zipf-frequency scoring (threshold 2.5) plus a hand-curated whitelist of contractions (`dont`, `cant`, `youre`...) and a **known-Tanglish function-word set** (`enna`, `iruku`, `naan`, `venum`...) to route each token.
5. **English-path correction** — `symspellpy` (edit distance ≤ 2) fixes typos, with a calibrated Zipf threshold (4.5) so it doesn't misfire on proper nouns that happen to be edit-distance-1 from a common word.
6. **Tanglish-path**: `transliterate.py` maps romanized Tanglish to Tamil script via a **hand-built lexicon of ~90+ entries** (sourced partly from a frequency analysis of a public Tanglish corpus), then `nllb_translate.py` runs **Meta's NLLB-200 (distilled-600M)** Tamil→English translation over the whole clause.
7. **Sentence reconstruction** (`reconstruct.py`) — stitches processed clauses back together with correct spacing/punctuation.
8. **Grammar correction** (`grammar_correct.py`) — a T5 grammar-correction model (`vennify/t5-base-grammar-correction`), gated by a **content-word overlap check (≥0.8)** against the pre-correction text — if the model paraphrases or drops meaning instead of making a minimal grammar fix, its output is discarded and the safer pre-correction text is kept. This guards against a generative model silently hallucinating away evidentiary content.
9. **Entity restoration** — swaps the protected placeholders back in.
10. Every stage logs a `StageTrace` — the **full transformation is auditable end-to-end**, important for defending translated evidence in court.

**Status: best-effort, not fully wired in.** `run_pipeline.py` calls it as a non-fatal stage (large ~2.4GB NLLB model download may not be available everywhere), and per the README it currently has to be run with `backend/` as the working directory despite living at the project root — a known rough edge, not a design choice.

### Phase 4 — Audio Transcription (`backend/transcribe.py`)

- **faster-whisper** (`base` model, CPU, `int8` compute type — a deliberate speed/accuracy tradeoff for a hackathon-scale demo) transcribes every successfully-parsed `audio` media record.
- Also detects and records the spoken language per clip.
- Handles a real Windows-specific gotcha: both `onnxruntime` and `faster-whisper`'s `ctranslate2`/`av` dependency bundle their own copy of Intel's OpenMP runtime, which crashes on double-init unless `KMP_DUPLICATE_LIB_OK=TRUE` is set *before* either library is imported.
- Output: `transcripts_output.json`.

### Phase 5 — Image Analysis & Evidence Tagging (`backend/image_extractor.py`)

Three independent local-AI subsystems over every successfully-parsed image:

1. **Face detection + clustering** — OpenCV's **YuNet** (detector) + **SFace** (128-d embedding), both auto-downloaded ONNX models from the OpenCV Zoo on first run. Faces across the *entire case* are clustered into `person_1`, `person_2`, ... using **scikit-learn's `AgglomerativeClustering`** (cosine distance, threshold 0.363 — SFace's own documented same-person threshold at a low false-accept rate). This lets an investigator ask "which photos does this same person appear in?" without manual tagging.
2. **CLIP zero-shot evidence tagging** — `openai/clip-vit-base-patch32` compares each image against a **fixed vocabulary of forensically-relevant prompts**: pills/medication, drug paraphernalia, firearms, knives, cash, financial documents, ID documents, screenshots. Confidence threshold set at 0.25, deliberately **recall-biased**: a false positive costs an analyst a few seconds of review; a false negative silently hides evidence. Explicitly flagged in code comments as *not yet calibrated against real evidentiary photos* — a known, honestly-disclosed limitation.
3. **Heuristic scene context** — no generative captioning (avoids hallucination risk); instead computes orientation, brightness (via mean grayscale value), dominant color channel, and face count into a template sentence like `"landscape image, 1920x1080, bright, predominantly red tones, 2 faces detected."` This becomes one of the free-text fields embedded for semantic search.
- Also extracts EXIF metadata when present (camera info, GPS, timestamps — forensically valuable).
- Output: `image_analysis_output.json` (per-image analysis + a `persons` summary keyed by cluster).

### Phase 6 — PostgreSQL Import (`backend/import_data.py`)

- Loads every prior stage's JSON and **upserts** it into Postgres inside a single transaction per case (`ON CONFLICT DO UPDATE` everywhere — safe to re-run against the same case).
- Strict validation before any row is written: ISO-timestamp parsing, non-negative integer checks, SHA-256 format validation (`^[0-9a-fA-F]{64}$`), confidence bounded to `[0,1]`. A malformed record doesn't crash the import — it's **collected into a `skipped` list and reported**, so partial data quality issues are visible rather than silent.
- Resolves foreign-key references (media → message/call) defensively: if an associated message/call ID doesn't exist yet, the association is dropped (not the whole record) and logged.
- When `translate.py`'s output exists, its `final_english` text is attached to the matching OCR row as `translated_text` — a nice example of a "best-effort" stage still improving the pipeline's other outputs when available.
- `run_pipeline.py` **only invokes this stage if every extraction stage actually produced output** — a guard against silently importing an incomplete/corrupt case.

### Phase 7 — Semantic Search Indexing (`backend/vector_db/`)

- **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, ~80MB, CPU-friendly) — chosen to reuse the same torch/transformers stack CLIP already needs, rather than adding a new heavy dependency.
- **Vector store**: **Qdrant** (local Docker container by default).
- What gets embedded (`extractor.py`): message text, OCR transcript text (**preferring the English-translated version over raw Tanglish** when available — the embedding model was trained on English, so semantic search over untranslated code-mixed text is much weaker), audio transcript text, image heuristic context, and above-threshold CLIP evidence tags rendered as text (e.g. `"Possible evidentiary content: firearm (0.81), cash (0.42)"`).
- **Deterministic point IDs** (`case_ref + source_type + business_id`) make re-indexing idempotent — no duplicate points from re-runs.
- Decoupled from Postgres: doesn't require the DB to be reachable, and doesn't require Postgres row IDs to exist yet (those get enriched later); it only needs the pipeline's JSON files.
- CLI: `python -m backend.vector_db.search "some query" --case-id <ref> --top 10` — real natural-language search over an entire case's messages, documents, transcripts, and image content in one query.
- Best-effort in `run_pipeline.py`: a Qdrant outage doesn't fail the pipeline, since the case data is already safely in Postgres by that point.

### Phase 8 — REST API (`backend/main.py` + `backend/routes/`)

- **FastAPI**, with a modular router per resource: `cases`, `devices`, `contacts`, `messages`, `calls`, `media`, `ocr_results`, `transcriptions`, `image_analysis`, `image_tags`, `upload`.
- Schema self-initializes on startup (`initialize_schema()` — idempotent `CREATE TABLE/INDEX IF NOT EXISTS`), so a fresh Postgres instance needs zero manual migration steps.
- `/api/health` checks live DB connectivity and reports the Postgres version — useful both for local dev and as a demo talking point ("the system self-reports its own health").
- CORS: wide open (`allow_origins=["*"]`) but **`allow_credentials=False`** — a deliberate, documented choice (browsers reject wildcard origin + credentials together, and the frontend's mock auth never sends cookies anyway).
- Every data endpoint is scoped with a `?case_id=` query param — multi-case-aware from the ground up even though the pipeline itself processes one case at a time.

### Phase 9 — Frontend (`frontend/forensics-workflow-main/`)

- **Stack**: React 19, TanStack Start + TanStack Router (file-based routing) + TanStack Query, Vite 8, Tailwind CSS v4, Radix UI primitives wrapped in shadcn-style components, `recharts` for charts, `jspdf` for client-side PDF report export, `react-hook-form` + `zod` for forms, `sonner` for toasts, `lucide-react` for icons.
- **Routes** (`src/routes/_shell.*.tsx`): `login`, `dashboard`, `upload`, `timeline`, `entities` (contact/relationship view), `flags` (evidence tags surfaced from CLIP), `media`, `report`, `settings` — a full investigator workflow, not just a file browser.
- **State management**: a custom `InvestigationProvider` React context (`src/lib/investigation.tsx`) tracks the whole upload → analysis → report lifecycle client-side, persisted to `sessionStorage` so navigating between pages (or a refresh) never loses the active case. It polls the backend's job-status endpoint and maps backend stage state onto a fixed `STAGE_DEFS` list (upload → parse → messages → ... ) for the progress UI.
- **Key components**: `UploadDropzone`, `AnalysisProgress`/`AnalysisStatusBar`, `Timeline`/`TimelineItem`, `EvidenceBlock`, `SearchBar`, `StatCard`, `SummaryPanel`, `CaseOverview`, `ReportPreview`/`ReportSection`, `PDFGenerator`, `AiCaption`, `FilterBar`.
- **Auth**: `src/lib/auth.tsx` is an explicitly **local-only mock** — no real backend authentication. This is a known, disclosed gap (README calls it out directly), not something to claim as secure in a demo.
- Talks to the backend purely over `fetch` against `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8000`).

---

## 4. Tooling reference (by module)

| Layer | Tool / Library | Purpose | Why this one |
|---|---|---|---|
| XML parsing | `xmltodict` | UFDR/Cellebrite XML → Python dict | Handles arbitrary/nested schemas without a hand-written parser |
| Integrity | `hashlib` (SHA-256) | Per-file hash at parse time | Tamper-evidence — cheap now, expensive to retrofit |
| Image metadata | `Pillow` | Dimensions, format, EXIF | Standard, lightweight |
| PDF rendering | `pymupdf` (fitz) | Render PDF pages to bitmaps for OCR | Fast, no external binary dependency |
| OCR | `pytesseract` + Tesseract OCR | Document/image text extraction | Free, fully offline, industry-standard |
| Audio transcription | `faster-whisper` | Speech-to-text | CTranslate2-optimized Whisper — much faster than stock `openai-whisper` on CPU |
| Face detection | OpenCV `FaceDetectorYN` (YuNet) | Locate faces in images | Small ONNX model, no GPU required |
| Face embedding | OpenCV `FaceRecognizerSF` (SFace) | 128-d face vectors for matching | Pairs natively with YuNet in OpenCV's zoo |
| Face clustering | `scikit-learn` `AgglomerativeClustering` | Group faces into person identities | No need to pre-specify cluster count |
| Zero-shot image tagging | `transformers` `CLIPModel` (ViT-B/32) | Evidence-category detection without training data | Zero-shot = no labeled forensic dataset needed |
| Tanglish NLP | `spacy` (`en_core_web_sm`), `wordfreq`, `symspellpy`, `indic_transliteration`, `transformers` (NLLB-200, T5 grammar) | Code-mixed translation pipeline | Purpose-built for a gap generic translators (Google Translate etc.) handle poorly |
| Vector embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Semantic text embeddings | Small, fast, CPU-friendly, shares the torch stack CLIP needs |
| Vector database | `qdrant-client` / Qdrant server | Semantic search index | Open-source, self-hostable, filterable payloads |
| Relational database | PostgreSQL + `psycopg[binary]` | System of record for structured case data | ACID guarantees for evidentiary data, mature FK/constraint support |
| Backend API | `FastAPI` + `uvicorn` | REST layer | Async, auto-validated, fast to build against |
| Backend config | `python-dotenv` | `.env`-based DB/Qdrant config | Keeps secrets out of source |
| Frontend framework | React 19 + TanStack Start/Router/Query | SPA + routing + server-state caching | File-based routing, strong caching/retry semantics for polling job status |
| Frontend styling | Tailwind CSS v4 + Radix UI (shadcn pattern) | Accessible, consistent UI components | Accessible primitives + full styling control |
| PDF export | `jspdf` | Client-side report generation | No backend rendering service needed |
| Charts | `recharts` | Dashboard visualizations | Standard React charting library |

---

## 5. Data model (PostgreSQL)

`cases (1) → devices, contacts, messages, calls, media (N)`, with `media` optionally pointing at a `message` or `call` it was attached to, and `ocr_results` / `transcriptions` / `image_analysis` / `image_tags` hanging off `media`.

Notable schema decisions:
- Every business-facing ID (`case_id, message_id`) etc. is `UNIQUE` per case, enabling idempotent upserts.
- `media.storage_path` is `NOT NULL` — every media row is traceable to a file on disk.
- `sha256 CHAR(64)` with app-level regex validation — enforced at the import layer, not just trusted from JSON.
- Foreign keys use **composite keys** (`case_id, associated_message_id`) rather than bare IDs — prevents a media row in Case A from ever referencing a message in Case B.
- All numeric/confidence columns carry `CHECK` constraints (non-negative durations/sizes, confidence in `[0,1]`) — the database itself is a second line of defense against bad data, not just the Python validation in `import_data.py`.

---

## 6. Known limitations (own these proactively — they're already documented in the repo's own README, which is a strength, not a weakness)

- **Video is not processed** — parser records it as seen-and-skipped; same extension pattern as audio would apply (ffprobe/moviepy) but isn't built.
- **Tanglish translation isn't wired into the automated pipeline's downstream consumers** as tightly as the other stages — it runs, but the working-directory mismatch (script at root, reads `backend/ocr_output.json`) is a real rough edge.
- **CLIP evidence-tag threshold (0.25) is uncalibrated** against real evidentiary photos — the only bundled sample image is a placeholder graphic. This is explicitly flagged in the code itself.
- **Frontend auth is a local mock** — not connected to any real backend authentication/authorization.
- **One case processes at a time** — concurrent uploads would race on shared intermediate JSON filenames rather than getting isolated outputs (each upload *is* isolated on disk, but the underlying scripts still write to fixed filenames like `parsed_output.json` inside `backend/`, so two pipeline runs at once would clobber each other).
- **In-memory job tracking** — `JOBS` dict in `upload.py` is lost on server restart; there's no persistent job/task table.

---

## 7. Hackathon judge Q&A — preparation guide

Organized by the categories judges typically probe. Each entry gives the likely question and a tight, honest answer built from what's actually in this codebase — not aspirational claims.

### A. Problem & value proposition

**Q: What problem does this solve, and who's the user?**
> Digital forensic examiners currently work through UFDR exports largely manually — reading raw XML/CSV dumps, playing every audio file, eyeballing every photo. AI-ForenSight automates extraction, transcription, translation, and evidence tagging, then gives them a searchable, timeline-based case view instead of a folder of files. The user is a forensic analyst or investigator working a phone-extraction case.

**Q: Why does this need AI at all — couldn't this just be a parser + UI?**
> The parsing/structuring part could be. The value-add is the enrichment layer: OCR turns scanned documents into searchable text, Whisper turns voice notes into readable transcripts, CLIP flags images that might contain contraband/weapons/cash without an analyst opening every photo, and face clustering answers "who else is in these photos with the suspect" automatically. None of that is possible from the raw XML alone.

**Q: What's novel here versus existing forensic tools (Cellebrite, Magnet AXIOM, etc.)?**
> Two things: (1) it's open, local, and free — no vendor lock-in or per-seat licensing; (2) the Tanglish/code-mixed translation pipeline is a genuinely underserved niche — generic translators handle code-switched informal chat (a huge fraction of real South Asian messaging data) poorly, and this project built a dedicated NLP pipeline for exactly that case, including an audit trail per translation stage.

### B. Architecture & technical depth

**Q: Walk me through what happens the moment someone uploads a case.**
> (Use the Phase 0–7 breakdown above — zip-slip-safe extraction, background subprocess pipeline, seven sequential stages each producing a JSON artifact, Postgres import guarded to only run if every stage succeeded, then best-effort vector indexing.)

**Q: Why JSON intermediate files between stages instead of, say, calling functions directly in one process?**
> Each stage is a separate script with its own heavy dependencies (Tesseract, Whisper, OpenCV, CLIP, NLLB) — keeping them as separate processes means one stage's failure or dependency issue doesn't take down the others, and each is independently runnable/debuggable/re-runnable by hand. `run_pipeline.py` documents this is by design.

**Q: Why both Postgres AND Qdrant — isn't that redundant?**
> Different jobs. Postgres is the system of record: structured, relational, ACID, exact-match queries ("all calls to this number," "all media from this date"). Qdrant is for semantic search over free text — "find messages/documents/transcripts about X" where you don't know the exact keyword. They're deliberately decoupled: the vector index doesn't require Postgres to be up, and a Qdrant outage doesn't fail the pipeline since Postgres import already succeeded.

**Q: How do you handle two different UFDR export formats?**
> `parser.py` detects the XML root element and branches: this project's own flat `<ufdr_report>` schema, or a Cellebrite-style `<report>` schema with nested per-app chats and attribute-based calls. Both get normalized into the same internal shape before anything downstream touches them, so OCR/transcription/import code never needs to know which source format was used.

**Q: What happens if a stage fails partway through?**
> Depends on the stage. Core extraction stages (parse, OCR, transcribe, image analysis) are fatal — the pipeline halts and Postgres import is skipped entirely, so you never get a half-imported case. Translation and vector indexing are explicitly marked best-effort/non-fatal, because they depend on large model downloads or an optional external service (Qdrant) that shouldn't block getting the core evidence into the database.

### C. AI/ML specifics

**Q: What models are you running, and are any of them fine-tuned?**
> All off-the-shelf, zero/few-shot — no custom training, which is honest for a hackathon timeframe: Tesseract (OCR), faster-whisper `base` (ASR), OpenCV YuNet+SFace (face detection/embedding, not fine-tuned), CLIP ViT-B/32 (zero-shot evidence classification via prompt engineering against 8 fixed categories), NLLB-200-distilled-600M (Tamil→English MT), a T5 grammar-correction checkpoint, and `all-MiniLM-L6-v2` for embeddings.

**Q: How confident are you in the CLIP evidence tags — could this create false accusations?**
> This is intentionally recall-biased and explicitly framed as a screening aid, not a verdict — the threshold (0.25) is uncalibrated against real evidentiary photos in the code's own comments, and the UI presents tags as flags for analyst review, never as automated conclusions. The cost asymmetry is deliberate: a false positive costs a few seconds of human review; a false negative silently hides evidence from the investigation entirely.

**Q: How do you avoid hallucination in the AI-generated content (since this is evidence)?**
> By design choice, the image "context" description is **not** generative captioning — it's computed from measurable heuristics (orientation, brightness, dominant color, face count) specifically to avoid a model inventing details about evidentiary images. Similarly, the grammar-correction stage in the translation pipeline is gated by a content-word-overlap check (≥80%) against the pre-correction text — if the model appears to have paraphrased/dropped meaning rather than just fixing grammar, its output is discarded.

**Q: How does the Tanglish translator actually decide what's English vs Tanglish?**
> Word-frequency scoring (`wordfreq` Zipf scale) against an English-word threshold, plus a curated whitelist for contractions that frequency scoring alone would miss (`dont`, `im`), plus a hand-built set of common Tanglish function words that must always route to translation regardless of length. Crucially, routing decisions never determine *meaning* — meaning resolution happens later, over the whole clause, via NLLB — the classifier only decides which words get sent down which path.

**Q: Why NLLB over something like Google Translate's API?**
> Fully offline/local — no external API call, no data leaving the machine, no per-request cost, and no dependency on an internet connection during analysis. That's directly in line with the project's evidentiary-integrity stance.

### D. Data privacy, legal, and forensic soundness

**Q: How do you preserve chain of custody / evidentiary integrity?**
> Every media file gets SHA-256 hashed at parse time and that hash travels with the record through the whole pipeline into Postgres — if a file is later re-hashed and the digest doesn't match, tampering is provable. Combined with nothing ever leaving the local machine (no cloud AI calls), the evidentiary chain stays defensible.

**Q: Is any data sent to a third party / the cloud?**
> No. Every model used (Tesseract, Whisper, YuNet/SFace, CLIP, NLLB, the grammar model, the embedding model) runs locally; the only network activity is a one-time model-weight download on first use, cached afterward. This was a deliberate architectural constraint, not an accident.

**Q: What about admissibility of AI-translated or AI-tagged evidence in court?**
> Two answers, both honest: (1) the translation pipeline keeps a full per-stage trace (`StageTrace`) of every transformation applied to a piece of text, which supports an audit trail; (2) none of the AI outputs (tags, translations, face clusters) are presented as ground truth — they're investigative aids surfaced for human review, with the underlying raw data (original OCR text, original audio) always preserved alongside the derived output.

**Q: Is the frontend login secure?**
> No — and that's explicitly documented rather than hidden. It's a local-only mock with no real backend authentication, appropriate for a hackathon demo but flagged as a gap before any real deployment.

### E. Scalability & production readiness

**Q: Does this scale to a real forensic lab's caseload?**
> Not yet, by design — it currently processes one case at a time (documented limitation), background job state is in-memory (lost on restart), and there's no queueing system. The natural next step would be a real task queue (Celery/RQ) backed by persistent job storage, and per-case working directories for the extraction scripts (right now they share fixed filenames like `parsed_output.json`) to allow true concurrent processing.

**Q: What's the performance bottleneck?**
> The AI-heavy stages — Whisper transcription and CLIP/face-embedding inference — are CPU-bound in this configuration (`WHISPER_DEVICE = "cpu"`, `compute_type="int8"` deliberately chosen for a speed/accuracy tradeoff without a GPU). Swapping to GPU inference (`device="cuda"`) is a one-line config change if hardware allows it, and would be the first optimization for larger caseloads.

**Q: How would this handle a much larger UFDR export (say, 50,000 messages)?**
> Structurally, fine — Postgres with proper indexes on `case_id`/`timestamp` handles that scale trivially, and the vector index is upsert-based so it can grow incrementally. The bottleneck would be the media-heavy stages (OCR/transcription/image analysis), which are currently sequential per-file; batching or parallelizing those would be the next step.

### F. Security

**Q: How do you defend against a malicious UFDR upload (zip bomb, path traversal)?**
> Path traversal is actively defended — every zip member's extraction destination is resolved and checked against the target folder before extraction, and the whole upload is aborted if any entry tries to escape it ("zip-slip"). Filenames used to build folder paths are also sanitized to an alphanumeric/underscore/hyphen whitelist. Zip-bomb protection (extracted-size limits) isn't currently implemented — a fair follow-up question to be upfront about if asked directly.

**Q: What about SQL injection?**
> All queries use parameterized `psycopg` cursor execution (`%s` placeholders) — no string-interpolated SQL anywhere in `import_data.py` or the route handlers.

### G. Demo risk / "what if it breaks live"

**Q: What's your fallback if a live demo upload fails?**
> Have the bundled `backend/sample_ufdr/` case and a pre-processed case already sitting in Postgres/Qdrant as a backup — walk the judges through the dashboard/timeline/search on that data if the live pipeline run hits a flaky dependency (e.g., a cold-start model download taking too long on a hackathon Wi-Fi connection).

**Q: Why is the very first run slow?**
> First run downloads and caches several models (YuNet/SFace ONNX weights, CLIP checkpoint, and if using translation, the ~2.4GB NLLB weights) — everything after that is fully offline and fast. Worth pre-warming this before a live demo.

### H. Team / roadmap

**Q: What would you build next with more time?**
> In priority order: (1) wire `translate.py` fully into the automated pipeline and fix its working-directory dependency; (2) calibrate the CLIP evidence-tag threshold against real forensic sample data rather than the current placeholder; (3) add video support (ffprobe/moviepy, following the same pattern as audio); (4) real authentication and persistent (not in-memory) job tracking; (5) concurrent multi-case processing via per-case working directories and a real task queue.

---

## 8. Quick-reference cheat sheet (for the pitch)

- **7-stage local AI pipeline**: parse → OCR → translate → transcribe → image-analyze → import → index.
- **Zero cloud AI calls** — Tesseract, Whisper, CLIP, YuNet/SFace, NLLB, and the embedding model all run on-device.
- **Two database systems, each doing the job it's good at**: Postgres for structured/exact queries, Qdrant for semantic search.
- **SHA-256 hash per media file** for tamper-evidence.
- **Bespoke Tanglish→English NLP pipeline** — not a generic translator — with a full auditable per-stage trace.
- **Recall-biased, human-in-the-loop evidence tagging** — CLIP flags candidates, never delivers verdicts.
- **Heuristic (not generative) image context** — deliberately avoids hallucination risk on evidentiary images.
- **Path-traversal-safe upload handling** for untrusted zip archives.
- **Honest, documented limitations** (video unsupported, uncalibrated thresholds, mock auth, single-case-at-a-time) — a strength when a judge asks a pointed question, since the answer is already written down rather than improvised.
