"""
AI-ForenSight - Module: English Spelling Correction (SymSpell)

Corrects likely spelling errors on tokens that lang_id.py has ALREADY
classified as English (e.g. "tomorow" -> "tomorrow", "frnd" -> "friend").
This module is never called on Tanglish tokens - lang_id.py's routing is
what keeps a word like "naliku" from ever reaching SymSpell and being
forced into an unrelated English word.
"""

import pkgutil

from .errors import MissingDependencyError
from .logging_utils import get_logger, StageTrace, STAGE_SYMSPELL_CORRECTION
from . import config

logger = get_logger(__name__)

_symspell = None
_load_attempted = False


def _get_symspell():
    global _symspell, _load_attempted
    if _load_attempted:
        if _symspell is None:
            raise MissingDependencyError(
                "symspellpy",
                extra="Previous load attempt failed - see earlier log output.",
            )
        return _symspell
    _load_attempted = True

    try:
        from symspellpy import SymSpell
        import symspellpy
    except ImportError as exc:
        raise MissingDependencyError("symspellpy") from exc

    sym_spell = SymSpell(
        max_dictionary_edit_distance=config.SYMSPELL_MAX_EDIT_DISTANCE,
        prefix_length=config.SYMSPELL_PREFIX_LENGTH,
    )

    dictionary_bytes = pkgutil.get_data(
        "symspellpy", "frequency_dictionary_en_82_765.txt"
    )
    if dictionary_bytes is None:
        raise MissingDependencyError(
            "symspellpy",
            extra="Bundled frequency dictionary not found in the installed package.",
        )

    import io
    sym_spell.load_dictionary(
        io.StringIO(dictionary_bytes.decode("utf-8")),
        term_index=0, count_index=1, separator=" ",
    )

    _symspell = sym_spell
    return _symspell


def has_close_english_match(token, max_edit_distance=1):
    """Return True if `token` is within `max_edit_distance` of a common
    English dictionary word - used by lang_id.py as a secondary signal to
    catch English typos (e.g. "tomorow") that wordfreq's raw frequency
    lookup would otherwise miss and misroute as Tanglish, since a
    misspelling has near-zero corpus frequency of its own.

    Two guards keep this from misfiring on genuine Tanglish (confirmed
    empirically: "avun" - a common spelling of Tanglish "avan"/"he" - is
    edit-distance 1 from the English word "avon" and was wrongly flagged
    as an English typo before these guards were added):
      1. distance 1 by default - close enough that an accidental match
         against genuine Tanglish should be rare.
      2. the suggested correction itself must be a genuinely COMMON
         English word (SYMSPELL_TYPO_TARGET_MIN_ZIPF), not just any
         dictionary entry - typos are misspellings of common words
         ("tomorrow", "friend"), whereas a coincidental one-edit match to
         an uncommon/proper-noun-ish word like "avon" (zipf ~3.45, well
         below the 4.5 threshold) is far more likely a genuine Tanglish
         word that happens to look similar.
    """
    if not token.isalpha():
        return False
    sym_spell = _get_symspell()
    from symspellpy import Verbosity
    from wordfreq import zipf_frequency
    suggestions = sym_spell.lookup(
        token.lower(), Verbosity.CLOSEST, max_edit_distance=max_edit_distance
    )
    if not suggestions or suggestions[0].term == token.lower():
        return False
    return zipf_frequency(suggestions[0].term, "en") >= config.SYMSPELL_TYPO_TARGET_MIN_ZIPF


def correct_english_token(token):
    """Return the corrected spelling of an English token, or the token
    unchanged if SymSpell has no better suggestion (already-correct or
    rare-but-valid words are left alone)."""
    if not token.isalpha():
        return token, StageTrace(STAGE_SYMSPELL_CORRECTION, token, token,
                                  {"reason": "not_alphabetic"})

    sym_spell = _get_symspell()

    from symspellpy import Verbosity
    suggestions = sym_spell.lookup(
        token.lower(), Verbosity.CLOSEST,
        max_edit_distance=config.SYMSPELL_MAX_EDIT_DISTANCE,
    )

    if not suggestions:
        return token, StageTrace(STAGE_SYMSPELL_CORRECTION, token, token,
                                  {"reason": "no_suggestion"})

    best = suggestions[0]
    if best.term == token.lower():
        return token, StageTrace(STAGE_SYMSPELL_CORRECTION, token, token,
                                  {"reason": "already_correct"})

    corrected = best.term
    # Preserve original capitalization style (e.g. "Tomorow" -> "Tomorrow").
    if token[0].isupper():
        corrected = corrected.capitalize()

    logger.debug("SymSpell corrected '%s' -> '%s' (distance=%d)",
                 token, corrected, best.distance)
    trace = StageTrace(STAGE_SYMSPELL_CORRECTION, token, corrected,
                        {"edit_distance": best.distance})
    return corrected, trace
