"""
AI-ForenSight - Module: Sentence Reconstruction

Joins ordered chunks (kept-English text, NLLB-translated clause text,
punctuation, entity placeholders) back into one string, normalizing
whitespace around punctuation so joins between differently-processed
chunks don't produce doubled spaces or a space before a comma/period.
"""

import re

_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.!?;:])")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")


def reconstruct(chunks):
    """chunks: list[str] in output order. Returns one cleaned-up string."""
    joined = " ".join(chunk for chunk in chunks if chunk != "")
    joined = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", joined)
    joined = _MULTI_SPACE_RE.sub(" ", joined)
    return joined.strip()
