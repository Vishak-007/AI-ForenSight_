"""
AI-ForenSight - Package: translation

Tanglish/code-mixed Tamil -> English translation pipeline. Public entry
point: translate_transcript(text: str) -> str.
"""

from .pipeline import translate_transcript, translate_transcript_verbose, TranslationResult

__all__ = ["translate_transcript", "translate_transcript_verbose", "TranslationResult"]
