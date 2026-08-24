"""
AI-ForenSight - Module: Translation Pipeline Orchestration

Wires every stage together per the target flow:

    Transcript text
      -> NER / protected entity detection
      -> Tokenization
      -> English-word detection
           English -> keep (+ SymSpell)
           Tanglish -> Tamil script -> NLLB Tamil->English
      -> Sentence reconstruction
      -> Whole-sentence contextual correction
      -> Restore protected entities
      -> Final English sentence

Hard rule enforced here: translation NEVER happens per isolated word. A
clause (split at punctuation/entity placeholders) is first grouped into
alternating English-runs and Tanglish-runs; a SHORT English run embedded
inside an otherwise-Tanglish clause is kept as an inline Latin-script
loanword rather than splitting the clause, so the ENTIRE clause is always
handed to NLLB in a single call.
"""

from dataclasses import dataclass, field
from typing import List

from . import config, ner, lang_id, spellcheck, transliterate, nllb_translate
from . import grammar_correct, reconstruct
from .logging_utils import get_logger, StageTrace, STAGE_TANGLISH_DETECTION
from .tokenizer import tokenize, is_word, is_whitespace, is_punctuation

logger = get_logger(__name__)


@dataclass
class TranslationResult:
    raw_transcript: str
    final_english: str
    trace: List[StageTrace] = field(default_factory=list)


def _split_into_clauses(tokens):
    """Split tokens into clauses at punctuation and entity placeholders.

    Adjacent separators with NO whitespace between them in the source
    (e.g. the ':' in a masked "21:00", or "...") are kept together in one
    clause so they reconstruct verbatim with their original tight spacing,
    instead of each becoming its own clause and picking up a stray space
    from reconstruct.py's inter-clause join.
    """
    clauses = []
    current = []
    current_is_sep = None  # None = empty, True = separator run, False = word run
    for token in tokens:
        if is_whitespace(token):
            if current_is_sep is True:
                clauses.append(current)
                current = []
                current_is_sep = None
            else:
                current.append(token)
            continue

        token_is_sep = is_punctuation(token) or ner.is_placeholder(token)
        if current_is_sep is None:
            current = [token]
            current_is_sep = token_is_sep
        elif token_is_sep == current_is_sep:
            current.append(token)
        else:
            clauses.append(current)
            current = [token]
            current_is_sep = token_is_sep
    if current:
        clauses.append(current)
    return clauses


def _is_separator_clause(clause):
    return bool(clause) and all(
        is_punctuation(t) or ner.is_placeholder(t) for t in clause
    )


def _segment_clause(word_tokens, classifications):
    """Segment a clause's word tokens into ("english", tokens) and
    ("tanglish", [(token, is_english_loanword), ...]) parts.

    A run of consecutive English tokens LONGER than
    ENGLISH_RUN_EMBED_THRESHOLD is a genuine standalone English segment.
    Everything else - Tanglish runs, plus any English run at or below the
    threshold sitting among them - is merged into ONE contiguous Tanglish
    segment per stretch, so a clause like "naan nalaiku vara maten enaku
    work iruku" (only "work" is a short embedded English run) becomes a
    SINGLE Tanglish segment sent to NLLB in one call, never split around
    the embedded loanword.
    """
    raw_runs = []
    for token, (is_english, _trace) in zip(word_tokens, classifications):
        if raw_runs and raw_runs[-1][0] == is_english:
            raw_runs[-1][1].append(token)
        else:
            raw_runs.append([is_english, [token]])

    if not any(not is_english for is_english, _ in raw_runs):
        return [("english", word_tokens)]

    segments = []
    pending = []

    def flush_pending():
        if pending:
            segments.append(("tanglish", list(pending)))
            pending.clear()

    for is_english, tokens in raw_runs:
        if is_english and len(tokens) > config.ENGLISH_RUN_EMBED_THRESHOLD:
            flush_pending()
            segments.append(("english", tokens))
        else:
            pending.extend((t, is_english) for t in tokens)
    flush_pending()

    return segments


def _process_clause(clause_tokens, trace):
    if _is_separator_clause(clause_tokens):
        return "".join(clause_tokens)

    word_tokens = [t for t in clause_tokens if is_word(t)]
    if not word_tokens:
        return "".join(clause_tokens)

    classifications = [lang_id.is_english_word(t) for t in word_tokens]
    for _is_eng, ctrace in classifications:
        trace.append(ctrace)

    segments = _segment_clause(word_tokens, classifications)

    output_parts = []
    for kind, items in segments:
        if kind == "english":
            corrected = []
            for token in items:
                fixed, ctrace = spellcheck.correct_english_token(token)
                trace.append(ctrace)
                corrected.append(fixed)
            output_parts.append(" ".join(corrected))
        else:
            tanglish_tokens = [t for t, is_eng in items if not is_eng]
            trace.append(StageTrace(
                STAGE_TANGLISH_DETECTION,
                " ".join(t for t, _ in items), "routed_to_transliteration",
                {"tanglish_token_count": len(tanglish_tokens),
                 "embedded_english_loanwords": [t for t, is_eng in items if is_eng]},
            ))
            tamil_text, translit_traces = transliterate.transliterate_span(items)
            trace.extend(translit_traces)
            english_text, nllb_trace = nllb_translate.translate_ta_to_en(tamil_text)
            trace.append(nllb_trace)
            output_parts.append(english_text)

    return " ".join(part for part in output_parts if part)


def translate_transcript_verbose(text):
    """Run the full pipeline and return a TranslationResult with a
    per-stage trace suitable for forensic audit."""
    trace = []

    masked_text, entity_map = ner.protect_entities(text)
    tokens = tokenize(masked_text)
    clauses = _split_into_clauses(tokens)

    processed_clauses = [_process_clause(clause, trace) for clause in clauses]

    reconstructed = reconstruct.reconstruct(processed_clauses)
    corrected, grammar_trace = grammar_correct.correct_sentence(reconstructed)
    trace.append(grammar_trace)

    final_english = ner.restore_entities(corrected, entity_map)

    return TranslationResult(raw_transcript=text, final_english=final_english, trace=trace)


def translate_transcript(text):
    """translate_transcript(text: str) -> str

    Convenience wrapper around translate_transcript_verbose() for callers
    that only need the final English sentence.
    """
    return translate_transcript_verbose(text).final_english
