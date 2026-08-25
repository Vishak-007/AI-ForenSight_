"""
AI-ForenSight - Module: Translation Config

All tunable values for the Tanglish -> English pipeline live here as named
constants: model names, thresholds, and the Tanglish lexicon. Nothing else
in the `translation` package should hardcode a model name or a magic number.
"""

# ---- Models -----------------------------------------------------------

SPACY_MODEL_NAME = "en_core_web_sm"

NLLB_MODEL_NAME = "facebook/nllb-200-distilled-600M"
NLLB_SRC_LANG = "tam_Taml"
NLLB_TGT_LANG = "eng_Latn"

GRAMMAR_MODEL_NAME = "vennify/t5-base-grammar-correction"
GRAMMAR_MODEL_PROMPT_PREFIX = "grammar: "

# ---- Thresholds ---------------------------------------------------------

# wordfreq zipf_frequency scale: ~7 = "the", ~3 = common word, <1 = very rare/absent.
ENGLISH_ZIPF_THRESHOLD = 2.5

# A run of consecutive English-classified tokens longer than this is treated
# as its own English clause; a run at or below this length, embedded inside
# an otherwise-Tanglish clause, is kept as an inline loanword instead
# (see translation/pipeline.py).
ENGLISH_RUN_EMBED_THRESHOLD = 2

SYMSPELL_MAX_EDIT_DISTANCE = 2
SYMSPELL_PREFIX_LENGTH = 7

# Minimum wordfreq zipf frequency the SUGGESTED correction itself must have
# before lang_id.py trusts "this looks like a misspelling of a common
# English word" as a signal to override an otherwise-Tanglish classification.
# Without this, a Tanglish word that happens to be edit-distance-1 from an
# uncommon/proper-noun English word (e.g. "avun" -> "avon") gets wrongly
# treated as an English typo. Common typo targets ("tomorrow", "friend")
# score 5+; borderline proper nouns like "avon" score ~3.45, so this
# threshold cleanly separates the two cases (calibrated empirically).
SYMSPELL_TYPO_TARGET_MIN_ZIPF = 4.5

# Minimum fraction of the reconstructed sentence's content words (nouns/
# verbs/etc. - i.e. not stopwords) that must still appear in the
# grammar-correction model's output. Guards against a model that
# paraphrases/drops meaning instead of making minimal grammar fixes -
# below this, its output is discarded and the pre-correction text is
# used instead (see translation/grammar_correct.py).
GRAMMAR_MIN_CONTENT_WORD_OVERLAP = 0.8

GRAMMAR_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "am", "be", "been", "being",
    "to", "of", "in", "on", "at", "for", "with", "and", "or", "but", "so",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "its", "our", "their",
    "do", "does", "did", "doing", "done",
    "have", "has", "had", "having",
    "will", "would", "can", "could", "should", "shall", "may", "might", "must",
    "that", "this", "these", "those", "not", "no", "n't",
}

# ---- Contractions / abbreviations that wordfreq alone won't recognize ---
# (no apostrophe, so they don't look like their "real" English word to a
# frequency lookup) - force these to English rather than misrouting them
# into the Tanglish path.
CONTRACTION_WHITELIST = {
    "id", "im", "dont", "cant", "wont", "didnt", "isnt", "arent",
    "youre", "theyre", "ive", "ill", "lets", "whats", "thats", "hes",
    "shes", "wasnt", "werent", "havent", "hasnt", "couldnt", "wouldnt",
    "shouldnt",
}

# ---- Tanglish function words that MUST be routed as Tanglish even though ----
# they are short/common enough that a naive check might otherwise miss them.
# Meaning is context-dependent (resolved later by NLLB over the whole
# clause, never here) - this set only decides ROUTING, not translation.
KNOWN_TANGLISH_FUNCTION_WORDS = {
    "enna", "enaku", "enakku", "na", "iruku", "irukku", "po", "poren",
    "pannitu", "venum", "illa", "naan", "nee", "avan", "avun", "aval", "avaru",
    "avar", "romba", "vara", "maten", "ana", "aana",
}

# ---- Tanglish -> Tamil lexicon -------------------------------------------
# Highest-priority resolution step in translation/transliterate.py. Keys are
# lowercase romanized spellings (including common variants); values are the
# Tamil-script rendering. This is a normalization aid, NOT a translation -
# meaning is still resolved later by NLLB over the full clause.
TANGLISH_LEXICON = {
    "naan": "நான்",
    "nee": "நீ",
    "avan": "அவன்",
    "avun": "அவன்",
    "aval": "அவள்",
    "avaru": "அவரு",
    "avar": "அவர்",

    # Adjectival/relative-participle marker, e.g. "serious ana person" =
    # "person who is serious". Distinct from standalone "na" (discourse
    # filler, mapped separately below) even though both romanize similarly.
    # NOTE: "aana" is intentionally NOT duplicated here - it's already a
    # variant key for "na" below (mapping to "ஆனா"); a duplicate dict key
    # would silently keep only the later definition, discarding one sense.
    "ana": "ஆன",

    "nalaiku": "நாளைக்கு",
    "nalaikku": "நாளைக்கு",
    "naliku": "நாளைக்கு",
    "nalekku": "நாளைக்கு",
    "nalaikke": "நாளைக்கு",

    "vara": "வர",
    "maten": "மாட்டேன்",
    "matten": "மாட்டேன்",

    "enaku": "எனக்கு",
    "enakku": "எனக்கு",
    "enakkuh": "எனக்கு",

    "iruku": "இருக்கு",
    "irukku": "இருக்கு",
    "irukuthu": "இருக்குது",

    "romba": "ரொம்ப",
    "rompa": "ரொம்ப",

    "pasikuthu": "பசிக்குது",
    "pasikkudhu": "பசிக்குது",
    "pasikkuthu": "பசிக்குது",

    "enna": "என்ன",
    "yenna": "என்ன",

    "na": "ஆனா",
    "aana": "ஆனா",

    "po": "போ",
    "poren": "போறேன்",
    "poriyen": "போறேன்",

    "pannitu": "பண்ணிட்டு",
    "pannittu": "பண்ணிட்டு",

    "venum": "வேணும்",
    "venam": "வேணும்",

    "illa": "இல்ல",
    "illai": "இல்ல",

    # ---- Corpus-derived additions -----------------------------------
    # Sourced from a frequency analysis of vishnu-n/Tanglish-Corpus-185k
    # (CC-BY-4.0, real informal Tanglish text from r/TamilNaduDiscussion):
    # these are the most common words the pipeline was leaving unresolved
    # on real data. Only unambiguous, high-confidence common vocabulary was
    # added; political acronyms, usernames, and unclear short strings from
    # the same frequency list were deliberately excluded.
    "intha": "இந்த", "andha": "அந்த", "antha": "அந்த",
    "athu": "அது", "adhu": "அது",
    "atha": "அத", "adha": "அத",
    "ithu": "இது", "idhu": "இது", "itha": "இத",
    "neenga": "நீங்க", "unga": "உங்க", "namma": "நம்ம", "avanga": "அவங்க",
    "enga": "எங்க", "entha": "எந்த",
    "nalla": "நல்ல", "periya": "பெரிய", "ellam": "எல்லாம்",
    "onnu": "ஒன்னு", "ulla": "உள்ள", "athula": "அதுல", "athuku": "அதுக்கு",
    "kuda": "கூட", "kooda": "கூட", "innum": "இன்னும்", "dhaan": "தான்",
    "maari": "மாதிரி", "mathiri": "மாதிரி", "pola": "போல",
    "epdi": "எப்டி", "ippo": "இப்போ", "mattum": "மட்டும்", "kitta": "கிட்ட",
    "iruka": "இருக்கு", "irukum": "இருக்கும்", "varum": "வரும்",
    "varuthu": "வருது", "unaku": "உனக்கு",
    "panna": "பண்ண", "pana": "பண்ண", "pannu": "பண்ணு", "panni": "பண்ணி",
    "pannunga": "பண்ணுங்க", "panra": "பண்ற",
    "podu": "போடு", "poda": "போட", "potu": "போட்டு", "pottu": "போட்டு",
    "podunga": "போடுங்க",
    "sollu": "சொல்லு", "solli": "சொல்லி", "sollunga": "சொல்லுங்க",
    "solla": "சொல்ல",
    "thala": "தல",
    "ipdi": "இப்டி", "apdi": "அப்டி",
    "vanthu": "வந்து", "evlo": "எவ்ளோ", "illama": "இல்லாம",
    "iruntha": "இருந்தா", "pandra": "பண்ற",
}
