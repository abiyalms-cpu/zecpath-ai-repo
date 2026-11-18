import json

from screening_ai.transcript_processor import process_transcript
from screening_ai.answer_understanding import build_semantic_answer
from screening_ai.behavioral_signals import (
    hesitation_score,
    length_signal,
    sentiment_score,
    uncertainty_score,
    extract_year_mentions,
    detect_contradictions,
    analyze_answer_behavior,
    build_behavioral_report,
)

CANONICAL_SKILLS = ["Excel", "Power BI", "SAP FICO"]


def _answer(raw_text, expected_answer_type, category, question_id="q1", canonical_skills=None, **kwargs):
    record = process_transcript(
        transcript_id="t1", candidate_id="c1", job_id="financial_analyst", question_id=question_id,
        raw_text=raw_text, expected_answer_type=expected_answer_type,
        canonical_skills=canonical_skills, **kwargs,
    )
    return build_semantic_answer(record, category, canonical_skills=canonical_skills)


# ---------- hesitation_score ----------

def test_hesitation_counts_filler_words_from_raw_text():
    result = hesitation_score("um, so, I think, uh, I worked there for like two years")
    assert result["filler_count"] == 4
    assert result["word_count"] == 12
    assert result["level"] == "high"


def test_hesitation_is_low_for_a_clean_answer():
    result = hesitation_score("I worked as a financial analyst for six years at a consulting firm")
    assert result["filler_count"] == 0
    assert result["level"] == "low"


def test_hesitation_is_na_for_empty_text():
    result = hesitation_score("")
    assert result["level"] == "n/a"
    assert result["word_count"] == 0


def test_hesitation_does_not_match_filler_words_inside_other_words():
    # "basically" shouldn't double-count, and "solid" shouldn't match "so"
    result = hesitation_score("I gave a solid and basically complete answer")
    assert result["filler_count"] == 1


# ---------- length_signal ----------

def test_length_signal_labels_brief_typical_lengthy():
    assert length_signal("not really")["label"] == "brief"
    assert length_signal("I worked as a financial analyst for six years at a firm")["label"] == "typical"
    assert length_signal(" ".join(["word"] * 25))["label"] == "lengthy"


def test_length_signal_none_for_empty():
    result = length_signal("")
    assert result["label"] == "none"
    assert result["word_count"] == 0


# ---------- sentiment_score ----------

def test_sentiment_positive():
    result = sentiment_score("I really enjoyed the role and felt confident and strong in my skills")
    assert result["label"] == "positive"
    assert result["positive_count"] == 3


def test_sentiment_negative():
    result = sentiment_score("it was a difficult and stressful project and I struggled a lot")
    assert result["label"] == "negative"
    assert result["negative_count"] >= 2


def test_sentiment_neutral_when_no_sentiment_words_found():
    result = sentiment_score("I did my MBA in Finance from Delhi University")
    assert result["label"] == "neutral"
    assert result["score"] == 0.0


def test_sentiment_mixed_when_roughly_balanced():
    result = sentiment_score("it was a great team but a difficult project")
    assert result["label"] == "mixed"


# ---------- uncertainty_score ----------

def test_uncertainty_is_none_for_no_answer():
    answer = _answer("", "free_text", "experience")
    assert uncertainty_score(answer)["score"] is None


def test_uncertainty_is_high_for_vague_with_hedges():
    answer = _answer("I think, maybe, it depends", "free_text", "notice_period")
    result = uncertainty_score(answer)
    assert answer["intent"] == "vague"
    assert result["score"] > 0.7


def test_uncertainty_is_zero_for_a_clean_confident_answer():
    answer = _answer("I worked as a financial analyst for six years at a consulting firm", "free_text", "experience")
    result = uncertainty_score(answer)
    assert result["score"] == 0.0
    assert result["level"] == "low"


def test_uncertainty_picks_up_hedge_inside_an_otherwise_answered_response():
    answer = _answer(
        "I think I worked as a financial analyst for six years at a consulting firm", "free_text", "experience",
    )
    assert answer["intent"] == "answered"
    result = uncertainty_score(answer)
    assert result["hedge_count"] == 1
    assert result["score"] > 0.0


# ---------- extract_year_mentions ----------

def test_extract_year_mentions_digit_form():
    assert extract_year_mentions("I have 7 years of experience") == [7]


def test_extract_year_mentions_spoken_form():
    assert extract_year_mentions("I have about seven years of experience") == [7]


def test_extract_year_mentions_multiple_in_one_text():
    mentions = extract_year_mentions("worked for six years, then three years at the first job")
    assert mentions == [6, 3]


def test_extract_year_mentions_empty_for_no_year_talk():
    assert extract_year_mentions("I did my MBA in Finance from Delhi University") == []


def test_extract_year_mentions_empty_text():
    assert extract_year_mentions("") == []
    assert extract_year_mentions(None) == []


# ---------- detect_contradictions ----------

def test_detect_contradictions_flags_a_real_mismatch():
    answers = [
        _answer("seven years", "number", "experience", question_id="exp_01"),
        _answer("I worked for six years at a consulting firm", "free_text", "experience", question_id="exp_02"),
    ]
    contradictions = detect_contradictions(answers)
    assert len(contradictions) == 1
    assert contradictions[0]["difference"] == 1.0


def test_detect_contradictions_allows_small_rounding_gap():
    answers = [
        _answer("five years", "number", "experience", question_id="exp_01"),
        _answer("about five years, give or take", "free_text", "experience", question_id="exp_02"),
    ]
    assert detect_contradictions(answers) == []


def test_detect_contradictions_empty_when_consistent():
    answers = [
        _answer("seven years", "number", "experience", question_id="exp_01"),
        _answer("I did my MBA in Finance from Delhi University", "free_text", "education", question_id="edu_01"),
    ]
    assert detect_contradictions(answers) == []


def test_detect_contradictions_ignores_same_question_duplicate():
    # same question_id shouldn't be compared against itself
    answers = [_answer("seven years", "number", "experience", question_id="exp_01")]
    assert detect_contradictions(answers) == []


# ---------- analyze_answer_behavior / build_behavioral_report ----------

def test_analyze_answer_behavior_bundles_all_four_signals():
    answer = _answer("um, I think I worked for six years", "free_text", "experience")
    result = analyze_answer_behavior(answer)
    assert set(result.keys()) == {"question_id", "hesitation", "length", "sentiment", "uncertainty"}


def test_build_behavioral_report_averages_skip_unavailable_signals():
    answers = [
        _answer("", "free_text", "experience", question_id="q1"),  # silence: uncertainty unavailable
        _answer("I enjoyed the work and felt confident", "free_text", "experience", question_id="q2"),
    ]
    report = build_behavioral_report(answers)
    assert report["average_uncertainty_score"] is not None  # only q2 counted, not averaged with a guess
    assert len(report["per_answer"]) == 2


# ---------- end to end against real repo data: the Day 26 gap, closed ----------

def test_full_session_catches_the_day26_documented_contradiction():
    jd = json.load(open("data/screening_questions/financial_analyst_questions.json"))
    canonical_skills = ["Excel", "Power BI", "SAP FICO"]

    answers_text = {
        "financial_analyst_introduction_01": "um, so, I am a financial analyst with about seven years of experience",
        "financial_analyst_education_01": "I did my MBA in Finance from Delhi University",
        "financial_analyst_education_02": "not really",
        "financial_analyst_experience_01": "seven years",
        "financial_analyst_experience_02": "I think I worked as a financial analyst for six years at a consulting firm",
        "financial_analyst_skills_01": "excel and power bi, and also SAP FICO a bit",
        "financial_analyst_skills_02": "I really love hiking and photography on weekends",
        "financial_analyst_location_01": "yes I am based in Mumbai",
        "financial_analyst_salary_01": "around 15 lakhs per annum",
        "financial_analyst_notice_period_01": "",
    }

    semantic_answers = []
    for q in jd["questions"]:
        record = process_transcript(
            transcript_id=f"t_{q['id']}", candidate_id="karthik_subramaniam.docx",
            job_id="financial_analyst", question_id=q["id"],
            raw_text=answers_text[q["id"]], expected_answer_type=q["expected_answer_type"],
            canonical_skills=canonical_skills if q["expected_answer_type"] == "list" else None,
        )
        semantic_answers.append(build_semantic_answer(record, q["category"], canonical_skills=canonical_skills))

    report = build_behavioral_report(semantic_answers)

    # The exact gap Day 26's screening_scoring.py named: "seven years" (intro
    # + dedicated experience question) vs "six years" (a later experience
    # question) -- not caught by consistency_score, which only checks the
    # resume. This module checks the candidate against themselves.
    assert len(report["contradictions"]) == 2
    mismatched_pairs = {(c["question_a"], c["question_b"]) for c in report["contradictions"]}
    assert ("financial_analyst_experience_01", "financial_analyst_experience_02") in mismatched_pairs
    assert report["communication_strength"] == "needs_follow_up"
    assert len(report["per_answer"]) == 10