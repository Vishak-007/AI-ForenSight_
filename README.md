# AI-ForenSight: UFDR Parser & OCR Transcription Pipeline

AI-ForenSight provides local, offline forensic parsing and automated text extraction from UFDR (Universal Forensic Data Extraction) packages.

---

## Features

- **UFDR Data Parsing (`parser.py`)**: Normalizes messages, contacts, calls, and media items from `report.xml`.
- **Evidentiary Integrity**: Computes SHA-256 hashes for all media files to detect tampering.
- **Media Metadata Extraction**: Extracts format, dimensions, duration, and sampling rate for image, audio, and PDF media.
- **Local Document OCR (`ocr_transcribe.py`)**: Uses Tesseract OCR and PyMuPDF to extract text from image documents (`.png`, `.jpg`) and PDF documents page-by-page.

---

## Installation & Setup

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Tesseract OCR (Windows):**
   - Download Tesseract OCR installer for Windows and install to default path (`C:\Program Files\Tesseract-OCR\tesseract.exe`).

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
