"""
Turns one raw speech-to-text answer into the `normalized_text` the schema in
TRANSCRIPT_DATA_ARCHITECTURE.md (section 4) already specified -- this module
just makes those rules real code instead of a table in a markdown file.

Each rule is keyed to `expected_answer_type`, exactly like the architecture
doc says, because a number and a yes/no answer need different cleanup; one
generic rule can't honestly serve both. `raw_text` is never modified by any
function here -- every rule only ever produces a new `normalized_text` value,
so the original spoken answer stays recoverable for audit.
"""

import re

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------- shared building blocks ----------

FILLER_WORDS = {"um", "uh", "umm", "uhh", "like", "you know", "so", "actually", "basically"}

# Matches a filler word only as a standalone word (not a substring of a real
# word, e.g. "like" must not strip the "like" inside "likely").
_FILLER_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(FILLER_WORDS, key=len, reverse=True)) + r")\b[,]?\s*",
    re.IGNORECASE,
)

_WHITESPACE_PATTERN = re.compile(r"\s+")


def strip_filler_words(text):
    """Remove standalone filler words and collapse repeated whitespace.
    Used as the first step by every answer type, not only free_text."""
    if not text:
        return ""
    cleaned = _FILLER_PATTERN.sub(" ", text)
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()
    return cleaned


# Spoken number words, 0-99 -- the realistic range for "years of experience"
# questions, same ceiling the architecture doc names.
_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}


def spoken_number_to_digit(text):
    """Converts a spoken number phrase ("five", "twenty one", "twenty-five")
    to an int 0-99. Returns None if the phrase isn't a recognizable number in
    that range -- callers must not coerce that None to 0, see
    normalize_number_answer."""
    if text is None:
        return None
    cleaned = text.strip().lower().replace("-", " ")
    if cleaned.isdigit():
        value = int(cleaned)
        return value if 0 <= value <= 99 else None

    words = cleaned.split()
    if len(words) == 1 and words[0] in _ONES:
        return _ONES[words[0]]
    if len(words) == 1 and words[0] in _TENS:
        return _TENS[words[0]]
    if len(words) == 2 and words[0] in _TENS and words[1] in _ONES and _ONES[words[1]] < 10:
        return _TENS[words[0]] + _ONES[words[1]]
    return None


# ---------- per-type normalization rules ----------

def normalize_free_text(raw_text):
    """free_text: strip filler words, collapse whitespace, otherwise keep
    exactly as spoken -- this type is read by a person or a future NLP step,
    not parsed into a strict value."""
    return strip_filler_words(raw_text)


_TRAILING_UNIT_PATTERN = re.compile(r"\b(years?|yrs?|months?)\b\.?\s*$", re.IGNORECASE)


def normalize_number_answer(raw_text):
    """number: strip filler words, then convert a spoken number word to a
    digit. A value outside the recognizable 0-99 range is left as text and
    flagged, never silently coerced to 0 -- same honest-null discipline as
    scoring_engine's redistribution logic."""
    cleaned = strip_filler_words(raw_text)
    # "twenty five years" answers "how many years" with the unit spoken back
    # -- the unit itself isn't part of the number, so it's dropped before
    # matching, not treated as an unparseable phrase.
    without_unit = _TRAILING_UNIT_PATTERN.sub("", cleaned).strip()
    digit = spoken_number_to_digit(without_unit)
    if digit is not None:
        return {"value": digit, "unparsed": False}
    return {"value": cleaned, "unparsed": True}


_YES_VARIANTS = {"yes", "yeah", "yep", "yup", "sure", "of course", "definitely"}
_NO_VARIANTS = {"no", "nope", "not really", "nah"}


def normalize_yes_no_answer(raw_text):
    """yes_no: map a closed set of real spoken variants to a boolean.
    Anything outside that closed set is left as None with the raw text kept
    separately -- a hedging answer ("maybe, depends") must not be forced into
    yes or no. A candidate rarely answers with the bare word alone ("uh yeah
    sure, definitely") so this checks for a leading matching phrase rather
    than requiring the whole cleaned answer to equal one exactly."""
    cleaned = strip_filler_words(raw_text).lower().strip(" .!")
    if not cleaned:
        return None

    # Multi-word variants first ("not really" must win over a bare "not").
    for variant in sorted(_NO_VARIANTS, key=len, reverse=True):
        if cleaned.startswith(variant):
            return False
    for variant in sorted(_YES_VARIANTS, key=len, reverse=True):
        if cleaned.startswith(variant):
            return True
    return None


_CURRENCY_WORDS_PATTERN = re.compile(r"\b(rupees?|rs\.?|inr|per\s+annum|per\s+month|p\.?a\.?)\b", re.IGNORECASE)
_LAKH_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*lakhs?", re.IGNORECASE)
_CRORE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*crores?", re.IGNORECASE)
_PLAIN_NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")


def normalize_currency_answer(raw_text, default_currency="INR"):
    """currency: strip filler words and currency words/symbols into one
    numeric value plus a currency code (defaults to INR, since every sample
    JD in this repo is an India-based role). Vague answers ("market rate",
    "negotiable") are kept as text, not forced into a number."""
    cleaned = strip_filler_words(raw_text)
    cleaned = _CURRENCY_WORDS_PATTERN.sub("", cleaned).strip()

    lakh_match = _LAKH_PATTERN.search(cleaned)
    if lakh_match:
        amount = int(float(lakh_match.group(1)) * 100_000)
        return {"amount": amount, "currency": default_currency, "unparsed": False}

    crore_match = _CRORE_PATTERN.search(cleaned)
    if crore_match:
        amount = int(float(crore_match.group(1)) * 10_000_000)
        return {"amount": amount, "currency": default_currency, "unparsed": False}

    plain_match = _PLAIN_NUMBER_PATTERN.search(cleaned)
    if plain_match:
        amount = int(float(plain_match.group(0).replace(",", "")))
        return {"amount": amount, "currency": default_currency, "unparsed": False}

    return {"value": cleaned, "unparsed": True}


_DAY_PATTERN = re.compile(r"(\d+)\s*day")
_WEEK_PATTERN = re.compile(r"(\d+)\s*week")
_MONTH_PATTERN = re.compile(r"(\d+)\s*month")
_IMMEDIATE_PHRASES = {"immediately", "right away", "i can join right away", "today", "tomorrow"}

_WORD_NUMBER_BEFORE_UNIT = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
}


def _word_number_before(unit_word, text):
    match = re.search(r"(\w+)\s*" + unit_word, text)
    if not match:
        return None
    token = match.group(1)
    if token.isdigit():
        return int(token)
    return _WORD_NUMBER_BEFORE_UNIT.get(token)


def normalize_duration_answer(raw_text):
    """duration: normalize to a number of days wherever the phrasing gives
    one ("one month" -> 30, "two weeks" -> 14, "immediately" -> 0). An
    unparseable duration stays as text rather than being guessed at."""
    cleaned = strip_filler_words(raw_text).lower()

    if cleaned.strip(" .!") in _IMMEDIATE_PHRASES:
        return {"days": 0, "unparsed": False}

    day_match = _DAY_PATTERN.search(cleaned)
    if day_match:
        return {"days": int(day_match.group(1)), "unparsed": False}

    week_match = _WEEK_PATTERN.search(cleaned)
    weeks = int(week_match.group(1)) if week_match else _word_number_before("week", cleaned)
    if weeks is not None:
        return {"days": weeks * 7, "unparsed": False}

    month_match = _MONTH_PATTERN.search(cleaned)
    months = int(month_match.group(1)) if month_match else _word_number_before("month", cleaned)
    if months is not None:
        return {"days": months * 30, "unparsed": False}

    return {"value": cleaned, "unparsed": True}


_LIST_SPLIT_PATTERN = re.compile(r",|\band\b", re.IGNORECASE)

# Words that, said just before a skill name, mean the candidate is denying
# that skill rather than claiming it ("not so much Mongo"). Kept small and
# literal on purpose -- this is a cue check, not sentiment analysis.
_NEGATION_CUE_PATTERN = re.compile(
    r"\b(not|no|never|without|n't|haven't|hasn't|don't|doesn't|didn't)\b", re.IGNORECASE
)


def _skill_key(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_list_answer(raw_text, canonical_skills=None):
    """list: match the role's own mandatory-skill list (passed in as
    `canonical_skills`, the same names already filled into the question text
    by question_builder.py) against the candidate's answer, however it's
    phrased -- a direct list ("React, Node.js") or a sentence ("I've worked
    with React and Node.js, not so much Mongo"). A skill is only counted when
    it's actually mentioned, and dropped (not silently kept as a positive
    match) when a negation word appears in the few words right before it, so
    "not so much Mongo" does not get recorded as the candidate claiming
    MongoDB. Matching ignores case, spacing and punctuation, so "node js"
    still lands on the canonical "Node.js".

    If no canonical list is given there's nothing to check mentions against,
    so this falls back to a plain comma/"and" split instead."""
    cleaned = strip_filler_words(raw_text)

    if not canonical_skills:
        return [item.strip(" .") for item in _LIST_SPLIT_PATTERN.split(cleaned) if item.strip(" .")]

    words = cleaned.split()
    word_keys = [_skill_key(w) for w in words]

    matched = []
    for skill in canonical_skills:
        skill_key = _skill_key(skill)
        match_start = None
        for i in range(len(words)):
            for span in (1, 2, 3):
                if i + span > len(words):
                    continue
                if "".join(word_keys[i:i + span]) == skill_key:
                    match_start = i
                    break
            if match_start is not None:
                break
        if match_start is None:
            continue

        preceding_words = " ".join(words[max(0, match_start - 3):match_start])
        if _NEGATION_CUE_PATTERN.search(preceding_words):
            continue  # explicitly denied -- never recorded as a positive match

        matched.append(skill)
    return matched


# ---------- dispatcher ----------

NORMALIZERS = {
    "free_text": lambda raw, **kw: normalize_free_text(raw),
    "number": lambda raw, **kw: normalize_number_answer(raw),
    "yes_no": lambda raw, **kw: normalize_yes_no_answer(raw),
    "currency": lambda raw, **kw: normalize_currency_answer(raw),
    "duration": lambda raw, **kw: normalize_duration_answer(raw),
    "list": lambda raw, canonical_skills=None, **kw: normalize_list_answer(raw, canonical_skills),
}


def normalize_answer(raw_text, expected_answer_type, canonical_skills=None):
    """Single entry point: dispatches to the rule for `expected_answer_type`.
    Raises on an unknown type rather than silently falling back to free_text
    -- expected_answer_type is a fixed, closed vocabulary (Day 22), and a
    value outside it means something upstream is wrong, not that this
    function should guess."""
    if expected_answer_type not in NORMALIZERS:
        raise ValueError(
            f"Unknown expected_answer_type '{expected_answer_type}'. "
            f"Must be one of: {sorted(NORMALIZERS)}"
        )
    return NORMALIZERS[expected_answer_type](raw_text, canonical_skills=canonical_skills)