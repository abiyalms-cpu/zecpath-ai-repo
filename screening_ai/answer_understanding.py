"""
Day 25 -- Answer Intent & Understanding Engine.

Day 24 cleaned up *what the candidate said* (filler words gone, a number
parsed, a skill list matched). This module decides *whether that answer is
actually usable*, and if so, folds it into one structured picture of the
candidate -- the next layer on top of transcript_processor.py's output, not
a replacement for it.

Three pieces, matching the brief's three deliverables:

- classify_intent()            -- the intent classifier
- build_semantic_answer()      -- turns one Day 24 transcript record into
                                   one semantic answer object (the
                                   "structured answer format")
- understand_candidate_answers() -- the answer understanding engine: runs
                                   every answer in one screening session
                                   through the two functions above and
                                   folds the usable ones into one candidate
                                   profile (skills, experience, availability,
                                   salary expectation), flagging the rest.

Honest scope note: this is a rule-based classifier (keyword overlap + a
fixed vague-phrase list), not a trained intent model -- consistent with the
rest of this pipeline (scoring_engine, eligibility_engine are rule-based
too, for the same reason: predictable and auditable). It will miss genuinely
novel phrasing it has no keyword for. See the honest-gaps note at the bottom
of this file for where that shows up in practice.
"""

import re

from screening_ai.transcript_normalizer import strip_filler_words
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------- topic keywords, per question category ----------
# Deliberately small and literal -- a keyword set is auditable, a trained
# classifier isn't, and the brief asks for something that can flag off-topic
# answers, not understand arbitrary language. "introduction" has no keyword
# set on purpose: a self-introduction can legitimately be about almost
# anything, so off-topic detection is skipped for it (see classify_intent).

CATEGORY_TOPIC_KEYWORDS = {
    "introduction": set(),
    # Deliberately empty, same reasoning as "introduction": "which field was
    # it in" has no closed answer vocabulary (it could legitimately be
    # "Computer Science", "Mechanical", "Commerce", "Fine Arts" ...), so a
    # fixed keyword list would misfire on real, on-topic answers more often
    # than it would catch a genuinely off-topic one. Verified against a real
    # answer during build: "I did my B.Tech in Computer Science from VIT"
    # was wrongly flagged off_topic before this was emptied out.
    "education": set(),
    "experience": {"experience", "years", "worked", "work", "role", "position", "job", "year"},
    "skills": {"skill", "skills", "worked", "used", "experience", "familiar", "know", "proficient"},
    "location": {"location", "relocate", "relocation", "remote", "based", "city", "move", "willing"},
    "salary": {"salary", "pay", "compensation", "package", "lakh", "lakhs", "crore",
               "crores", "rupees", "expect", "expectation", "ctc"},
    "notice_period": {"notice", "join", "joining", "available", "availability",
                       "immediately", "weeks", "days", "month", "months"},
}

# Phrases that mean "I'm not really answering this" even though something
# was said -- checked as a substring, not an exact match, since a real
# answer is rarely just the bare phrase ("hmm, not really sure to be honest").
VAGUE_PHRASES = [
    "not sure", "don't know", "dont know", "can't say", "cant say", "no idea",
    "it depends", "depends on", "varies", "not applicable", "n/a", "tbd",
    "to be discussed", "market rate", "negotiable",
    "a couple", "a few", "a while", "some time",
]

_WORD_PATTERN = re.compile(r"[a-z']+")

# Below this many meaningful words, an answer is too thin to extract
# anything useful from, even if it isn't a recognized vague phrase.
_MIN_WORDS_FOR_SUBSTANCE = 4


def _words(text):
    return _WORD_PATTERN.findall((text or "").lower())


def classify_intent(record, category, canonical_skills=None):
    """Classifies one Day-24-processed transcript record into:
    - "no_answer"      -- silence, or normalized to nothing
    - "partial_answer" -- call was cut off or interrupted (Day 24 flags)
    - "vague"           -- something was said, but too thin or hedging to use
    - "off_topic"       -- an answer, but not to the question that was asked
    - "answered"        -- a usable answer

    Order matters: silence and partial/interrupted are checked first because
    they come from Day 24's own flags, not from guessing at the text.
    """
    if record["silence_detected"]:
        return "no_answer"
    if record.get("partial_answer") or record.get("interrupted"):
        return "partial_answer"

    expected_type = record["expected_answer_type"]
    parsed_value = record["parsed_value"]

    # Structured types: trust Day 24's own parse. A non-None/non-empty
    # parsed_value already means the normalizer found a real value, so
    # there's nothing more honest to check here than that.
    if expected_type in ("yes_no", "number", "currency", "duration") and parsed_value is not None:
        return "answered"
    if expected_type == "list" and parsed_value:
        return "answered"

    # Everything below runs for: free_text answers, and structured answers
    # the normalizer couldn't parse (unparsed number/currency/duration, a
    # yes_no that stayed null, or a list that matched no canonical skill).
    # normalized_text can come back "" by design in several of those cases
    # (Day 24's process_transcript -- see _stringify_normalized_result) even
    # though the candidate said something real, so that tells us nothing
    # about whether they actually answered. Fall back to the cleaned raw
    # text whenever normalized_text is empty but raw_text isn't.
    base_text = record["normalized_text"] or ""
    if not base_text.strip():
        base_text = strip_filler_words(record["raw_text"])

    words = _words(base_text)
    if not words:
        return "no_answer"

    lowered = base_text.lower()
    if any(phrase in lowered for phrase in VAGUE_PHRASES):
        return "vague"

    keywords = CATEGORY_TOPIC_KEYWORDS.get(category, set())
    if category == "skills" and canonical_skills:
        keywords = keywords | {s.lower() for s in canonical_skills}

    if keywords and len(words) >= _MIN_WORDS_FOR_SUBSTANCE:
        if not (keywords & set(words)):
            return "off_topic"

    if len(words) < _MIN_WORDS_FOR_SUBSTANCE:
        return "vague"

    return "answered"


def build_semantic_answer(record, category, canonical_skills=None):
    """The "structured answer format": one consistent object per answer,
    whatever its expected_answer_type was, so a later step (scoring,
    eligibility re-check) can read every answer the same way instead of
    branching on type itself."""
    intent = classify_intent(record, category, canonical_skills=canonical_skills)
    return {
        "question_id": record["question_id"],
        "category": category,
        "expected_answer_type": record["expected_answer_type"],
        "intent": intent,
        "value": record["parsed_value"],
        "normalized_text": record["normalized_text"],
        "raw_text": record["raw_text"],
        "needs_follow_up": intent in ("vague", "off_topic", "no_answer", "partial_answer"),
    }


_PROFILE_EXTRACTORS = {
    ("skills", "list"): lambda profile, value: profile["skills"].extend(
        s for s in (value or []) if s not in profile["skills"]
    ),
    ("experience", "number"): lambda profile, value: profile.__setitem__("experience_years", value),
    ("notice_period", "duration"): lambda profile, value: profile.__setitem__("availability_days", value),
    ("salary", "currency"): lambda profile, value: profile.__setitem__("salary_expectation", value),
    ("location", "yes_no"): lambda profile, value: profile.__setitem__("location_confirmed", value),
}


def understand_candidate_answers(records_with_categories, canonical_skills=None):
    """The answer understanding engine. Takes a list of
    (transcript_record, category) pairs for one screening session -- every
    transcript_record already produced by Day 24's process_transcript() --
    and returns (semantic_answers, profile):

    - semantic_answers: one structured object per answer (build_semantic_answer)
    - profile: the four fields the brief names by name (skills, experience,
      availability, salary expectation), filled in only from answers
      classified "answered", plus every other answer's question_id sorted
      into a flags bucket by intent -- so a vague or off-topic answer is
      never silently dropped, only kept out of the trusted fields."""
    semantic_answers = []
    profile = {
        "skills": [],
        "experience_years": None,
        "availability_days": None,
        "salary_expectation": None,
        "location_confirmed": None,
        "flags": {"vague": [], "off_topic": [], "no_answer": [], "partial_answer": []},
    }

    for record, category in records_with_categories:
        answer = build_semantic_answer(record, category, canonical_skills=canonical_skills)
        semantic_answers.append(answer)

        if answer["intent"] in profile["flags"]:
            profile["flags"][answer["intent"]].append(answer["question_id"])
            continue

        extractor = _PROFILE_EXTRACTORS.get((category, answer["expected_answer_type"]))
        if extractor:
            extractor(profile, answer["value"])

    return semantic_answers, profile


# ---------- Honest gaps, flagged rather than guessed at ----------
#
# - Off-topic detection is a keyword-overlap check, not language
#   understanding. A genuine on-topic answer phrased with none of the
#   listed keywords ("I'm all set salary-wise, whatever's fair") can be
#   misclassified as off-topic. The keyword lists were built from the real
#   question text in data/screening_questions/, not guessed cold, but they
#   are not exhaustive.
# - "vague" vs "off_topic" for an empty skills list is a real judgment call
#   this module makes: a candidate who clearly addresses the skills
#   question but claims none of the listed skills ("I haven't used any of
#   those, mostly backend Python") is still scored "answered" here, because
#   the keyword overlap on "used" is real engagement with the question --
#   even though the resulting skills list is empty. A future day re-scoring
#   eligibility off this profile should treat an empty `skills` list as
#   "answered zero matches," not as "didn't answer."
# - This module has no visibility into a candidate's tone or sarcasm --
#   only the words Day 24 already normalized.
