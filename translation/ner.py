"""
AI-ForenSight - Module: NER / Protected Entities

Masks names, places, organizations, numbers, URLs, and emails with atomic
placeholder tokens BEFORE tokenization/translation, so nothing downstream
(SymSpell, transliteration, NLLB, grammar correction) can alter forensic
facts. Placeholders are restored verbatim as the final pipeline step.

Regex-based entities (numbers, URLs, emails, phone numbers) are always
detected. spaCy NER (PERSON/GPE/LOC/ORG) is used when available; if spaCy
or its model isn't installed, NER degrades to regex-only rather than
failing the whole pipeline - loss of name-detection is a quality tradeoff,
not a broken dependency, since regex-based protection still covers the
highest-stakes entities (numbers, contacts).
"""

import re

from .logging_utils import get_logger
from . import config

logger = get_logger(__name__)

PLACEHOLDER_TEMPLATE = "__ENT{index}__"
_PLACEHOLDER_RE = re.compile(r"__ENT\d+__")

_SPACY_ENTITY_LABELS = {"PERSON", "GPE", "LOC", "ORG"}

# Order matters: more specific patterns first so e.g. an email isn't first
# partially eaten by the URL pattern.
_REGEX_ENTITY_PATTERNS = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("URL", re.compile(r"https?://\S+|www\.\S+")),
    ("PHONE", re.compile(r"\+?\d[\d\-\s]{7,}\d")),
    ("NUMBER", re.compile(r"\b\d+(?:\.\d+)?\b")),
]

# Closed-class capitalized words that are NOT proper nouns (pronouns,
# determiners, WH-words, common interjections/greetings, days/months).
# Used by the capitalization safety-net below: since this list is small
# and enumerable while proper nouns are not, treating "capitalized and
# not in this list" as "probable proper noun" is a safe, conservative
# heuristic - it only risks OVER-protecting (leaving an ordinary word
# untranslated), never corrupting a real name, which matches the hard
# forensic requirement to never mangle entities.
_CAPITALIZED_NON_ENTITY_WORDS = {
    "i", "i'm", "i've", "i'll", "i'd",
    "a", "an", "the", "this", "that", "these", "those",
    "he", "she", "it", "they", "we", "you", "who", "what", "when", "where",
    "why", "how", "which", "whose",
    "ok", "okay", "yes", "no", "hi", "hello", "hey", "please", "thanks",
    "thank", "sorry", "yeah", "sure", "well", "so", "but", "and", "or", "if",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "today", "tomorrow", "yesterday",
}

_CAPITALIZED_WORD_RE = re.compile(r"\b[A-Z][a-zA-Z']*\b")

_nlp = None
_spacy_load_attempted = False


def _get_spacy_model():
    """Lazy-load spaCy's English NER model. Returns None (not an
    exception) if unavailable, since NER is a best-effort enhancement on
    top of the always-on regex protection, not a hard pipeline dependency."""
    global _nlp, _spacy_load_attempted
    if _spacy_load_attempted:
        return _nlp
    _spacy_load_attempted = True

    from . import config

    try:
        import spacy
    except ImportError:
        logger.warning(
            "spaCy not installed - NER will only protect numbers/URLs/"
            "emails/phone numbers, not names/places/orgs. "
            "Run: pip install spacy && python -m spacy download %s",
            config.SPACY_MODEL_NAME,
        )
        return None

    try:
        _nlp = spacy.load(config.SPACY_MODEL_NAME)
    except OSError:
        logger.warning(
            "spaCy model '%s' not downloaded - NER will only protect "
            "numbers/URLs/emails/phone numbers, not names/places/orgs. "
            "Run: python -m spacy download %s",
            config.SPACY_MODEL_NAME, config.SPACY_MODEL_NAME,
        )
        return None

    return _nlp


def _looks_like_proper_noun(entity_text):
    """Require every word in the span to start with an uppercase letter.

    en_core_web_sm (a small model) misfires PERSON/GPE tags on lowercase
    colloquial/Tanglish phrases (e.g. "naan nalaiku" -> PERSON). Genuine
    names/places in this project's transcripts are written capitalized,
    so this filter is a cheap, effective guard against exactly that
    failure mode without needing a bigger (slower) spaCy model.
    """
    words = entity_text.split()
    return bool(words) and all(w[0].isupper() for w in words if w[0].isalpha())


def protect_entities(text):
    """Replace detected entities with placeholder tokens.

    Returns (masked_text, entity_map) where entity_map maps each
    placeholder token to the original verbatim text it replaced.
    """
    entity_map = {}
    spans = []  # (start, end, original_text)

    nlp = _get_spacy_model()
    if nlp is not None:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in _SPACY_ENTITY_LABELS and _looks_like_proper_noun(ent.text):
                spans.append((ent.start_char, ent.end_char, ent.text))
            elif ent.label_ in _SPACY_ENTITY_LABELS:
                logger.debug(
                    "Ignoring spaCy %s entity %r - not capitalized, likely a "
                    "false positive on lowercase/Tanglish text.",
                    ent.label_, ent.text,
                )

    # Capitalization safety net: catches proper nouns spaCy's small model
    # missed entirely (e.g. a name spaCy fails to tag at all - see
    # _looks_like_proper_noun's docstring for the companion false-positive
    # guard). Deliberately independent of spaCy's PERSON/GPE/ORG recall.
    #
    # One additional guard (added after real-corpus testing surfaced a
    # false-positive failure mode): a word already known to be Tanglish
    # (lexicon/function-word set) is never treated as an entity just
    # because it happens to be capitalized (e.g. "Iruku" ending a
    # capitalized sentence) - we already know exactly what this word is,
    # so guessing "maybe it's a name" is strictly worse than using what we
    # know. A sentence-initial-only/no-repeat exemption was deliberately
    # NOT added on top of this: it would also exempt a genuine single-
    # mention name at the start of a sentence (e.g. "Ravi went to
    # Chennai") - confirmed empirically to reintroduce the "Ravi" ->
    # "Rave" SymSpell corruption this safety net exists to prevent. Between
    # under-translating an unknown capitalized Tanglish word and risking
    # corrupting a real name, this project's hard requirement is to never
    # risk the latter.
    for match in _CAPITALIZED_WORD_RE.finditer(text):
        word = match.group()
        start, end = match.span()
        if word.lower() in _CAPITALIZED_NON_ENTITY_WORDS:
            continue
        if (word.lower() in config.KNOWN_TANGLISH_FUNCTION_WORDS
                or word.lower() in config.TANGLISH_LEXICON):
            continue
        if any(start < e and end > s for s, e, _ in spans):
            continue
        spans.append((start, end, word))

    for _label, pattern in _REGEX_ENTITY_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            # Skip if it overlaps a span already claimed (spaCy entities
            # take precedence since they were matched first).
            if any(start < e and end > s for s, e, _ in spans):
                continue
            spans.append((start, end, match.group()))

    if not spans:
        return text, entity_map

    spans.sort(key=lambda s: s[0])

    masked_parts = []
    cursor = 0
    for index, (start, end, original) in enumerate(spans):
        if start < cursor:
            continue  # overlapping span, already covered
        placeholder = PLACEHOLDER_TEMPLATE.format(index=index)
        masked_parts.append(text[cursor:start])
        masked_parts.append(placeholder)
        entity_map[placeholder] = original
        cursor = end
    masked_parts.append(text[cursor:])

    masked_text = "".join(masked_parts)
    logger.debug("protect_entities: masked %d entit(y/ies): %s",
                 len(entity_map), entity_map)
    return masked_text, entity_map


def restore_entities(text, entity_map):
    """Swap placeholder tokens back to their original verbatim text."""
    def _replace(match):
        placeholder = match.group()
        return entity_map.get(placeholder, placeholder)

    return _PLACEHOLDER_RE.sub(_replace, text)


def is_placeholder(token):
    return bool(_PLACEHOLDER_RE.fullmatch(token))
