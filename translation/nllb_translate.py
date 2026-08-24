"""
AI-ForenSight - Module: Tamil -> English Translation (NLLB)

Translates a COMPLETE normalized clause (Tamil script, possibly with
inline English loanwords left in Latin script) into English using a
locally-run NLLB model. This function must never be called with a single
isolated word - the pipeline always assembles a full clause first so the
model has enough context to resolve ambiguous function words correctly.
"""

from .errors import ModelLoadError, MissingDependencyError
from .logging_utils import get_logger, StageTrace, STAGE_NLLB_TRANSLATION
from . import config

logger = get_logger(__name__)

_model = None
_tokenizer = None
_load_attempted = False


def _get_model_and_tokenizer():
    global _model, _tokenizer, _load_attempted
    if _load_attempted:
        if _model is None:
            raise ModelLoadError(
                config.NLLB_MODEL_NAME,
                "Previous load attempt failed - see earlier log output.",
            )
        return _model, _tokenizer
    _load_attempted = True

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as exc:
        raise MissingDependencyError(
            "transformers", extra="Also requires: pip install torch sentencepiece"
        ) from exc

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            config.NLLB_MODEL_NAME, src_lang=config.NLLB_SRC_LANG
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(config.NLLB_MODEL_NAME)
    except OSError as exc:
        raise ModelLoadError(
            config.NLLB_MODEL_NAME,
            "Could not download/load the model. Ensure you have internet "
            "access for the first run (the model is cached locally "
            "afterward), or pre-download it with:\n"
            f"  huggingface-cli download {config.NLLB_MODEL_NAME}",
        ) from exc

    _model = model
    _tokenizer = tokenizer
    logger.info("Loaded NLLB model '%s'", config.NLLB_MODEL_NAME)
    return _model, _tokenizer


def translate_ta_to_en(tamil_text):
    """Translate one complete Tamil-script clause into English.

    Returns (english_text: str, trace: StageTrace).
    """
    if not tamil_text.strip():
        return "", StageTrace(STAGE_NLLB_TRANSLATION, tamil_text, "",
                               {"reason": "empty_input"})

    model, tokenizer = _get_model_and_tokenizer()

    inputs = tokenizer(tamil_text, return_tensors="pt")
    target_lang_id = tokenizer.convert_tokens_to_ids(config.NLLB_TGT_LANG)
    generated = model.generate(
        **inputs, forced_bos_token_id=target_lang_id, max_new_tokens=256
    )
    english_text = tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()

    logger.debug("NLLB: '%s' -> '%s'", tamil_text, english_text)
    trace = StageTrace(STAGE_NLLB_TRANSLATION, tamil_text, english_text,
                        {"model": config.NLLB_MODEL_NAME})
    return english_text, trace
