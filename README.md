# AI-ForenSight: Multimedia Forensic Video Analysis Pipeline

AI-ForenSight provides local, offline forensic video analysis, keyframe extraction, scene contextual classification, spoken dialogue transcription, and visual object/text extraction from digital evidence packages.

---

## Features

- **Forensic Video Metadata**: Extracts SHA-256 hash, duration, resolution, aspect ratio, frame rate, total frames, FourCC codec, and audio stream detection.
- **Audio Extraction & Dialogue Transcription**: Extracts normalized audio tracks and utilizes **Faster-Whisper** to transcribe spoken dialogue with sub-second timestamps and language detection.
- **Keyframe Extraction & Visual Object Detection**: Uses **YOLOv8** to detect and classify visual entities (people, vehicles, electronics, phones, etc.) across sampled keyframes with bounding boxes and confidence scores.
- **On-Screen OCR Text Extraction**: Uses **EasyOCR** to extract visible textual content from screen recordings, signs, banners, and documents within video frames.
- **Contextual Scene & Activity Classification**: Automatically infers scene context (e.g., *Screen Capture: Programming/Terminal Session*, *Screen Capture: Web Browsing*, *Surveillance/Outdoor Scene*, *Physical Real-World Scene*).
- **Unified Chronological Timeline**: Fuses audio speech events and visual frame activities into an ordered forensic event timeline.
- **Executive Forensic Summary**: Generates structured forensic summaries suitable for investigative reporting.

---

## Installation & Setup

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Pipeline Usage

### Run Video Analysis
Analyze any forensic video file (e.g. `sample_ufdr/media/video.mp4`):

```bash
python process_video.py sample_ufdr/media/video.mp4 video_analysis_output.json
```

### CLI Arguments
- `video_path`: Path to input video file (e.g., `sample_ufdr/media/video.mp4`).
- `-o, --output`: Path to output JSON analysis file (default: `<video_name>_analysis.json`).
- `--sample_fps`: Frames per second to sample for visual detection and OCR (default: `1.0`).
- `--whisper_model`: Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`, default: `base`).
- `--yolo_model`: YOLO model weights (default: `yolov8n.pt`).
- `--no_keyframes`: Flag to disable saving snapshot images to disk.

---

## Output Schema
The generated JSON report contains:
- `video_metadata`: Technical & integrity metadata (SHA-256, duration, dimensions, codecs).
- `video_summary`: Executive forensic summary and key metrics.
- `scene_and_context`: Contextual classification and inferred activity.
- `unified_chronological_timeline`: Integrated speech + visual event sequence.
- `audio_transcription`: Full transcript and timestamped speech segments.
- `visual_and_ocr_analysis`: Detected objects, bounding boxes, and OCR text per keyframe.
