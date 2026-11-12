from screening_ai.transcript_processor import process_transcript
from screening_ai.answer_understanding import build_semantic_answer
from screening_ai.screening_scoring import (
    clarity_score,
    relevance_score,
    completeness_score,
    consistency_score,
    score_answer,
    aggregate_screening_score,
    score_screening_session,
    load_resume_cross_check,
    explain_question_score,
    explain_screening_score,
)

CANONICAL_SKILLS = ["Excel", "Power BI", "SAP FICO"]


def _answer(raw_text, expected_answer_type, category, canonical_skills=None, **kwargs):
    record = process_transcript(
        transcript_id="t1", candidate_id="c1", job_id="financial_analyst", question_id="q1",
        raw_text=raw_text, expected_answer_type=expected_answer_type,
        canonical_skills=canonical_skills, **kwargs,
    )
    return build_semantic_answer(record, category, canonical_skills=canonical_skills)


# ---------- clarity_score ----------

def test_clarity_is_none_for_no_answer():
    answer = _answer("", "free_text", "experience")
    assert clarity_score(answer) is None


def test_clarity_is_full_for_a_parsed_structured_answer():
    answer = _answer("seven years", "number", "experience")
    assert clarity_score(answer) == 1.0


def test_clarity_is_low_for_an_unparsed_structured_answer():
    answer = _answer("a couple of years", "number", "experience")
    assert clarity_score(answer) == 0.3


def test_clarity_is_full_for_a_substantial_free_text_answer():
    answer = _answer("I worked as a financial analyst for six years at a consulting firm", "free_text", "experience")
    assert clarity_score(answer) == 1.0


def test_clarity_is_low_for_a_thin_free_text_answer():
    answer = _answer("not really", "free_text", "education")
    assert clarity_score(answer) == 0.3


def test_clarity_for_matched_skills_list_is_full():
    answer = _answer("excel and power bi", "list", "skills", canonical_skills=CANONICAL_SKILLS)
    assert clarity_score(answer) == 1.0


def test_clarity_for_genuine_zero_match_skills_is_partial():
    answer = _answer(
        "I haven't used any of those, mostly backend work in Python", "list", "skills",
        canonical_skills=CANONICAL_SKILLS,
    )
    assert clarity_score(answer) == 0.7


# ---------- relevance_score ----------

def test_relevance_is_none_for_no_answer():
    answer = _answer("", "free_text", "experience")
    assert relevance_score(answer) is None


def test_relevance_is_zero_for_off_topic():
    answer = _answer("I really love hiking and photography on weekends", "free_text", "salary")
    assert relevance_score(answer) == 0.0


def test_relevance_is_full_for_on_topic_answer():
    answer = _answer("worked as a financial analyst for six years", "free_text", "experience")
    assert relevance_score(answer) == 1.0


# ---------- completeness_score ----------

def test_completeness_is_zero_for_no_answer():
    answer = _answer("", "free_text", "experience")
    assert completeness_score(answer) == 0.0


def test_completeness_is_full_for_answered():
    answer = _answer("seven years", "number", "experience")
    assert completeness_score(answer) == 1.0


def test_completeness_is_partial_for_vague():
    answer = _answer("not really", "free_text", "education")
    assert completeness_score(answer) == 0.5


def test_completeness_is_low_for_partial_answer_flag():
    answer = _answer("I have about three years of", "free_text", "experience", partial=True)
    assert completeness_score(answer) == 0.4


# ---------- consistency_score ----------

def test_consistency_experience_close_match_is_full():
    answer = _answer("seven years", "number", "experience")
    # resume says 88 months = 7.33 years -- well within 1 year
    assert consistency_score(answer, "experience", resume_experience_months=88) == 1.0


def test_consistency_experience_far_mismatch_is_low():
    answer = _answer("one year", "number", "experience")
    assert consistency_score(answer, "experience", resume_experience_months=88) == 0.2


def test_consistency_experience_none_without_resume_data():
    answer = _answer("seven years", "number", "experience")
    assert consistency_score(answer, "experience", resume_experience_months=None) is None


def test_consistency_skills_partial_overlap():
    answer = _answer("excel, power bi, and sap fico", "list", "skills", canonical_skills=CANONICAL_SKILLS)
    score = consistency_score(answer, "skills", resume_skills={"Excel", "Power BI"})
    # 2 of 3 claimed skills are in the resume
    assert score == 0.6667


def test_consistency_skills_none_without_resume_data():
    answer = _answer("excel and power bi", "list", "skills", canonical_skills=CANONICAL_SKILLS)
    assert consistency_score(answer, "skills", resume_skills=None) is None


def test_consistency_is_none_for_categories_without_ground_truth():
    answer = _answer("around 15 lakhs per annum", "currency", "salary")
    assert consistency_score(answer, "salary", resume_skills={"Excel"}, resume_experience_months=88) is None


# ---------- score_answer: redistribution ----------

def test_score_answer_redistributes_weight_when_consistency_unavailable():
    # salary: clarity, relevance, completeness available; consistency is not
    answer = _answer("around 15 lakhs per annum", "currency", "salary")
    result = score_answer(answer, "salary")
    consistency_item = next(b for b in result["breakdown"] if b["component"] == "consistency")
    assert consistency_item["available"] is False
    assert consistency_item["normalized_weight"] == 0.0
    other_items = [b for b in result["breakdown"] if b["component"] != "consistency"]
    assert all(abs(b["normalized_weight"] - 1 / 3) < 0.01 for b in other_items)


def test_score_answer_final_score_is_bounded():
    answer = _answer("seven years", "number", "experience")
    result = score_answer(answer, "experience", resume_experience_months=88)
    assert 0.0 <= result["final_score"] <= 1.0


def test_score_answer_no_answer_scores_only_completeness():
    answer = _answer("", "duration", "notice_period")
    result = score_answer(answer, "notice_period")
    assert result["final_score"] == 0.0
    completeness_item = next(b for b in result["breakdown"] if b["component"] == "completeness")
    assert completeness_item["normalized_weight"] == 1.0


# ---------- aggregate_screening_score ----------

def test_aggregate_uses_scoring_importance_as_weights():
    results = [
        {"question_id": "q1", "category": "experience", "intent": "answered", "final_score": 1.0, "breakdown": []},
        {"question_id": "q2", "category": "salary", "intent": "answered", "final_score": 0.0, "breakdown": []},
    ]
    importance = {"q1": 0.8, "q2": 0.2}
    result = aggregate_screening_score(results, importance)
    assert result["final_screening_score"] == 0.8  # 1.0*0.8 + 0.0*0.2


def test_aggregate_redistributes_when_a_question_has_no_importance_entry():
    results = [
        {"question_id": "q1", "category": "experience", "intent": "answered", "final_score": 1.0, "breakdown": []},
        {"question_id": "q2", "category": "salary", "intent": "answered", "final_score": 0.0, "breakdown": []},
    ]
    importance = {"q1": 0.5}  # q2 missing entirely
    result = aggregate_screening_score(results, importance)
    assert result["final_screening_score"] == 1.0  # q1 gets 100% of the real weight


# ---------- score_screening_session: end to end against real repo data ----------

def test_full_session_against_real_financial_analyst_question_bank():
    import json
    jd = json.load(open("data/screening_questions/financial_analyst_questions.json"))
    canonical_skills = ["Excel", "Power BI", "SAP FICO"]

    answers_text = {
        "financial_analyst_introduction_01": "I'm a financial analyst with about seven years of experience",
        "financial_analyst_education_01": "I did my MBA in Finance from Delhi University",
        "financial_analyst_education_02": "not really",
        "financial_analyst_experience_01": "seven years",
        "financial_analyst_experience_02": "worked as a financial analyst for six years at a consulting firm",
        "financial_analyst_skills_01": "excel and power bi, and also SAP FICO a bit",
        "financial_analyst_skills_02": "I really love hiking and photography on weekends",
        "financial_analyst_location_01": "yes I'm based in Mumbai",
        "financial_analyst_salary_01": "around 15 lakhs per annum",
        "financial_analyst_notice_period_01": "",
    }

    categories_by_question = {}
    scoring_importance_by_question = {}
    semantic_answers = []
    for q in jd["questions"]:
        categories_by_question[q["id"]] = q["category"]
        scoring_importance_by_question[q["id"]] = q["scoring_importance"]
        record = process_transcript(
            transcript_id=f"t_{q['id']}", candidate_id="karthik_subramaniam.docx",
            job_id="financial_analyst", question_id=q["id"],
            raw_text=answers_text[q["id"]], expected_answer_type=q["expected_answer_type"],
            canonical_skills=canonical_skills if q["expected_answer_type"] == "list" else None,
        )
        semantic_answers.append(build_semantic_answer(record, q["category"], canonical_skills=canonical_skills))

    cross_check = load_resume_cross_check("karthik_subramaniam.docx")
    assert cross_check["resume_experience_months"] == 88
    assert "Excel" in cross_check["resume_skills"]

    result = score_screening_session(
        semantic_answers, categories_by_question, scoring_importance_by_question,
        resume_skills=cross_check["resume_skills"],
        resume_experience_months=cross_check["resume_experience_months"],
    )
    assert result["questions_scored"] == 10
    assert 0.0 <= result["final_screening_score"] <= 1.0
    # Matches hand-verified expectation from build-time verification.
    assert result["final_screening_score"] == 0.8388


def test_load_resume_cross_check_returns_none_for_unknown_candidate():
    result = load_resume_cross_check("nobody_real.docx")
    assert result["resume_skills"] is None
    assert result["resume_experience_months"] is None


# ---------- explainable output ----------

def test_explain_question_score_mentions_each_component():
    answer = _answer("seven years", "number", "experience")
    result = score_answer(answer, "experience", resume_experience_months=88)
    lines = explain_question_score(result)
    joined = "\n".join(lines)
    assert "clarity" in joined
    assert "relevance" in joined
    assert "completeness" in joined
    assert "consistency" in joined
    assert "Question score:" in joined


def test_explain_screening_score_lists_every_question():
    results = [
        {"question_id": "q1", "category": "experience", "intent": "answered", "final_score": 1.0, "breakdown": []},
    ]
    aggregate = aggregate_screening_score(results, {"q1": 1.0})
    lines = explain_screening_score(aggregate)
    assert any("Final screening score" in line for line in lines)
    assert any("q1" in line for line in lines)