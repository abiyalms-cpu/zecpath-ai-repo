"""
The "clean transcript processor" Day 24 asks for: takes one raw answer as it
would come back from a speech-to-text service, and returns one finished
transcript record in the exact shape TRANSCRIPT_DATA_ARCHITECTURE.md
(section 1) already defined.

This is the piece that was still just a schema on paper after Day 23 --
transcript_normalizer.py supplies the per-type rules, this module is what
actually calls them and assembles the record, including the three things
Day 24's brief names by name that Day 23's schema didn't yet have a field
for: interrupted speech, partial answers, and silence detection.

Honest gap, stated once here rather than guessed at silently: there is still
no real telephony/STT integration anywhere in this repo (screening_ai/
call_handler.py is still the Day 1 stub). So `partial` and `interrupted`
are accepted as explicit signals this function is ready to receive from a
real call event stream once one exists -- they are not detected from
raw_text alone, because text by itself can't reliably tell a cut-off answer
from one the candidate simply ended short.
"""

from datetime import datetime, timezone

from screening_ai.transcript_normalizer import normalize_answer
from utils.logger import get_logger

logger = get_logger(__name__)


def _now_iso():
    # Same format education_tagger.py / experience_tagger.py already use for
    # extracted_at, per TRANSCRIPT_DATA_ARCHITECTURE.md section 3.
    return datetime.now(timezone.utc).isoformat()


def _stringify_normalized_result(result, expected_answer_type):
    """normalized_text is documented as a string field (architecture doc,
    section 1 field table), but three of the per-type rules naturally
    produce a structured value (a number, a {amount, currency} pair, a
    number of days). Rather than quietly changing normalized_text's type,
    this renders a clean string for it and the caller also gets the
    structured value back separately as `parsed_value` -- see
    process_transcript's return shape."""
    if expected_answer_type == "free_text":
        return result, result

    if expected_answer_type == "list":
        return ", ".join(result) if result else "", result

    if expected_answer_type == "yes_no":
        if result is True:
            return "Yes", True
        if result is False:
            return "No", False
        return "", None

    if expected_answer_type == "number":
        if result["unparsed"]:
            return result["value"], None
        return str(result["value"]), result["value"]

    if expected_answer_type == "currency":
        if result["unparsed"]:
            return result["value"], None
        return f"{result['currency']} {result['amount']:,}", {
            "amount": result["amount"],
            "currency": result["currency"],
        }

    if expected_answer_type == "duration":
        if result["unparsed"]:
            return result["value"], None
        return f"{result['days']} days", result["days"]

    raise ValueError(f"Unhandled expected_answer_type '{expected_answer_type}'")


def process_transcript(
    *,
    transcript_id,
    candidate_id,
    job_id,
    question_id,
    raw_text,
    expected_answer_type,
    confidence_level=None,
    language="en",
    canonical_skills=None,
    partial=False,
    interrupted=False,
    timestamp=None,
):
    """Builds one full transcript record. `raw_text` is stored exactly as
    received and never altered -- every other field is derived from it."""
    silence_detected = raw_text is None or raw_text.strip() == ""

    if silence_detected:
        # Nothing was said -- there is nothing honest to normalize, so this
        # does not run raw_text through the normalizer at all, and a
        # provider-reported confidence (if any was even returned) is
        # replaced with 0.0: confidence in recognizing silence as silence
        # isn't the same thing as confidence in a transcribed answer.
        logger.info(f"Silence detected for {transcript_id}")
        normalized_text = None
        parsed_value = None
        confidence_level = 0.0
    else:
        raw_result = normalize_answer(raw_text, expected_answer_type, canonical_skills=canonical_skills)
        normalized_text, parsed_value = _stringify_normalized_result(raw_result, expected_answer_type)

    return {
        "transcript_id": transcript_id,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "question_id": question_id,
        "timestamp": timestamp or _now_iso(),
        "raw_text": raw_text,
        "normalized_text": normalized_text,
        "parsed_value": parsed_value,
        "confidence_level": confidence_level,
        "expected_answer_type": expected_answer_type,
        "language": language,
        "silence_detected": silence_detected,
        "partial_answer": bool(partial),
        "interrupted": bool(interrupted),
    }