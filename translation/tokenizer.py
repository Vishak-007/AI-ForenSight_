"""
AI-ForenSight - Module: Tokenizer

Splits text into atomic pieces - words, punctuation, and whitespace kept
as separate items - so downstream stages can classify/transform words
without losing the original spacing and punctuation needed to reconstruct
a natural-looking sentence later.
"""

import re

# A "word" is a run of letters/digits/apostrophes (keeps contractions like
# "don't" and entity placeholders like "__ENT0__" intact as one token).
_TOKEN_RE = re.compile(r"[A-Za-z0-9_']+|[^\sA-Za-z0-9_']+|\s+")


def tokenize(text):
    """Return a list of tokens covering `text` exactly when re-joined."""
    return _TOKEN_RE.findall(text)


def is_word(token):
    return bool(token) and token[0].isalnum() or token.startswith("_")


def is_whitespace(token):
    return bool(token) and token.isspace()


def is_punctuation(token):
    return not is_word(token) and not is_whitespace(token)
