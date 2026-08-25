"""
AI-ForenSight - Module: Translation Logging & Trace

Standard logging setup plus the StageTrace record used to build an
auditable trail of how each token/clause was classified and transformed.
Every stage tag is drawn from a fixed vocabulary (see STAGE_* constants)
so a reviewer can filter/audit by stage instead of parsing free-text logs.
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict

# ---- Fixed stage vocabulary ---------------------------------------------

STAGE_ENGLISH_DETECTION = "english_detection"
STAGE_SYMSPELL_CORRECTION = "symspell_correction"
STAGE_TANGLISH_DETECTION = "tanglish_detection"
STAGE_TANGLISH_LEXICON = "tanglish_lexicon"
STAGE_FALLBACK_TRANSLITERATION = "fallback_transliteration"
STAGE_LOW_CONFIDENCE_UNRESOLVED = "low_confidence_unresolved"
STAGE_NLLB_TRANSLATION = "nllb_translation"
STAGE_GRAMMAR_CORRECTION = "grammar_correction"

ALL_STAGES = {
    STAGE_ENGLISH_DETECTION,
    STAGE_SYMSPELL_CORRECTION,
    STAGE_TANGLISH_DETECTION,
    STAGE_TANGLISH_LEXICON,
    STAGE_FALLBACK_TRANSLITERATION,
    STAGE_LOW_CONFIDENCE_UNRESOLVED,
    STAGE_NLLB_TRANSLATION,
    STAGE_GRAMMAR_CORRECTION,
}


@dataclass
class StageTrace:
    stage: str
    input: str
    output: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.stage not in ALL_STAGES:
            raise ValueError(f"Unknown trace stage: {self.stage!r}")

    def as_dict(self):
        return asdict(self)


def get_logger(name):
    logger = logging.getLogger(name)
    return logger


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
