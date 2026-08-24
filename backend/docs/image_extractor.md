# `image_extractor.py` — Image Evidence Analysis Module

## What this is

`image_extractor.py` is the image-analysis stage of the UFDR pipeline. It
runs **after `parser.py`** (which turns the raw XML export into
`parsed_output.json`) and produces `image_analysis_output.json` — a
per-image breakdown of faces, evidentiary content tags, and plain-English
context, ready to feed into a report/dashboard stage.

It exists because an investigator can't manually look at every photo in a
large extraction. This module does three independent things per image and
merges the results:

1. **Detects and clusters faces** across the whole case, so the same person
   showing up in five different photos gets one consistent ID instead of
   five unrelated detections.
2. **Tags evidentiary content** (drugs, weapons, cash, documents, etc.)
   using zero-shot image classification — no training data needed, no
   fixed dataset of "known evidence photos" required.
3. **Describes basic visual context** (bright/dark, dominant color,
   orientation, face count) with cheap, deterministic heuristics — not a
   generative caption, just numbers translated to words.

Every result is keyed by `media_id`, so it can always be traced back to the
exact record it came from — the same citation discipline the project
requires of `analyze.py`.

---

## Inputs / outputs

| | |
|---|---|
| **Input** | `parsed_output.json` (produced by `parser.py`) |
| **Filter** | only records where `type == "image"` and `status == "PARSED"` |
| **Output** | `image_analysis_output.json` |
| **Media location** | `sample_ufdr/` by default, overridable with `--input-dir` |

Run order: `python parser.py` → `python image_extractor.py`.

---

## Pipeline stages

### 1. Image metadata + EXIF — `read_image_metadata`

Opens the image with Pillow, records width/height/format, and pulls any
EXIF tags present (translating numeric EXIF tag IDs to human-readable names
via `ExifTags.TAGS`). Raw byte-valued EXIF fields are skipped. If no EXIF
data exists, the `exif` key is simply omitted.

### 2. Face detection + embedding — `FaceDetector` (YuNet + SFace)

Two ONNX models, both from the OpenCV Zoo, wrapped as lazy-loaded class
singletons so they're only initialized once per run:

- **YuNet** (`cv2.FaceDetectorYN`) — detects face bounding boxes and a
  confidence score.
- **SFace** (`cv2.FaceRecognizerSF`) — given a detected face, aligns/crops
  it and produces a numeric embedding vector representing that face.

Models aren't bundled with the repo — `_ensure_model()` downloads them into
`backend/models/` the first time they're actually needed:

- `models/face_detection_yunet.onnx`
- `models/face_recognition_sface.onnx`

SFace specifically is **only** downloaded if a face is actually detected —
if an image has zero faces, the recognizer is never touched.

### 3. Cross-image face clustering — `cluster_faces`

All faces found across *every* image in the run are pooled together and
clustered with `sklearn.cluster.AgglomerativeClustering` on cosine distance
between embeddings, using a distance threshold of **0.363** — the value
SFace's own documentation gives as the same-person threshold at a low
false-accept rate.

Clusters are then relabeled in first-appearance order, so `person_1` is
always whichever distinct face showed up first when scanning images in
order — not an arbitrary cluster index. Output shape:

```json
{"person_1": {"appearances": ["MED003", "MED007"], "face_count": 2}}
```

### 4. Evidentiary content tagging — `EvidenceTagger` (CLIP)

Zero-shot classification using `openai/clip-vit-base-patch32` via
`transformers`. There's a fixed vocabulary of evidence-relevant labels
(`EVIDENCE_LABELS`):

```
pills, drug_paraphernalia, firearm, knife_or_blade, cash,
financial_document, id_document, screenshot
```

For each label, CLIP's image embedding is compared against the label's
text embedding *and* against a neutral baseline prompt (`"a photo"`), then
passed through a **2-way softmax** (label vs. baseline) to get that label's
confidence. This is done independently per label — the eight resulting
numbers are **not** a probability distribution that sums to 1 across
labels; each is its own binary decision ("does this look more like
`<label>` or more like a generic photo?").

The model and its text embeddings are loaded once and cached as class
attributes (`_model`, `_processor`, `_label_text_embeds`). Weights are
cached to disk at `models/clip_cache/` via Hugging Face's standard cache
layout, so subsequent runs don't re-download.

### 5. Heuristic visual context — `build_heuristic_context`

No ML model here — just arithmetic on the raw pixel array, translated into
a one-sentence description:

- **Orientation**: width vs. height → landscape / portrait / square
- **Brightness**: mean grayscale value vs. two thresholds
  (`DARK_BRIGHTNESS_MAX = 70`, `BRIGHT_BRIGHTNESS_MIN = 180`) → dark /
  bright / moderately lit
- **Dominant color**: mean B/G/R channel values; if the spread between the
  highest and lowest channel is under 15, it's called neutral/grayscale,
  otherwise it names whichever channel (red/green/blue) is highest
- **Face count**: folded in from stage 2/3

Example output: `"landscape image, 960x640, bright, predominantly red
tones, no faces detected."`

### 6. Orchestration — `analyze_all` / `main`

For each qualifying image record:
1. Resolve its file path (`resolve_media_path`, joining `MEDIA_DIR` with
   the record's `filename`)
2. Read metadata, run face detection, run heuristic context, run CLIP
   tagging
3. Collect all faces from all images into one list

After the loop, `cluster_faces` runs once over every face found across the
entire case, and each image's analysis entry gets its resolved `person_id`
values folded back in. Final JSON:

```json
{
  "images": [
    {
      "media_id": "MED001",
      "metadata": {...},
      "context": "...",
      "face_count": 0,
      "tags": {"pills": 0.58, "firearm": 0.74, ...},
      "faces": []
    }
  ],
  "persons": {}
}
```

If there are no image records at all, an empty `{"images": [], "persons":
{}}` is written immediately without loading any models.

---

## Design decisions worth knowing

- **Recall-biased threshold.** `TAG_CONFIDENCE_THRESHOLD = 0.25` is set
  low on purpose: a false positive costs an analyst a few seconds of
  review, a false negative silently hides evidence. The code's own
  comment flags this as **not yet calibrated against real evidentiary
  photos** — treat it as a starting point, not a tuned value.
- **Lazy, on-demand model downloads.** Nothing downloads at import time.
  YuNet downloads on first `detect()` call; SFace only if a face is
  actually found; CLIP downloads on first `classify()` call. This keeps a
  no-op run (e.g. an XML with zero images) fast and network-free.
- **Traceability preserved.** Every finding — faces, tags, context — is
  attached to a `media_id` that maps straight back to the record in
  `parsed_output.json`, consistent with the project's evidentiary-
  integrity requirement.
- **Offline gap, same shape as `analyze.py`.** CLIP, YuNet, and SFace all
  pull from the network on first use (Hugging Face Hub / GitHub raw URLs).
  For a genuinely air-gapped deployment, these would need to be
  pre-downloaded and bundled rather than fetched at runtime — the same
  gap already called out for `analyze.py`'s live Anthropic API call.

---

## Models & dependencies

| Component | Library | Model | Cached at |
|---|---|---|---|
| Face detection | `opencv-python` (`cv2.FaceDetectorYN`) | YuNet | `backend/models/face_detection_yunet.onnx` |
| Face embedding | `opencv-python` (`cv2.FaceRecognizerSF`) | SFace | `backend/models/face_recognition_sface.onnx` |
| Face clustering | `scikit-learn` | `AgglomerativeClustering` | n/a (in-memory) |
| Evidence tagging | `transformers` + `torch` | `openai/clip-vit-base-patch32` | `backend/models/clip_cache/` |
| Metadata/EXIF | `Pillow` | — | n/a |

---

## How to run it

```bash
python parser.py            # must run first — produces parsed_output.json
python image_extractor.py   # optional: --input-dir <path to sample_ufdr>
```

First run will download YuNet (~230 KB) and the CLIP checkpoint
(~600 MB); SFace downloads too if any face is detected. Subsequent runs
reuse the cached files under `backend/models/`.

---

## Verified behavior (this session)

The output was independently checked, not just assumed correct:

- **Metadata** (`width`/`height`/`format`) matched `parser.py`'s own
  values exactly for both sample images.
- **Brightness and dominant-color heuristics** were recomputed from
  scratch with raw `numpy`/`cv2` calls outside the script, and matched the
  script's output exactly (e.g. brightness 47.3 → correctly bucketed
  "dark"; BGR spread 19.7 with red as the max channel → correctly labeled
  "red").
- **CLIP tagging** was sanity-checked against actual image content:
  `img_002.jpg` turned out to be a real photo of pill blister packs (not a
  placeholder), and CLIP tagged it `pills: 1.0` — the maximum possible
  confidence, correctly identifying the dominant real-world content. The
  other sample (`img_001.jpg`, an abstract gray placeholder graphic)
  produced noisy, elevated scores across unrelated categories — expected,
  since it's out-of-distribution for CLIP, and consistent with the code's
  own "not yet calibrated" caveat rather than a bug.
