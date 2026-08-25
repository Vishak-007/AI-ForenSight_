"""
AI-ForenSight - Module: English-word Detection

Decides whether a token should be treated as English (kept, then
SymSpell-checked) or as Tanglish/non-English (routed to transliteration).
Uses wordfreq's frequency data as the general-purpose signal, with two
override sets from config.py that take precedence for tokens wordfreq
would otherwise get wrong.

Word-level here means "classification and routing" only - never
translation itself (that always happens later, at clause level).
"""

from .logging_utils import get_logger, StageTrace, STAGE_ENGLISH_DETECTION
from . import config
from .errors import MissingDependencyError
from .tokenizer import is_word
from . import spellcheck

logger = get_logger(__name__)

_REASON_WHITELIST = "contraction_whitelist"
_REASON_TANGLISH_OVERRIDE = "tanglish_function_word_override"
_REASON_WORDFREQ = "wordfreq_threshold"
_REASON_LIKELY_ENGLISH_TYPO = "likely_english_typo"
_REASON_NOT_A_WORD = "not_a_word"


def _zipf_frequency(word):
    try:
        from wordfreq import zipf_frequency
    except ImportError as exc:
        raise MissingDependencyError("wordfreq") from exc
    return zipf_frequency(word, "en")


def is_english_word(token):
    """Return (is_english: bool, trace: StageTrace) for a single token."""
    lowered = token.lower()

    if not is_word(token):
        trace = StageTrace(STAGE_ENGLISH_DETECTION, token, "n/a",
                            {"reason": _REASON_NOT_A_WORD})
        return True, trace  # punctuation/whitespace passes through untouched

    if lowered in config.KNOWN_TANGLISH_FUNCTION_WORDS:
        trace = StageTrace(STAGE_ENGLISH_DETECTION, token, "non_english",
                            {"reason": _REASON_TANGLISH_OVERRIDE})
        logger.debug("'%s' -> non-English (%s)", token, _REASON_TANGLISH_OVERRIDE)
        return False, trace

    if lowered in config.CONTRACTION_WHITELIST:
        trace = StageTrace(STAGE_ENGLISH_DETECTION, token, "english",
                            {"reason": _REASON_WHITELIST})
        logger.debug("'%s' -> English (%s)", token, _REASON_WHITELIST)
        return True, trace

    zipf = _zipf_frequency(lowered)
    if zipf >= config.ENGLISH_ZIPF_THRESHOLD:
        trace = StageTrace(STAGE_ENGLISH_DETECTION, token, "english",
                            {"reason": _REASON_WORDFREQ, "zipf": zipf})
        logger.debug("'%s' -> English (zipf=%.2f)", token, zipf)
        return True, trace

    # Low/zero corpus frequency could mean genuine Tanglish, OR an English
    # word misspelled badly enough that wordfreq doesn't recognize it (a
    # typo has its own near-zero frequency). A very close (edit distance 1)
    # match to a real English dictionary word is a strong signal it's the
    # latter - romanized Tamil is rarely one edit away from an English word.
    if spellcheck.has_close_english_match(lowered):
        trace = StageTrace(STAGE_ENGLISH_DETECTION, token, "english",
                            {"reason": _REASON_LIKELY_ENGLISH_TYPO, "zipf": zipf})
        logger.debug("'%s' -> English (%s, zipf=%.2f)",
                     token, _REASON_LIKELY_ENGLISH_TYPO, zipf)
        return True, trace

    trace = StageTrace(STAGE_ENGLISH_DETECTION, token, "non_english",
                        {"reason": _REASON_WORDFREQ, "zipf": zipf})
    logger.debug("'%s' -> non-English (zipf=%.2f)", token, zipf)
    return False, trace
