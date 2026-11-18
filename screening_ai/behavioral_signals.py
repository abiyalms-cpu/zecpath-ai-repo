"""
Day 27 -- Confidence & Sentiment Signal Analysis.

Days 24-26 decided what a candidate said, whether it was usable, and how
good it was. This module looks at HOW it was said -- hesitation, length,
tone, hedging -- and, the one genuinely new piece, whether the candidate's
own answers agree with each other across the call.

Honest constraint, stated once here rather than repeated per function:
there is still no real telephony/audio integration anywhere in this repo
(screening_ai/call_handler.py is still the Day 1 stub), so there is no real
speech pace, tone of voice, or pause timing to measure. Everything below is
built from the TEXT Day 24 already produced -- filler-word counts, word
counts, word choice -- and is named for what it actually measures, not for
what it would measure if real audio existed.

Five pieces, matching the brief:
- hesitation_score()       -- "Detect hesitation patterns"
- length_signal()          -- "Measure response length and pace" (length only; see above)
- sentiment_score()        -- "Identify positive/negative sentiment"
- uncertainty_score()      -- "Detect uncertainty ..."
- detect_contradictions()  -- "... and contradictions" -- closes the exact
                               gap screening_scoring.py's own honest-gaps
                               note flagged on Day 26 (a candidate who said
                               "seven years" and, two questions later,
                               "worked for six years" went uncaught).

analyze_answer_behavior() and build_behavioral_report() are the "confidence
analysis logic" / "behavioral indicators report" deliverables: one signal
bundle per answer, then one session-level report.
"""

import re

from screening_ai.transcript_normalizer import FILLER_WORDS, spoken_number_to_digit
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------- hesitation ----------

_FILLER_TOKEN_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(FILLER_WORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_WORD_PATTERN = re.compile(r"[a-z']+")


def hesitation_score(raw_text):
    """Hesitation is measured on raw_text, not normalized_text -- Day 24's
    normalizer already strips filler words out to produce normalized_text,
    so that signal would be gone by the time it reached this module.
    Reuses transcript_normalizer's own FILLER_WORDS list rather than
    maintaining a second one that could drift out of sync with it.

    Returns {"filler_count", "word_count", "ratio", "level"}. `ratio` is
    filler words as a fraction of all words -- a short answer with one
    "um" reads very differently from a long one with the same count."""
    words = _WORD_PATTERN.findall((raw_text or "").lower())
    filler_matches = _FILLER_TOKEN_PATTERN.findall(raw_text or "")

    word_count = len(words)
    filler_count = len(filler_matches)
    ratio = round(filler_count / word_count, 4) if word_count else 0.0

    if word_count == 0:
        level = "n/a"
    elif ratio >= 0.25:
        level = "high"
    elif ratio >= 0.1:
        level = "moderate"
    else:
        level = "low"

    return {"filler_count": filler_count, "word_count": word_count, "ratio": ratio, "level": level}


# ---------- length (text-length proxy for "pace") ----------

def length_signal(normalized_text):
    """Response length as a text-based proxy. Explicitly NOT "pace" in any
    real sense -- there is no call duration or words-per-minute anywhere in
    this repo to compute actual pace from, so this only ever reports word
    count and a relative label, never a rate."""
    word_count = len((normalized_text or "").split())
    if word_count == 0:
        label = "none"
    elif word_count < 4:
        label = "brief"
    elif word_count <= 20:
        label = "typical"
    else:
        label = "lengthy"
    return {"word_count": word_count, "label": label}


# ---------- sentiment ----------
# A small, literal lexicon -- auditable, like every other rule-based
# component in this repo, not a trained sentiment model. Built from words
# that would plausibly appear in a screening-call answer, not a generic
# product-review wordlist.

POSITIVE_WORDS = {
    "great", "good", "excellent", "confident", "enjoy", "enjoyed", "love",
    "loved", "passionate", "strong", "comfortable", "happy", "excited",
    "proud", "successful", "effective", "capable", "skilled",
}
NEGATIVE_WORDS = {
    "bad", "poor", "difficult", "struggle", "struggled", "weak", "worried",
    "nervous", "unsure", "frustrated", "failed", "failure", "problem",
    "problems", "hate", "hated", "dislike", "stressful", "stressed",
}


def sentiment_score(text):
    """A (positive_count - negative_count) tally normalized by the number
    of sentiment words actually found, not by total word count -- a short
    answer with one positive word is fully positive, not diluted toward
    neutral just because the sentence around it was short."""
    words = _WORD_PATTERN.findall((text or "").lower())
    positive_count = sum(1 for w in words if w in POSITIVE_WORDS)
    negative_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    total = positive_count + negative_count

    if total == 0:
        return {"positive_count": 0, "negative_count": 0, "score": 0.0, "label": "neutral"}

    score = round((positive_count - negative_count) / total, 4)
    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "mixed"
    return {"positive_count": positive_count, "negative_count": negative_count, "score": score, "label": label}


# ---------- uncertainty ----------
# Hedge words are distinct from answer_understanding.py's VAGUE_PHRASES:
# a vague answer has too little content to use at all ("not sure"), while a
# hedge can sit inside an otherwise perfectly usable answer ("I think it
# was around five years") -- real content, delivered with uncertainty. Both
# signals matter here for different reasons, so uncertainty_score folds in
# the intent Day 25 already computed rather than re-deciding vagueness.

HEDGE_WORDS = ["i think", "i guess", "probably", "maybe", "sort of", "kind of", "possibly", "i suppose"]


def uncertainty_score(answer):
    """Takes one Day 25 semantic answer object. Combines its own intent
    (an answer already labeled "vague" is uncertain by definition) with a
    hedge-word count on top of that, so an "answered" response that's
    still hedged ("I think around five years") is caught too, not just
    outright vague ones."""
    text = (answer.get("normalized_text") or answer.get("raw_text") or "").lower()
    hedge_count = sum(1 for phrase in HEDGE_WORDS if phrase in text)

    if answer["intent"] == "vague":
        base = 0.7
    elif answer["intent"] in ("no_answer", "partial_answer"):
        base = None  # nothing substantive enough to call "uncertain" vs "certain"
    else:
        base = 0.0

    if base is None:
        return {"hedge_count": hedge_count, "score": None, "level": "n/a"}

    score = min(1.0, base + hedge_count * 0.15)
    level = "high" if score >= 0.6 else "moderate" if score >= 0.3 else "low"
    return {"hedge_count": hedge_count, "score": round(score, 4), "level": level}


# ---------- contradictions ----------
# Closes screening_scoring.py's own documented gap: Consistency (Day 26)
# only checks an answer against the resume. This checks the candidate's
# answers against EACH OTHER within the same call -- specifically, every
# place a number of years gets mentioned, in any category, not just the
# dedicated experience question, because a real candidate mentions years of
# experience in their self-introduction too (seen during Day 25's own
# build-time testing).

_YEAR_UNIT_PATTERN = re.compile(r"\byears?\b|\byrs?\b", re.IGNORECASE)
_DIGIT_BEFORE_YEAR_PATTERN = re.compile(r"\b(\d{1,2})\s*(?:years?|yrs?)\b", re.IGNORECASE)

# Tolerance before two year-mentions count as a real contradiction rather
# than honest rounding ("about five" vs "five and a half"). Year mentions
# are almost always whole numbers in speech, so even a 1-year gap ("seven
# years" vs "six years" -- the exact case Day 26 documented as missed) is
# a real contradiction, not rounding -- only a half-year or less is given
# the benefit of the doubt.
_CONTRADICTION_TOLERANCE_YEARS = 0.5


def extract_year_mentions(text):
    """Finds every "<number> year(s)" mention in a piece of text, spoken or
    digit form -- "seven years", "7 years", "worked for six years at...".
    Reuses transcript_normalizer.spoken_number_to_digit for the word form
    rather than writing a second number-word parser."""
    if not text:
        return []

    found = [int(m) for m in _DIGIT_BEFORE_YEAR_PATTERN.findall(text)]

    words = _WORD_PATTERN.findall(text.lower())
    for i, word in enumerate(words):
        if word in ("year", "years", "yr", "yrs"):
            for span in (1, 2):
                start = i - span
                if start < 0:
                    continue
                phrase = " ".join(words[start:i])
                value = spoken_number_to_digit(phrase)
                if value is not None:
                    found.append(value)
                    break
    return found


def detect_contradictions(semantic_answers):
    """Collects every year-mention across every answer in the session
    (structured `number`-type answers use their already-parsed value
    directly; everything else is text-scanned), then flags any pair whose
    values disagree by more than the tolerance -- the exact pattern
    screening_scoring.py's honest-gaps note named as uncaught."""
    mentions = []  # list of (question_id, value)

    for answer in semantic_answers:
        if answer["expected_answer_type"] == "number" and answer["value"] is not None:
            mentions.append((answer["question_id"], float(answer["value"])))
            continue
        text = answer.get("normalized_text") or answer.get("raw_text") or ""
        for value in extract_year_mentions(text):
            mentions.append((answer["question_id"], float(value)))

    contradictions = []
    for i in range(len(mentions)):
        for j in range(i + 1, len(mentions)):
            qid_a, val_a = mentions[i]
            qid_b, val_b = mentions[j]
            if qid_a == qid_b:
                continue
            if abs(val_a - val_b) > _CONTRADICTION_TOLERANCE_YEARS:
                contradictions.append({
                    "question_a": qid_a, "value_a": val_a,
                    "question_b": qid_b, "value_b": val_b,
                    "difference": round(abs(val_a - val_b), 2),
                })
    return contradictions


# ---------- per-answer bundle and session report ----------

def analyze_answer_behavior(answer):
    """One behavioral signal bundle for a single Day 25 semantic answer --
    the "confidence analysis logic" deliverable, applied per answer."""
    return {
        "question_id": answer["question_id"],
        "hesitation": hesitation_score(answer.get("raw_text")),
        "length": length_signal(answer.get("normalized_text")),
        "sentiment": sentiment_score(answer.get("normalized_text")),
        "uncertainty": uncertainty_score(answer),
    }


def build_behavioral_report(semantic_answers):
    """The "behavioral indicators report" deliverable: every answer's
    signal bundle, plus session-level contradictions and an overall
    communication-strength label. Averages are computed only over answers
    where a signal was actually available (e.g. uncertainty is None for
    silence/partial answers) -- never padded with a guessed value."""
    per_answer = [analyze_answer_behavior(a) for a in semantic_answers]
    contradictions = detect_contradictions(semantic_answers)

    hesitation_ratios = [a["hesitation"]["ratio"] for a in per_answer if a["hesitation"]["word_count"] > 0]
    uncertainty_scores = [a["uncertainty"]["score"] for a in per_answer if a["uncertainty"]["score"] is not None]
    sentiment_scores = [a["sentiment"]["score"] for a in per_answer if a["sentiment"]["label"] != "neutral"]

    avg_hesitation = round(sum(hesitation_ratios) / len(hesitation_ratios), 4) if hesitation_ratios else None
    avg_uncertainty = round(sum(uncertainty_scores) / len(uncertainty_scores), 4) if uncertainty_scores else None
    avg_sentiment = round(sum(sentiment_scores) / len(sentiment_scores), 4) if sentiment_scores else None

    # A simple, inspectable strength label -- not a fifth score to argue
    # over, just a human-readable summary of the three averages above.
    if contradictions or (avg_uncertainty is not None and avg_uncertainty >= 0.6) or \
       (avg_hesitation is not None and avg_hesitation >= 0.25):
        strength = "needs_follow_up"
    elif (avg_uncertainty is not None and avg_uncertainty >= 0.3) or \
         (avg_hesitation is not None and avg_hesitation >= 0.1):
        strength = "moderate"
    else:
        strength = "strong"

    return {
        "per_answer": per_answer,
        "contradictions": contradictions,
        "average_hesitation_ratio": avg_hesitation,
        "average_uncertainty_score": avg_uncertainty,
        "average_sentiment_score": avg_sentiment,
        "communication_strength": strength,
    }


# ---------- Honest gaps ----------
#
# - "Pace" is reported as text length only. Real pace (words per minute)
#   needs call duration data this repo has never had -- screening_ai/
#   call_handler.py has never placed a real call. Renaming length_signal()
#   to claim it measures pace would be the same mistake Day 24 explicitly
#   avoided with the STT "accuracy" report.
# - The sentiment lexicon is small and literal. A real answer using none of
#   these exact words scores "neutral" by default -- that's an honest
#   default (no opinion found), not a claim that the answer was emotionally
#   flat.
# - Contradiction detection only covers "years of experience" mentions,
#   because that's the specific, concrete gap Day 26 found and named. A
#   candidate contradicting themselves on salary, location, or skills
#   across two answers is not caught by this -- a real but narrower gap
#   than the one this closes, left for a future day rather than guessed at
#   with a less-tested generic rule.