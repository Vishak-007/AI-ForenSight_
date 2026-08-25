"""
AI-ForenSight: Multimedia Forensic Video Analysis Pipeline.

Performs local, offline forensic video analysis, keyframe extraction,
scene contextual classification, spoken dialogue transcription with Whisper,
and visual object/text extraction (YOLO + EasyOCR).
"""

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import sys
import json
import hashlib
import argparse
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import torch
except ImportError:
    torch = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    import easyocr
except ImportError:
    easyocr = None


def get_optimal_device() -> str:
    """Detects available hardware acceleration (CUDA or CPU)."""
    if torch is not None and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 hash for evidentiary integrity."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_detailed_video_metadata(video_path: str) -> Dict[str, Any]:
    """Extracts forensic and technical metadata from video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc_val = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = "".join([chr((fourcc_val >> 8 * i) & 0xFF) for i in range(4)]).strip()
    duration = round(total_frames / fps, 2) if fps > 0 else 0.0
    cap.release()

    filesize = os.path.getsize(video_path)
    file_hash = compute_sha256(video_path)

    has_audio = False
    if imageio_ffmpeg is not None:
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            probe_cmd = [ffmpeg_exe, "-i", video_path]
            probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stderr_info = probe_res.stderr.lower()
            has_audio = any(tag in stderr_info for tag in ["audio:", "pcm_", "aac", "mp3", "opus", "vorbis"])
        except Exception:
            has_audio = False

    aspect_ratio = f"{round(width/height, 2)}:1" if height > 0 else "unknown"

    return {
        "filename": os.path.basename(video_path),
        "filepath": os.path.abspath(video_path),
        "sha256_hash": file_hash,
        "filesize_bytes": filesize,
        "filesize_human": f"{filesize / (1024*1024):.2f} MB",
        "duration_seconds": duration,
        "duration_formatted": f"{int(duration // 60):02d}:{int(duration % 60):02d}",
        "resolution": f"{width}x{height}",
        "aspect_ratio": aspect_ratio,
        "width": width,
        "height": height,
        "fps": round(fps, 2),
        "total_frames": total_frames,
        "fourcc_codec": codec if codec else "unknown",
        "has_audio_track": has_audio,
    }


def extract_audio(video_path: str, output_audio_path: str) -> bool:
    """Extracts normalized 16kHz mono WAV audio efficiently."""
    if imageio_ffmpeg is None:
        return False
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_audio_path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0 and os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000
    except Exception:
        return False


def clean_whisper_text(text: str) -> str:
    """Cleans up Whisper silence hallucination artifacts."""
    cleaned = text.strip()
    if not cleaned or set(cleaned).issubset({'.', ',', ' ', '!', '?', '-', '_', '?'}):
        return ""
    return cleaned


def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Transcribes audio using Faster-Whisper with speech segment timestamps."""
    if WhisperModel is None:
        return {
            "status": "UNAVAILABLE",
            "has_audible_speech": False,
            "error": "faster-whisper is not installed",
            "detected_language": None,
            "language_confidence": 0.0,
            "full_transcript": "",
            "segments": [],
        }

    if device is None:
        device = get_optimal_device()
    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"

    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)

        transcript_segments = []
        valid_texts = []
        for segment in segments:
            cleaned = clean_whisper_text(segment.text)
            if cleaned:
                valid_texts.append(cleaned)
                transcript_segments.append({
                    "start_time": f"{int(segment.start // 60):02d}:{int(segment.start % 60):02d}",
                    "start_seconds": round(segment.start, 2),
                    "end_seconds": round(segment.end, 2),
                    "text": cleaned,
                })

        full_transcript = " ".join(valid_texts)
        has_speech = len(full_transcript.strip()) > 0

        return {
            "status": "SUCCESS" if has_speech else "NO_SPEECH_DETECTED",
            "has_audible_speech": has_speech,
            "detected_language": info.language if (has_speech and hasattr(info, "language")) else None,
            "language_confidence": round(info.language_probability, 3) if (has_speech and hasattr(info, "language_probability")) else 0.0,
            "full_transcript": full_transcript,
            "segments": transcript_segments,
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "has_audible_speech": False,
            "error": str(e),
            "detected_language": None,
            "language_confidence": 0.0,
            "full_transcript": "",
            "segments": [],
        }


def analyze_visual_and_ocr(
    video_path: str,
    yolo_model: str = "yolov8n.pt",
    sample_fps: float = 1.0,
    conf_threshold: float = 0.35,
    save_keyframes: bool = True,
    keyframes_dir: Optional[str] = None,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """Frame processing for object detection and OCR text extraction."""
    if device is None:
        device = get_optimal_device()

    use_gpu = (device == "cuda")
    yolo = YOLO(yolo_model) if YOLO is not None else None
    ocr_reader = easyocr.Reader(['en'], gpu=use_gpu, verbose=False) if easyocr is not None else None

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {
            "status": "ERROR",
            "error": "Failed to open video file",
            "frame_analyses": [],
            "unique_objects_detected": [],
            "all_extracted_text": [],
        }

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, int(round(fps / sample_fps))) if sample_fps > 0 else 1

    if save_keyframes and keyframes_dir:
        os.makedirs(keyframes_dir, exist_ok=True)

    frame_analyses = []
    summary_objects: Dict[str, int] = {}
    unique_objects = set()
    all_seen_texts: List[str] = []
    analyzed_count = 0

    target_frame_indices = list(range(0, total_frames, frame_interval))

    for frame_idx in target_frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        analyzed_count += 1
        timestamp = round(frame_idx / fps, 2)
        time_formatted = f"{int(timestamp // 60):02d}:{int(timestamp % 60):02d}"

        # 1. Keyframe Image Save
        keyframe_rel_path = None
        if save_keyframes and keyframes_dir:
            kf_filename = f"keyframe_{analyzed_count:03d}_{int(timestamp)}s.jpg"
            kf_full_path = os.path.join(keyframes_dir, kf_filename)
            cv2.imwrite(kf_full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
            keyframe_rel_path = os.path.relpath(kf_full_path, os.path.dirname(keyframes_dir) or ".")

        # 2. YOLO Object Detection
        detected_objects = []
        if yolo is not None:
            try:
                yolo_results = yolo.predict(frame, conf=conf_threshold, verbose=False, device=device)
                for r in yolo_results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        label = yolo.names[cls_id]
                        confidence = round(float(box.conf[0].item()), 3)
                        xyxy = [round(float(coord), 1) for coord in box.xyxy[0].tolist()]

                        detected_objects.append({
                            "label": label,
                            "confidence": confidence,
                            "bounding_box": {
                                "x1": xyxy[0],
                                "y1": xyxy[1],
                                "x2": xyxy[2],
                                "y2": xyxy[3],
                            },
                        })
                        summary_objects[label] = summary_objects.get(label, 0) + 1
                        unique_objects.add(label)
            except Exception:
                pass

        # 3. OCR Text Extraction
        frame_texts = []
        if ocr_reader is not None:
            try:
                h, w = frame.shape[:2]
                max_dim = max(h, w)
                if max_dim > 1280:
                    scale = 1280.0 / max_dim
                    ocr_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                else:
                    ocr_frame = frame

                ocr_results = ocr_reader.readtext(ocr_frame)
                for bbox, text, prob in ocr_results:
                    text_clean = text.strip()
                    if len(text_clean) >= 2 and prob >= 0.35:
                        frame_texts.append({
                            "text": text_clean,
                            "confidence": round(float(prob), 3),
                        })
                        if text_clean not in all_seen_texts:
                            all_seen_texts.append(text_clean)
            except Exception:
                pass

        frame_analyses.append({
            "timestamp_seconds": timestamp,
            "timestamp_formatted": time_formatted,
            "frame_index": frame_idx,
            "keyframe_image": keyframe_rel_path,
            "detected_objects_count": len(detected_objects),
            "detected_objects": detected_objects,
            "visible_text_count": len(frame_texts),
            "visible_text": frame_texts,
        })

    cap.release()

    return {
        "status": "SUCCESS",
        "sample_fps": sample_fps,
        "total_frames_analyzed": analyzed_count,
        "unique_objects_detected": sorted(list(unique_objects)),
        "detected_objects_frequency": summary_objects,
        "distinct_text_snippets_found": len(all_seen_texts),
        "extracted_text_vocabulary": all_seen_texts[:50],
        "frame_analyses": frame_analyses,
    }


def infer_scene_context_and_activity(
    metadata: Dict[str, Any],
    visual_res: Dict[str, Any],
    audio_res: Dict[str, Any],
) -> Dict[str, Any]:
    """Infers forensic scene classification and contextual activity from multi-modal cues."""
    filename = metadata.get("filename", "").lower()
    objects = visual_res.get("unique_objects_detected", [])
    ocr_texts = " ".join(visual_res.get("extracted_text_vocabulary", [])).lower()

    is_screen_recording = any(k in filename for k in ["screen recording", "screencast", "capture"]) or \
                          any(k in ocr_texts for k in ["file", "edit", "terminal", "python", "git", "powershell", "cmd", "select-object", "localhost", "http"])
    is_surveillance_or_outdoor = any(obj in ["car", "truck", "bus", "traffic light", "motorcycle"] for obj in objects)

    if is_screen_recording:
        scene_type = "Screen Capture: Desktop / Application Interaction"
        scene_description = "The video captures computer desktop software usage, developer tools, or on-screen interface interactions."
    elif is_surveillance_or_outdoor:
        scene_type = "Outdoor / Traffic / Surveillance Footage"
        scene_description = "The video depicts outdoor or traffic environments with vehicular and pedestrian movements."
    elif "person" in objects:
        scene_type = "Human Subject / Indoor / Interaction"
        scene_description = "The video captures human subjects interacting in an indoor or camera-facing environment."
    else:
        scene_type = "General Media Video"
        scene_description = "Recorded video footage containing varied visual and contextual entities."

    return {
        "scene_classification": scene_type,
        "scene_description": scene_description,
        "detected_environment": "Desktop / Software UI" if is_screen_recording else "Physical Real-World Scene",
        "prominent_keywords_on_screen": visual_res.get("extracted_text_vocabulary", [])[:15],
    }


def generate_unified_timeline(audio_res: Dict[str, Any], visual_res: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Combines speech transcripts, visual objects, and OCR text into a unified forensic timeline."""
    events = []

    # 1. Spoken dialogue events
    for seg in audio_res.get("segments", []):
        events.append({
            "timestamp_seconds": seg["start_seconds"],
            "timestamp_formatted": seg["start_time"],
            "event_type": "audio_speech",
            "summary": f"Spoken: \"{seg['text']}\"",
            "details": {
                "transcript": seg["text"],
                "duration_seconds": round(seg["end_seconds"] - seg["start_seconds"], 2),
            },
        })

    # 2. Visual frame events (objects & OCR text)
    for frame in visual_res.get("frame_analyses", []):
        has_objs = len(frame.get("detected_objects", [])) > 0
        has_text = len(frame.get("visible_text", [])) > 0

        if has_objs or has_text:
            obj_labels = [o["label"] for o in frame.get("detected_objects", [])]
            text_snippets = [t["text"] for t in frame.get("visible_text", [])[:5]]

            summary_parts = []
            if obj_labels:
                summary_parts.append(f"Objects: {', '.join(set(obj_labels))}")
            if text_snippets:
                summary_parts.append(f"On-Screen Text: '{' | '.join(text_snippets)}'")

            events.append({
                "timestamp_seconds": frame["timestamp_seconds"],
                "timestamp_formatted": frame["timestamp_formatted"],
                "event_type": "visual_frame_activity",
                "keyframe_image": frame.get("keyframe_image"),
                "summary": " | ".join(summary_parts),
                "details": {
                    "objects": frame.get("detected_objects", []),
                    "visible_text": frame.get("visible_text", []),
                },
            })

    events.sort(key=lambda x: x["timestamp_seconds"])
    return events


def generate_video_summary(
    metadata: Dict[str, Any],
    scene_context: Dict[str, Any],
    audio_res: Dict[str, Any],
    visual_res: Dict[str, Any],
    timeline: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generates an executive forensic summary describing the video analysis results."""
    duration_str = metadata.get("duration_formatted", "00:00")
    unique_objs = visual_res.get("unique_objects_detected", [])
    has_speech = audio_res.get("has_audible_speech", False)

    if has_speech:
        lang = audio_res.get("detected_language", "unknown")
        audio_desc = f"Spoken dialogue detected in '{lang}' language ({len(audio_res.get('segments', []))} speech segments)."
    elif metadata.get("has_audio_track"):
        audio_desc = "Audio track is present with ambient sound/silence (no intelligible speech)."
    else:
        audio_desc = "Silent video (no audio track)."

    ocr_count = visual_res.get("distinct_text_snippets_found", 0)
    top_objs = [f"{k} ({v}x)" for k, v in visual_res.get("detected_objects_frequency", {}).items()]
    objs_str = f"Objects: {', '.join(top_objs)}" if top_objs else "No standard objects detected."
    text_str = f"Found {ocr_count} on-screen text snippet(s)." if ocr_count > 0 else "No prominent on-screen text."

    executive = (
        f"{scene_context['scene_description']} Duration: {duration_str}, "
        f"Resolution: {metadata.get('resolution')}. {objs_str} {text_str} {audio_desc}"
    )

    return {
        "executive_summary": executive,
        "scene_type": scene_context["scene_classification"],
        "scene_description": scene_context["scene_description"],
        "environment": scene_context["detected_environment"],
        "visual_summary": f"{objs_str} {text_str}",
        "audio_summary": audio_desc,
        "key_highlights": {
            "duration": duration_str,
            "detected_scene": scene_context["scene_classification"],
            "objects_found": unique_objs,
            "on_screen_text_snippets_count": ocr_count,
            "has_speech": has_speech,
            "total_timeline_events": len(timeline),
        },
    }


def analyze_video(
    video_path: str,
    output_json_path: Optional[str] = None,
    whisper_model: str = "base",
    yolo_model: str = "yolov8n.pt",
    sample_fps: float = 1.0,
    save_keyframes: bool = True,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """Main pipeline function to analyze a single video file."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    start_time = time.time()
    base_dir = os.path.dirname(os.path.abspath(output_json_path)) if output_json_path else os.getcwd()
    video_stem = os.path.splitext(os.path.basename(video_path))[0]
    keyframes_dir = os.path.join(base_dir, f"{video_stem}_keyframes")

    # 1. Metadata
    metadata = get_detailed_video_metadata(video_path)

    # 2. Audio Whisper
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
        tmp_audio_path = tmp_audio.name

    try:
        if metadata["has_audio_track"]:
            audio_extracted = extract_audio(video_path, tmp_audio_path)
            if audio_extracted:
                audio_result = transcribe_audio(tmp_audio_path, model_size=whisper_model, device=device)
            else:
                audio_result = {
                    "status": "SILENT_OR_EMPTY_AUDIO",
                    "has_audible_speech": False,
                    "detected_language": None,
                    "language_confidence": 0.0,
                    "full_transcript": "",
                    "segments": [],
                }
        else:
            audio_result = {
                "status": "NO_AUDIO_TRACK",
                "has_audible_speech": False,
                "detected_language": None,
                "language_confidence": 0.0,
                "full_transcript": "",
                "segments": [],
            }
    finally:
        if os.path.exists(tmp_audio_path):
            try:
                os.remove(tmp_audio_path)
            except OSError:
                pass

    # 3. Visual & OCR
    visual_result = analyze_visual_and_ocr(
        video_path=video_path,
        yolo_model=yolo_model,
        sample_fps=sample_fps,
        save_keyframes=save_keyframes,
        keyframes_dir=keyframes_dir,
        device=device,
    )

    # 4. Context & Scene
    scene_context = infer_scene_context_and_activity(metadata, visual_result, audio_result)

    # 5. Timeline & Summary
    timeline = generate_unified_timeline(audio_result, visual_result)
    summary = generate_video_summary(metadata, scene_context, audio_result, visual_result, timeline)

    analysis_output = {
        "video_metadata": metadata,
        "video_summary": summary,
        "scene_and_context": scene_context,
        "unified_chronological_timeline": timeline,
        "audio_transcription": audio_result,
        "visual_and_ocr_analysis": visual_result,
        "processing_metrics": {
            "execution_time_seconds": round(time.time() - start_time, 2),
            "device_used": device or get_optimal_device(),
            "sample_fps": sample_fps,
        },
    }

    if output_json_path:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(analysis_output, f, indent=2, ensure_ascii=False)
        print(f"Video analysis saved to: {output_json_path}")

    return analysis_output


def process_ufdr_videos(input_dir: str, output_path: str = "video_analysis_output.json"):
    """
    Scans a UFDR extraction folder for video files and processes each one.
    If no videos are found, produces a valid empty report.
    """
    media_dir = os.path.join(input_dir, "media") if os.path.exists(os.path.join(input_dir, "media")) else input_dir
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".webm"}
    video_files = []

    if os.path.exists(media_dir):
        for root, _, files in os.walk(media_dir):
            for file in files:
                if Path(file).suffix.lower() in video_extensions:
                    video_files.append(os.path.join(root, file))

    if not video_files:
        print(f"No video files found in '{input_dir}'. Writing empty video analysis report.")
        empty_report = {
            "status": "NO_VIDEOS_FOUND",
            "videos_count": 0,
            "videos": [],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(empty_report, f, indent=2)
        return empty_report

    print(f"Found {len(video_files)} video file(s) in '{input_dir}' to analyze.")
    results = []
    for v_path in video_files:
        try:
            res = analyze_video(v_path, output_json_path=None)
            results.append(res)
        except Exception as e:
            print(f"Failed to analyze video {v_path}: {e}")

    final_report = {
        "status": "SUCCESS",
        "videos_count": len(results),
        "videos": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    print(f"Batch video analysis saved to: {output_path}")
    return final_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-ForenSight Forensic Video Processing")
    parser.add_argument("video_path", nargs="?", default=None, help="Path to single video file")
    parser.add_argument("output", nargs="?", default=None, help="Output JSON path")
    parser.add_argument("--input-dir", default=None, help="UFDR directory containing media/ folder")
    parser.add_argument("--output-file", default="video_analysis_output.json", help="Output JSON path")
    args = parser.parse_args()

    if args.input_dir:
        process_ufdr_videos(args.input_dir, args.output_file)
    elif args.video_path:
        out = args.output or args.output_file
        analyze_video(args.video_path, out)
    else:
        # Default fallback to check sample_ufdr
        if os.path.exists("sample_ufdr"):
            process_ufdr_videos("sample_ufdr", "video_analysis_output.json")
        else:
            parser.print_help()
