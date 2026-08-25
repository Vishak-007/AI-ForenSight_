"""
Test suite for the Tanglish -> English translation pipeline.

Model-backed tests assert MEANING PRESERVATION (keyword/entity presence),
not exact string equality, since ML model output varies run to run.
Fast tests (no @pytest.mark.model) exercise routing/lexicon logic that
must be deterministic and don't need any model loaded.
"""

import pytest

from translation import lang_id, transliterate
from translation.logging_utils import STAGE_TANGLISH_LEXICON


# ---- Fast tests: no model required ---------------------------------------

@pytest.mark.parametrize("token", ["id", "im", "dont", "cant", "wont"])
def test_contraction_routing(token):
    is_english, _trace = lang_id.is_english_word(token)
    assert is_english is True


@pytest.mark.parametrize("token", ["naliku", "nalaiku", "na", "iruku", "enaku"])
def test_symspell_not_applied_to_tanglish(token):
    is_english, _trace = lang_id.is_english_word(token)
    assert is_english is False


def test_lexicon_precedence_over_fallback():
    tamil, trace = transliterate.transliterate_token("nalaiku")
    assert trace.stage == STAGE_TANGLISH_LEXICON
    tamil2, trace2 = transliterate.transliterate_token("naliku")
    assert trace2.stage == STAGE_TANGLISH_LEXICON
    assert tamil == tamil2  # same spelling-variant resolve to the same Tamil text


def test_low_confidence_tanglish_token_preserved_unchanged():
    # "xkq" has no vowel and isn't in the lexicon - must be preserved, not guessed.
    result, trace = transliterate.transliterate_token("xkq")
    assert result == "xkq"
    assert trace.stage != STAGE_TANGLISH_LEXICON


# ---- Model-backed tests: full pipeline, meaning-preservation assertions --

@pytest.mark.model
def test_pure_english_sentence():
    from translation import translate_transcript
    result = translate_transcript("I will call you tomorrow.")
    assert "tomorrow" in result.lower()
    assert not any("஀" <= ch <= "௿" for ch in result)  # no residual Tamil script


@pytest.mark.model
def test_pure_tanglish_sentence():
    from translation import translate_transcript
    result = translate_transcript("enaku romba pasikuthu")
    assert "hungry" in result.lower()


@pytest.mark.model
def test_english_tanglish_mixed():
    from translation import translate_transcript
    result = translate_transcript("naan nalaiku vara maten enaku work iruku").lower()
    assert "tomorrow" in result
    assert ("won't" in result or "will not" in result or "not" in result)
    assert "work" in result


@pytest.mark.model
@pytest.mark.parametrize("spelling", ["nalaiku", "nalaikku", "naliku", "nalekku"])
def test_tanglish_spelling_variation(spelling):
    from translation import translate_transcript
    result = translate_transcript(f"enaku {spelling} work iruku").lower()
    assert "tomorrow" in result


@pytest.mark.model
def test_english_misspellings():
    from translation import translate_transcript
    result = translate_transcript("I will meet you tomorow").lower()
    assert "tomorrow" in result


@pytest.mark.model
def test_names_and_locations_protected():
    from translation import translate_transcript
    result = translate_transcript("Ravi went to Chennai")
    assert "Ravi" in result
    assert "Chennai" in result


@pytest.mark.model
def test_numbers_preserved():
    from translation import translate_transcript
    result = translate_transcript("call me at 9876543210 tomorrow")
    assert "9876543210" in result


@pytest.mark.model
def test_punctuation_preserved():
    from translation import translate_transcript
    result = translate_transcript("naan nalaiku varen, seri na?")
    assert result.strip().endswith("?")
    assert "," in result


@pytest.mark.model
@pytest.mark.xfail(
    reason=(
        "Known limitation: 'na' repeated as a colloquial discourse filler "
        "produces ungrammatical literal Tamil once transliterated word-for-"
        "word (verified: cleaner Tamil phrasings of the same meaning "
        "translate correctly via the same NLLB call), and the distilled "
        "600M NLLB checkpoint hallucinates an unrelated sentence instead of "
        "erroring. Fixing this needs either a larger NLLB checkpoint or "
        "genuine Tamil discourse-particle handling - not a lexicon guess. "
        "See translation/config.py NLLB_MODEL_NAME."
    ),
    strict=False,
)
def test_slang_code_mixed():
    from translation import translate_transcript
    result = translate_transcript(
        "id like to go meet her today, enna na naliku na busy"
    ).lower()
    assert "tomorrow" in result
    assert "busy" in result


@pytest.mark.model
def test_ambiguous_word_context_dependent():
    from translation import translate_transcript
    result_a = translate_transcript("naan nalaiku vara maten enaku work iruku")
    result_b = translate_transcript("enaku romba pasikuthu, na po poren")
    assert result_a.strip() != ""
    assert result_b.strip() != ""
    assert result_a.lower() != result_b.lower()


@pytest.mark.model
def test_raw_transcript_preserved():
    from translation import translate_transcript_verbose
    raw = "naan nalaiku vara maten enaku work iruku"
    result = translate_transcript_verbose(raw)
    assert result.raw_transcript == raw
    assert result.final_english.strip() != ""
