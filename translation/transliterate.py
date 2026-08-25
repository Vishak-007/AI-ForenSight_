"""
AI-ForenSight - Module: Tanglish -> Tamil Transliteration

Converts a Tanglish (romanized) token into Tamil script, in strict
priority order:

    1. TANGLISH_LEXICON exact match (including known spelling variants)
    2. indic_transliteration / sanscript rule-based fallback
    3. unchanged passthrough if still low-confidence

`sanscript` is a fixed-rule ITRANS->Tamil character mapper. It has no
notion of Tamil grammar, word meaning, or code-mixed context - it is a
transliteration fallback, NOT a Tanglish understanding model. Real
meaning resolution happens later, at clause level, in nllb_translate.py.
"""

import re

from .errors import MissingDependencyError
from .logging_utils import (
    get_logger, StageTrace,
    STAGE_TANGLISH_LEXICON, STAGE_FALLBACK_TRANSLITERATION,
    STAGE_LOW_CONFIDENCE_UNRESOLVED,
)
from . import config

logger = get_logger(__name__)

# A plausible Tanglish romanization has at least one vowel and no long run
# of consonants (English/foreign words and typos often violate this).
_HAS_VOWEL_RE = re.compile(r"[aeiouAEIOU]")
_LONG_CONSONANT_RUN_RE = re.compile(r"[^aeiouAEIOU\s]{5,}")

_sanscript = None
_sanscript_load_attempted = False


def _get_sanscript():
    global _sanscript, _sanscript_load_attempted
    if _sanscript_load_attempted:
        return _sanscript
    _sanscript_load_attempted = True

    try:
        from indic_transliteration import sanscript
    except ImportError as exc:
        raise MissingDependencyError(
            "indic_transliteration", pip_name="indic_transliteration"
        ) from exc

    _sanscript = sanscript
    return _sanscript


def _looks_plausible(romanized_token, tamil_output):
    if not tamil_output:
        return False
    if not _HAS_VOWEL_RE.search(romanized_token):
        return False
    if _LONG_CONSONANT_RUN_RE.search(romanized_token):
        return False
    # sanscript leaves characters it can't map untouched (ASCII survives);
    # if nothing actually became Tamil script, the conversion did nothing.
    if tamil_output == romanized_token:
        return False
    return True


def transliterate_token(token):
    """Return (tamil_or_original: str, trace: StageTrace) for one token."""
    lowered = token.lower()

    lexicon_match = config.TANGLISH_LEXICON.get(lowered)
    if lexicon_match is not None:
        logger.debug("'%s' -> '%s' via TANGLISH_LEXICON", token, lexicon_match)
        trace = StageTrace(STAGE_TANGLISH_LEXICON, token, lexicon_match,
                            {"source": "lexicon"})
        return lexicon_match, trace

    sanscript = _get_sanscript()
    fallback_output = sanscript.transliterate(
        lowered, sanscript.ITRANS, sanscript.TAMIL
    )

    if _looks_plausible(lowered, fallback_output):
        logger.debug("'%s' -> '%s' via sanscript fallback", token, fallback_output)
        trace = StageTrace(STAGE_FALLBACK_TRANSLITERATION, token, fallback_output,
                            {"source": "sanscript_itrans"})
        return fallback_output, trace

    logger.warning("'%s' -> left unchanged (low-confidence, unresolved)", token)
    trace = StageTrace(STAGE_LOW_CONFIDENCE_UNRESOLVED, token, token,
                        {"reason": "no_lexicon_match_and_implausible_fallback"})
    return token, trace


def transliterate_span(token_flags):
    """Transliterate a Tanglish clause as a unit.

    `token_flags` is a list of (token, is_english_loanword) pairs. Tokens
    already classified as English loanwords embedded in this Tanglish
    clause (is_english_loanword=True) are kept verbatim in Latin script -
    they are NOT run through the lexicon/sanscript fallback, since they
    were never Tanglish to begin with (lang_id.py already traced them).

    Returns (tamil_text: str, traces: list[StageTrace]). Tokens are still
    converted one at a time internally (that's what "transliteration" is -
    script conversion), but this is explicitly NOT translation: no meaning
    is resolved here, and the caller (pipeline.py) always sends the joined
    output to NLLB as one clause, never per-token.
    """
    pieces = []
    traces = []
    for token, is_english_loanword in token_flags:
        if is_english_loanword:
            pieces.append(token)
            continue
        converted, trace = transliterate_token(token)
        pieces.append(converted)
        traces.append(trace)
    return " ".join(pieces), traces
