import argparse
import json
import os
import sys
import urllib.request

import cv2
import numpy as np
from PIL import Image, ExifTags

PARSED_INPUT_PATH = "parsed_output.json"
OUTPUT_PATH = "image_analysis_output.json"
MEDIA_DIR = "sample_ufdr"          # image files live under here, per parser.py


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", default=MEDIA_DIR,
                    help=f"folder containing the media/ referenced by parsed_output.json (default: {MEDIA_DIR!r})")
    return p.parse_args()

MODELS_DIR = "models"
YUNET_PATH = os.path.join(MODELS_DIR, "face_detection_yunet.onnx")
SFACE_PATH = os.path.join(MODELS_DIR, "face_recognition_sface.onnx")
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

DARK_BRIGHTNESS_MAX = 70
BRIGHT_BRIGHTNESS_MIN = 180

# Faces closer than this cosine distance are treated as the same person.
# SFace's own docs suggest ~0.363 cosine distance as the same-person
# threshold at a low false-accept rate; we use the same value.
FACE_MATCH_DISTANCE_THRESHOLD = 0.363
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
CLIP_CACHE_DIR = os.path.join(MODELS_DIR, "clip_cache")  # keep under ./models like YuNet/SFace

EVIDENCE_LABELS = {
    "pills":              "a photo of pills or medication tablets",
    "drug_paraphernalia": "a photo of drug paraphernalia such as a pipe, syringe, scale, or baggie of powder",
    "firearm":            "a photo of a firearm or gun",
    "knife_or_blade":     "a photo of a knife or bladed weapon",
    "cash":               "a photo of cash or stacks of money",
    "financial_document": "a photo of a bank statement, financial document, or receipt",
    "id_document":        "a photo of an identification card, passport, or official document",
    "screenshot":         "a screenshot of a phone or computer screen",
}
EVIDENCE_BASELINE_PROMPT = "a photo"

# Recall-biased on purpose: a false positive costs a few seconds of analyst
# review; a false negative silently hides evidence. Not yet calibrated
# against real evidentiary photos -- the only sample image in this
# prototype is a placeholder graphic. Revisit before trusting this value.
TAG_CONFIDENCE_THRESHOLD = 0.25


# Loading parsed_output.json 

def load_parsed_data(path):
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run parser.py first to generate it.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_image_records(parsed_data):
    """Filter parsed media records down to successfully-parsed images."""
    media_records = parsed_data.get("media", [])
    return [
        m for m in media_records
        if m.get("type") == "image" and m.get("status") == "PARSED"
    ]


def resolve_media_path(record):
    """
    parser.py stores a filename/relative path per record — adjust the key
    below if your parsed_output.json uses a different field name
    (e.g. "path" instead of "filename").
    """
    filename = record.get("filename") or record.get("path")
    if filename is None:
        return None
    if filename.startswith(MEDIA_DIR):
        return filename
    return os.path.join(MEDIA_DIR, filename)


# Metadata 

def read_image_metadata(path):
    with Image.open(path) as img:
        metadata = {"width": img.width, "height": img.height, "format": img.format}

        exif_raw = img.getexif()
        if exif_raw:
            exif = {}
            for tag_id, value in exif_raw.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    continue
                exif[tag] = value
            if exif:
                metadata["exif"] = exif

        return metadata


#  Face detection + embedding (YuNet + SFace)

def _ensure_model(path, url):
    if not os.path.exists(path):
        os.makedirs(MODELS_DIR, exist_ok=True)
        print(f"  Downloading model to {path} ...")
        urllib.request.urlretrieve(url, path)


class FaceDetector:
    """Wraps YuNet (detection) + SFace (embedding); lazy-loaded singletons."""

    _detector = None
    _recognizer = None

    @classmethod
    def _get_detector(cls, image_size):
        _ensure_model(YUNET_PATH, YUNET_URL)
        if cls._detector is None:
            cls._detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (320, 320))
        cls._detector.setInputSize(image_size)
        return cls._detector

    @classmethod
    def _get_recognizer(cls):
        _ensure_model(SFACE_PATH, SFACE_URL)
        if cls._recognizer is None:
            cls._recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "")
        return cls._recognizer

    @classmethod
    def detect(cls, image_path):
        """Returns a list of {bbox, confidence, embedding} for each face found."""
        img = cv2.imread(image_path)
        if img is None:
            return []

        h, w = img.shape[:2]
        detector = cls._get_detector((w, h))
        _, faces = detector.detect(img)
        if faces is None:
            return []

        recognizer = cls._get_recognizer()
        results = []
        for face in faces:
            bbox = [round(float(v)) for v in face[0:4]]
            confidence = float(face[14])
            aligned = recognizer.alignCrop(img, face)
            embedding = recognizer.feature(aligned).flatten()
            results.append({"bbox": bbox, "confidence": confidence, "embedding": embedding})

        return results


def cluster_faces(all_faces):
    """
    Assigns a person_id to every face across the whole report.

    all_faces: list of {"media_id": ..., "bbox": ..., "confidence": ..., "embedding": ...}
    Returns (all_faces with "person_id" added, persons summary dict):
        {person_id: {"appearances": [media_id, ...], "face_count": N}}
    """
    if not all_faces:
        return all_faces, {}

    if len(all_faces) == 1:
        labels = [0]
    else:
        from sklearn.cluster import AgglomerativeClustering

        embeddings = np.stack([f["embedding"] for f in all_faces])
        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=FACE_MATCH_DISTANCE_THRESHOLD,
        )
        labels = clustering.fit_predict(embeddings)

    # Relabel clusters in order of first appearance so person_1 is always
    # whichever distinct face showed up first in the media list.
    first_seen_order = []
    for label in labels:
        if label not in first_seen_order:
            first_seen_order.append(label)
    label_to_person = {label: f"person_{i + 1}" for i, label in enumerate(first_seen_order)}

    persons = {}
    for face, label in zip(all_faces, labels):
        person_id = label_to_person[label]
        face["person_id"] = person_id
        face.pop("embedding", None)
        entry = persons.setdefault(person_id, {"appearances": [], "face_count": 0})
        entry["face_count"] += 1
        if face["media_id"] not in entry["appearances"]:
            entry["appearances"].append(face["media_id"])

    return all_faces, persons


#  Evidentiary tagging (CLIP zero-shot, fixed vocabulary) 

class EvidenceTagger:
    
    _model = None
    _processor = None
    _label_text_embeds = None

    @classmethod
    def _load(cls):
        if cls._model is None:
            from transformers import CLIPModel, CLIPProcessor
            import torch

            print(f"  Loading CLIP model ({CLIP_MODEL_NAME})... this only happens once.")
            cls._model = CLIPModel.from_pretrained(CLIP_MODEL_NAME, cache_dir=CLIP_CACHE_DIR)
            cls._model.eval()
            cls._processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME, cache_dir=CLIP_CACHE_DIR)

            prompts = list(EVIDENCE_LABELS.values()) + [EVIDENCE_BASELINE_PROMPT]
            text_inputs = cls._processor(text=prompts, return_tensors="pt", padding=True)
            with torch.no_grad():
                # transformers' CLIPModel returns the projected embedding in
                # .pooler_output (not a plain tensor) as of this version.
                text_embeds = cls._model.get_text_features(**text_inputs).pooler_output
            cls._label_text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)

        return cls._model, cls._processor

    @classmethod
    def classify(cls, image_path):
        """Returns {label: confidence} for every label in EVIDENCE_LABELS."""
        try:
            import torch
            model, processor = cls._load()

            image = Image.open(image_path).convert("RGB")
            image_inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                image_embeds = model.get_image_features(**image_inputs).pooler_output
            image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)

            logit_scale = model.logit_scale.exp()
            sims = (logit_scale * image_embeds @ cls._label_text_embeds.T).squeeze(0)
            baseline_sim = sims[-1]

            tags = {}
            for i, label in enumerate(EVIDENCE_LABELS):
                probs = torch.softmax(torch.stack([sims[i], baseline_sim]), dim=0)
                tags[label] = round(probs[0].item(), 4)
            return tags
        except Exception as e:
            print(f"  -> WARNING: CLIP tagging failed for {image_path}: {e}")
            return {}


# Context (lightweight heuristics, no generative captioning)

_COLOR_NAMES = ["red", "green", "blue"]


def _dominant_color_name(mean_bgr):
    b, g, r = mean_bgr
    channels = {"red": r, "green": g, "blue": b}
    top = max(channels, key=channels.get)
    spread = max(channels.values()) - min(channels.values())
    if spread < 15:
        return "neutral/grayscale"
    return top


def build_heuristic_context(image_path, metadata, face_count):
    
    img = cv2.imread(image_path)
    if img is None:
        return None

    width, height = metadata["width"], metadata["height"]
    if width > height:
        orientation = "landscape"
    elif height > width:
        orientation = "portrait"
    else:
        orientation = "square"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    if brightness <= DARK_BRIGHTNESS_MAX:
        brightness_label = "dark"
    elif brightness >= BRIGHT_BRIGHTNESS_MIN:
        brightness_label = "bright"
    else:
        brightness_label = "moderately lit"

    mean_bgr = [float(np.mean(img[:, :, i])) for i in range(3)]
    color_name = _dominant_color_name(mean_bgr)

    if face_count == 0:
        face_phrase = "no faces detected"
    elif face_count == 1:
        face_phrase = "1 face detected"
    else:
        face_phrase = f"{face_count} faces detected"

    return (
        f"{orientation} image, {width}x{height}, {brightness_label}, "
        f"predominantly {color_name} tones, {face_phrase}."
    )


# Pipeline

def analyze_all(image_records):
    analyses = []
    all_faces = []
    total = len(image_records)

    for i, record in enumerate(image_records, start=1):
        media_id = record.get("id")
        file_path = resolve_media_path(record)

        print(f"[{i}/{total}] Analyzing {media_id} ({file_path}) ...")

        if not file_path or not os.path.exists(file_path):
            print(f"  -> SKIPPED: file not found at {file_path}")
            continue

        metadata = read_image_metadata(file_path)
        faces = FaceDetector.detect(file_path)
        for face in faces:
            face["media_id"] = media_id
        all_faces.extend(faces)
        context = build_heuristic_context(file_path, metadata, len(faces))
        tags = EvidenceTagger.classify(file_path)

        analyses.append({
            "media_id": media_id,
            "metadata": metadata,
            "context": context,
            "face_count": len(faces),
            "tags": tags,
        })

    all_faces, persons = cluster_faces(all_faces)

    # Fold each face's resolved person_id back into its image's analysis entry.
    faces_by_media = {}
    for face in all_faces:
        faces_by_media.setdefault(face["media_id"], []).append({
            "person_id": face["person_id"],
            "bbox": face["bbox"],
            "confidence": round(face["confidence"], 4),
        })
    for analysis in analyses:
        analysis["faces"] = faces_by_media.get(analysis["media_id"], [])

    return analyses, persons


def main():
    global MEDIA_DIR
    args = parse_args()
    MEDIA_DIR = args.input_dir

    print("Loading parsed data...")
    parsed_data = load_parsed_data(PARSED_INPUT_PATH)

    image_records = get_image_records(parsed_data)
    print(f"Found {len(image_records)} image record(s) to analyze.")

    if not image_records:
        print("Nothing to analyze. Writing empty output file.")
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump({"images": [], "persons": {}}, f, indent=2)
        return

    analyses, persons = analyze_all(image_records)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"images": analyses, "persons": persons}, f, indent=2)

    print(f"\nDone. Analyzed {len(analyses)} image(s), found {len(persons)} distinct person(s).")
    for person_id, info in persons.items():
        print(f"  - {person_id}: seen in {info['appearances']}")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
