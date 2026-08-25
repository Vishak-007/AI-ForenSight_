"""
AI-ForenSight - Module: Final Sentence-level Grammar Correction

Reads the fully reconstructed sentence (still containing entity
placeholders) as a whole and fixes grammar/word-order/missing auxiliary
verbs/articles/prepositions where necessary - without inventing new
information or over-formalizing already-correct English.

Includes two safety nets, either of which discards the model's output and
falls back to the pre-correction text:
  1. Entity-integrity check: the set of __ENTn__ placeholders must be
     unchanged (protects names/places/numbers from being dropped/altered).
  2. Content-word-overlap check: most of the sentence's non-stopword words
     must still appear in the output (protects against a model that
     paraphrases/drops meaning instead of making minimal grammar fixes -
     this is exactly the failure mode that ruled out an earlier model
     choice, pszemraj/grammar-synthesis-small, which rewrote "tomorrow"
     to "next week" and silently dropped "work").
"""

import re

from .errors import ModelLoadError, MissingDependencyError
from .logging_utils import get_logger, StageTrace, STAGE_GRAMMAR_CORRECTION
from . import config
from .tokenizer import tokenize, is_word
from .ner import is_placeholder

logger = get_logger(__name__)

_PLACEHOLDER_RE = re.compile(r"__ENT\d+__")


def _content_words(text):
    """Words that must survive grammar correction, excluding stopwords AND
    contractions like "ill"/"im"/"dont" - the latter are pronoun+verb
    function-word combinations (I'll = I + will, I'm = I + am, don't = do
    + not), so a correction that expands "ill" into "I will" is preserving
    meaning, not dropping a content word, even though "ill" itself isn't
    in GRAMMAR_STOPWORDS (confirmed empirically: this exact case - "ill"
    expanding to "I will" - was wrongly flagged as content loss before this
    exclusion was added, discarding an otherwise-correct model output)."""
    tokens = [t for t in tokenize(text) if is_word(t) and not is_placeholder(t)]
    excluded = config.GRAMMAR_STOPWORDS | config.CONTRACTION_WHITELIST
    return {t.lower() for t in tokens if t.lower() not in excluded}


def _content_overlap_ratio(original, corrected):
    original_words = _content_words(original)
    if not original_words:
        return 1.0
    corrected_words = _content_words(corrected)
    return len(original_words & corrected_words) / len(original_words)

_model = None
_tokenizer = None
_load_attempted = False


def _get_model_and_tokenizer():
    global _model, _tokenizer, _load_attempted
    if _load_attempted:
        if _model is None:
            raise ModelLoadError(
                config.GRAMMAR_MODEL_NAME,
                "Previous load attempt failed - see earlier log output.",
            )
        return _model, _tokenizer
    _load_attempted = True

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as exc:
        raise MissingDependencyError(
            "transformers", extra="Also requires: pip install torch"
        ) from exc

    try:
        tokenizer = AutoTokenizer.from_pretrained(config.GRAMMAR_MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(config.GRAMMAR_MODEL_NAME)
    except OSError as exc:
        raise ModelLoadError(
            config.GRAMMAR_MODEL_NAME,
            "Could not download/load the model. Ensure you have internet "
            "access for the first run (the model is cached locally "
            "afterward).",
        ) from exc

    _model = model
    _tokenizer = tokenizer
    logger.info("Loaded grammar-correction model '%s'", config.GRAMMAR_MODEL_NAME)
    return _model, _tokenizer


def correct_sentence(sentence):
    """Return (corrected_sentence: str, trace: StageTrace).

    Falls back to the original `sentence` unchanged if the model's output
    fails the entity-placeholder integrity check.
    """
    if not sentence.strip():
        return sentence, StageTrace(STAGE_GRAMMAR_CORRECTION, sentence, sentence,
                                     {"reason": "empty_input"})

    model, tokenizer = _get_model_and_tokenizer()

    inputs = tokenizer(
        config.GRAMMAR_MODEL_PROMPT_PREFIX + sentence,
        return_tensors="pt", truncation=True,
    )
    generated = model.generate(**inputs, max_new_tokens=256)
    corrected = tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()

    original_placeholders = sorted(_PLACEHOLDER_RE.findall(sentence))
    corrected_placeholders = sorted(_PLACEHOLDER_RE.findall(corrected))

    if original_placeholders != corrected_placeholders:
        logger.warning(
            "Grammar correction altered entity placeholders (%s -> %s); "
            "falling back to pre-correction text for safety.",
            original_placeholders, corrected_placeholders,
        )
        trace = StageTrace(STAGE_GRAMMAR_CORRECTION, sentence, sentence, {
            "reason": "entity_integrity_check_failed",
            "model_output_discarded": corrected,
        })
        return sentence, trace

    overlap = _content_overlap_ratio(sentence, corrected)
    if overlap < config.GRAMMAR_MIN_CONTENT_WORD_OVERLAP:
        logger.warning(
            "Grammar correction dropped too much content (overlap=%.2f < %.2f) "
            "-> '%s'; falling back to pre-correction text for safety.",
            overlap, config.GRAMMAR_MIN_CONTENT_WORD_OVERLAP, corrected,
        )
        trace = StageTrace(STAGE_GRAMMAR_CORRECTION, sentence, sentence, {
            "reason": "content_overlap_check_failed",
            "content_overlap_ratio": overlap,
            "model_output_discarded": corrected,
        })
        return sentence, trace

    logger.debug("Grammar correction: '%s' -> '%s'", sentence, corrected)
    trace = StageTrace(STAGE_GRAMMAR_CORRECTION, sentence, corrected, {
        "model": config.GRAMMAR_MODEL_NAME,
        "entity_integrity_check": "passed",
        "content_overlap_ratio": overlap,
    })
    return corrected, trace
