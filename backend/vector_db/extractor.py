import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]

OCR_SKIP_MARKER = "[OCR Skipped"

TAG_CONFIDENCE_THRESHOLD = 0.25


@dataclass
class SearchableRecord:
    source_type: str          # message | ocr_document | audio_transcript | image_context | image_tags | image_ocr
    source_table: str         # PostgreSQL table this content ultimately lands in
    business_id: str          # UFDR-level id (message_id or media_id)
    media_id: Optional[str]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_case_ref(parsed_data: dict[str, Any], override: Optional[str]) -> str:
    if override:
        return override
    device_id = (parsed_data.get("device_info") or {}).get("device_id")
    if not device_id:
        raise ValueError(
            "parsed_output.json has no device_info.device_id; pass --case-id explicitly"
        )
    return device_id


def extract_records(backend_dir: Path = BACKEND_DIR) -> list[SearchableRecord]:
    parsed = _load(backend_dir / "parsed_output.json")
    ocr = _load(backend_dir / "ocr_output.json")
    transcripts = _load(backend_dir / "transcripts_output.json")
    image_analysis = _load(backend_dir / "image_analysis_output.json")
    translated = _load(backend_dir / "translated_output.json")

    translated_by_media = {
        doc["media_id"]: doc["final_english"].strip()
        for doc in translated.get("documents", [])
        if doc.get("media_id") and (doc.get("final_english") or "").strip()
    }

    records: list[SearchableRecord] = []

    for msg in parsed.get("messages", []):
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        records.append(SearchableRecord(
            source_type="message",
            source_table="messages",
            business_id=msg["id"],
            media_id=None,
            text=text,
            metadata={
                "sender": msg.get("sender"),
                "receiver": msg.get("receiver"),
                "timestamp": msg.get("timestamp"),
            },
        ))

    for doc in ocr.get("documents", []):
        raw_text = (doc.get("transcript_text") or "").strip()
        if not raw_text or raw_text.startswith(OCR_SKIP_MARKER):
            continue
        translated_text = translated_by_media.get(doc["media_id"])
        text = translated_text or raw_text
        records.append(SearchableRecord(
            source_type="ocr_document",
            source_table="ocr_results",
            business_id=doc["media_id"],
            media_id=doc["media_id"],
            text=text,
            metadata={"filename": doc.get("filename"), "translated": bool(translated_text)},
        ))

    for tr in transcripts.get("transcripts", []):
        text = (tr.get("text") or "").strip()
        if not text:
            continue
        records.append(SearchableRecord(
            source_type="audio_transcript",
            source_table="transcriptions",
            business_id=tr["media_id"],
            media_id=tr["media_id"],
            text=text,
            metadata={"language": tr.get("language")},
        ))

    for img in image_analysis.get("images", []):
        media_id = img["media_id"]

        context = (img.get("context") or "").strip()
        if context:
            records.append(SearchableRecord(
                source_type="image_context",
                source_table="image_analysis",
                business_id=media_id,
                media_id=media_id,
                text=context,
                metadata={
                    "face_count": img.get("face_count"),
                    "image_metadata": img.get("metadata"),
                },
            ))

        ocr_text_raw = (img.get("ocr_text") or "").strip()
        if ocr_text_raw and not ocr_text_raw.startswith(OCR_SKIP_MARKER):
            translated_text = translated_by_media.get(media_id)
            text = translated_text or ocr_text_raw
            records.append(SearchableRecord(
                source_type="image_ocr",
                source_table="ocr_results",
                business_id=media_id,
                media_id=media_id,
                text=text,
                metadata={"translated": bool(translated_text)},
            ))

        tags = {
            tag: confidence
            for tag, confidence in (img.get("tags") or {}).items()
            if confidence >= TAG_CONFIDENCE_THRESHOLD
        }
        if tags:
            ranked = sorted(tags.items(), key=lambda kv: kv[1], reverse=True)
            tag_text = "Possible evidentiary content: " + ", ".join(
                f"{tag} ({confidence:.2f})" for tag, confidence in ranked
            )
            records.append(SearchableRecord(
                source_type="image_tags",
                source_table="image_tags",
                business_id=media_id,
                media_id=media_id,
                text=tag_text,
                metadata={"tags": tags},
            ))

    return records
