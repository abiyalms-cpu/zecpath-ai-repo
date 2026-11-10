from screening_ai.transcript_processor import process_transcript
from screening_ai.answer_understanding import (
    classify_intent,
    build_semantic_answer,
    understand_candidate_answers,
)

CANONICAL_SKILLS = ["JavaScript", "React", "Node.js", "MongoDB"]


def _record(raw_text, expected_answer_type, category_skills=None, **kwargs):
    return process_transcript(
        transcript_id="t1", candidate_id="c1", job_id="sde_ii", question_id="q1",
        raw_text=raw_text, expected_answer_type=expected_answer_type,
        canonical_skills=category_skills, **kwargs,
    )


# ---------- classify_intent: silence / partial / interrupted ----------

def test_silence_is_no_answer_regardless_of_category():
    record = _record("", "free_text")
    assert classify_intent(record, "experience") == "no_answer"


def test_partial_flag_overrides_content_quality():
    record = _record("I have about five years of", "free_text", partial=True)
    assert classify_intent(record, "experience") == "partial_answer"


def test_interrupted_flag_overrides_content_quality():
    record = _record("I worked at", "free_text", interrupted=True)
    assert classify_intent(record, "experience") == "partial_answer"


# ---------- classify_intent: structured types trust the Day 24 parse ----------

def test_parsed_number_is_answered():
    record = _record("five years", "number")
    assert classify_intent(record, "experience") == "answered"


def test_unparsed_number_falls_through_to_text_check():
    record = _record("a couple of years", "number")
    # short, vague, no real content -> vague, not silently "answered"
    assert classify_intent(record, "experience") == "vague"


def test_parsed_yes_no_is_answered():
    record = _record("yes", "yes_no")
    assert classify_intent(record, "location") == "answered"


def test_hedging_yes_no_is_vague():
    record = _record("maybe, it depends on the team", "yes_no")
    assert classify_intent(record, "location") == "vague"


def test_parsed_currency_is_answered():
    record = _record("12 lakhs per annum", "currency")
    assert classify_intent(record, "salary") == "answered"


def test_vague_currency_phrase_is_vague():
    record = _record("it's negotiable, market rate basically", "currency")
    assert classify_intent(record, "salary") == "vague"


def test_matched_skill_list_is_answered():
    record = _record(
        "react and node js, not so much mongo", "list", category_skills=CANONICAL_SKILLS,
    )
    assert classify_intent(record, "skills") == "answered"


def test_genuine_engaged_zero_match_skills_answer_is_answered():
    # Declines every listed skill, but clearly engages with the question --
    # documented judgment call in answer_understanding.py's honest-gaps note.
    record = _record(
        "I haven't used any of those, mostly backend work in Python",
        "list", category_skills=CANONICAL_SKILLS,
    )
    assert classify_intent(record, "skills") == "answered"


def test_off_topic_skills_answer_is_off_topic():
    record = _record(
        "I really love hiking and photography on weekends", "list", category_skills=CANONICAL_SKILLS,
    )
    assert classify_intent(record, "skills") == "off_topic"


# ---------- classify_intent: free_text ----------

def test_real_education_answer_is_answered_not_off_topic():
    # Open-vocabulary field -- education has no keyword set on purpose.
    record = _record("I did my B.Tech in Computer Science from VIT", "free_text")
    assert classify_intent(record, "education") == "answered"


def test_short_dismissive_answer_is_vague():
    record = _record("not really", "free_text")
    assert classify_intent(record, "education") == "vague"


def test_off_topic_free_text_answer_in_a_keyworded_category():
    record = _record("I really love hiking and photography on weekends", "free_text")
    assert classify_intent(record, "salary") == "off_topic"


def test_on_topic_free_text_answer_is_answered():
    record = _record("worked as a software engineer for three years at a startup", "free_text")
    assert classify_intent(record, "experience") == "answered"


def test_introduction_has_no_off_topic_check():
    # Open-ended by nature -- anything substantive counts.
    record = _record("I'm a product manager who loves building things people use daily", "free_text")
    assert classify_intent(record, "introduction") == "answered"


def test_very_short_answer_is_vague_even_without_a_vague_phrase():
    record = _record("good", "free_text")
    assert classify_intent(record, "experience") == "vague"


# ---------- build_semantic_answer ----------

def test_semantic_answer_has_the_fixed_shape():
    record = _record("yes", "yes_no")
    answer = build_semantic_answer(record, "location")
    assert set(answer.keys()) == {
        "question_id", "category", "expected_answer_type", "intent",
        "value", "normalized_text", "raw_text", "needs_follow_up",
    }


def test_needs_follow_up_is_false_for_answered():
    record = _record("yes", "yes_no")
    answer = build_semantic_answer(record, "location")
    assert answer["needs_follow_up"] is False


def test_needs_follow_up_is_true_for_vague():
    record = _record("not really", "free_text")
    answer = build_semantic_answer(record, "education")
    assert answer["needs_follow_up"] is True


# ---------- understand_candidate_answers ----------

def _full_session_records():
    answers = [
        ("sde_ii_introduction_01", "introduction", "free_text", "I'm a software engineer with five years of experience"),
        ("sde_ii_experience_01", "experience", "number", "five years"),
        ("sde_ii_skills_01", "skills", "list", "react and node js, not so much mongo"),
        ("sde_ii_location_01", "location", "yes_no", "yes"),
        ("sde_ii_salary_01", "salary", "currency", "12 lakhs per annum"),
        ("sde_ii_notice_period_01", "notice_period", "duration", ""),  # silence
        ("sde_ii_education_02", "education", "free_text", "not really"),  # vague
    ]
    records = []
    for question_id, category, answer_type, raw in answers:
        rec = process_transcript(
            transcript_id=f"t_{question_id}", candidate_id="c1", job_id="sde_ii",
            question_id=question_id, raw_text=raw, expected_answer_type=answer_type,
            canonical_skills=CANONICAL_SKILLS if answer_type == "list" else None,
        )
        records.append((rec, category))
    return records


def test_profile_extracts_the_four_named_fields():
    _, profile = understand_candidate_answers(_full_session_records(), canonical_skills=CANONICAL_SKILLS)
    assert profile["skills"] == ["React", "Node.js"]
    assert profile["experience_years"] == 5
    assert profile["salary_expectation"] == {"amount": 1_200_000, "currency": "INR"}
    assert profile["location_confirmed"] is True


def test_profile_flags_silence_and_vague_without_dropping_them():
    _, profile = understand_candidate_answers(_full_session_records(), canonical_skills=CANONICAL_SKILLS)
    assert profile["flags"]["no_answer"] == ["sde_ii_notice_period_01"]
    assert profile["flags"]["vague"] == ["sde_ii_education_02"]
    assert profile["availability_days"] is None  # never filled in -- it was silence, not guessed


def test_profile_returns_one_semantic_answer_per_record():
    semantic_answers, _ = understand_candidate_answers(_full_session_records(), canonical_skills=CANONICAL_SKILLS)
    assert len(semantic_answers) == 7
    assert {a["question_id"] for a in semantic_answers} == {
        "sde_ii_introduction_01", "sde_ii_experience_01", "sde_ii_skills_01",
        "sde_ii_location_01", "sde_ii_salary_01", "sde_ii_notice_period_01",
        "sde_ii_education_02",
    }