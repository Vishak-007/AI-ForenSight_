# AI-ForenSight: UFDR Parser & OCR Transcription Pipeline

AI-ForenSight provides local, offline forensic parsing and automated text extraction from UFDR (Universal Forensic Data Extraction) packages.

---

## Features

- **UFDR Data Parsing (`parser.py`)**: Normalizes messages, contacts, calls, and media items from `report.xml`.
- **Evidentiary Integrity**: Computes SHA-256 hashes for all media files to detect tampering.
- **Media Metadata Extraction**: Extracts format, dimensions, duration, and sampling rate for image, audio, and PDF media.
- **Local Document OCR (`ocr_transcribe.py`)**: Uses Tesseract OCR and PyMuPDF to extract text from image documents (`.png`, `.jpg`) and PDF documents page-by-page.
- **Tanglish → English Translation (`translate.py`)**: Converts code-mixed/romanized Tamil ("Tanglish") transcript text into fluent English via a local, offline NLP pipeline (NER protection, wordfreq, SymSpell, Tanglish lexicon + rule-based transliteration, NLLB, grammar correction).

---

## Installation & Setup

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Tesseract OCR (Windows):**
   - Download Tesseract OCR installer for Windows and install to default path (`C:\Program Files\Tesseract-OCR\tesseract.exe`).

3. **Download the spaCy English model (for entity protection in `translate.py`):**
   ```bash
   python -m spacy download en_core_web_sm
   ```

---

## Pipeline Usage

### Step 1: Parse UFDR Export
Run the UFDR XML parser to validate evidentiary hashes and normalize structure:
```bash
python parser.py
```
* **Input:** `sample_ufdr/report.xml` and media files under `sample_ufdr/media/`
* **Output:** `parsed_output.json`

### Step 2: Perform Document OCR
Transcribe document entries extracted during parsing:
```bash
python ocr_transcribe.py
```
* **Input:** `parsed_output.json`
* **Output:** `ocr_output.json`

### Step 3: Translate Tanglish Transcripts to English
Convert each document's OCR transcript from Tanglish/code-mixed Tamil into fluent English:
```bash
python translate.py
```
* **Input:** `ocr_output.json`
* **Output:** `translated_output.json` (each document keeps `raw_transcript`, adds `final_english` and a per-stage `translation_trace` for audit)

**Notes:**
- Fully offline after first run. The NLLB (`facebook/nllb-200-distilled-600M`, ~2.4GB) and grammar-correction models download from Hugging Face once, then run locally.
- No custom model training is used or required — every model is a pretrained, off-the-shelf inference model.
- See `translation/config.py` to swap models or tune thresholds, and `translation/config.py`'s `TANGLISH_LEXICON` to extend word coverage.
- **Known limitation**: clauses where a Tamil discourse filler (e.g. "na") repeats multiple times can transliterate into ungrammatical literal Tamil, which the distilled 600M NLLB checkpoint sometimes mistranslates into an unrelated sentence instead of the intended meaning (see `tests/test_translation_pipeline.py::test_slang_code_mixed`, marked `xfail`). A larger NLLB checkpoint (`facebook/nllb-200-1.3B`+) may improve this at the cost of a bigger download and slower CPU inference — swap `NLLB_MODEL_NAME` in `translation/config.py` to try it.
