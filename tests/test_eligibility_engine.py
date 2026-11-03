import json
from pathlib import Path

from eligibility_engine.eligibility_rules import build_rules_for_jd
from eligibility_engine.eligibility_engine import evaluate_candidate
from eligibility_engine.eligibility_tagger import evaluate_jd, evaluate_all_jds
from ranking_engine.shortlisting import SHORTLIST_THRESHOLD, REVIEW_THRESHOLD


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------- eligibility_rules ----------

def test_build_rules_pulls_mandatory_skills_and_experience_from_jd():
    jd_record = {
        "required_skills": [
            {"name": "React", "mandatory": True},
            {"name": "GraphQL", "mandatory": False},
        ],
        "experience_required": {"min_years": 3, "max_years": None},
    }
    rules = build_rules_for_jd(jd_record, "sde_ii")
    assert rules["mandatory_skills"] == ["React"]
    assert rules["experience_range"] == {"min_years": 3, "max_years": None}


def test_build_rules_falls_back_to_shortlist_threshold_when_no_override():
    rules = build_rules_for_jd({"required_skills": []}, "sde_ii")
    assert rules["min_score"] == SHORTLIST_THRESHOLD


def test_build_rules_honors_recruiter_override():
    rules = build_rules_for_jd({"required_skills": []}, "sde_ii", min_score=0.5)
    assert rules["min_score"] == 0.5


def test_build_rules_marks_location_as_not_evaluated():
    rules = build_rules_for_jd({"required_skills": []}, "sde_ii")
    assert rules["location"]["evaluated"] is False
    assert "reason" in rules["location"]


# ---------- eligibility_engine ----------

def test_missing_mandatory_skill_rejects_regardless_of_score():
    rules = build_rules_for_jd({"required_skills": [{"name": "React", "mandatory": True}]}, "sde_ii")
    result = evaluate_candidate(
        "alice.docx", 0.9, {"skills": []}, {"total_experience_months": 100}, rules,
    )
    assert result["status"] == "Rejected"
    assert "React" in result["checks"]["mandatory_skills"]["missing"]


def test_at_least_half_of_mandatory_skills_matched_is_enough_to_pass():
    # Real-data finding: requiring every mandatory skill by exact name gave 0%
    # pass on most roles, because the Day 9 skill dictionary doesn't cover every
    # tool name (Zendesk, Salesforce, SAP FICO, ...) even when a candidate has
    # it. At least half keeps this a real rule without that false-veto effect.
    rules = build_rules_for_jd(
        {"required_skills": [{"name": "Excel", "mandatory": True}, {"name": "SAP FICO", "mandatory": True}]},
        "financial_analyst",
    )
    result = evaluate_candidate(
        "alice.docx", 0.9, {"skills": [{"skill": "Excel"}]}, {"total_experience_months": 100}, rules,
    )
    assert result["checks"]["mandatory_skills"]["passed"] is True
    assert result["checks"]["mandatory_skills"]["missing"] == ["SAP FICO"]


def test_less_than_half_of_mandatory_skills_matched_still_rejects():
    rules = build_rules_for_jd(
        {"required_skills": [
            {"name": "Excel", "mandatory": True},
            {"name": "SAP FICO", "mandatory": True},
            {"name": "Power BI", "mandatory": True},
        ]},
        "financial_analyst",
    )
    result = evaluate_candidate(
        "alice.docx", 0.9, {"skills": [{"skill": "Excel"}]}, {"total_experience_months": 100}, rules,
    )
    assert result["checks"]["mandatory_skills"]["passed"] is False


def test_experience_outside_range_rejects_regardless_of_score():
    rules = build_rules_for_jd({"required_skills": [], "experience_required": {"min_years": 5, "max_years": None}}, "sde_ii")
    result = evaluate_candidate("alice.docx", 0.9, {"skills": []}, {"total_experience_months": 12}, rules)
    assert result["status"] == "Rejected"
    assert result["checks"]["experience"]["passed"] is False


def test_passes_hard_rules_and_meets_score_cutoff_is_eligible():
    rules = build_rules_for_jd({"required_skills": [{"name": "React", "mandatory": True}]}, "sde_ii")
    result = evaluate_candidate(
        "alice.docx", 0.5, {"skills": [{"skill": "React"}]}, {"total_experience_months": 60}, rules,
    )
    assert result["status"] == "Eligible"


def test_passes_hard_rules_but_below_cutoff_is_review_not_rejected():
    rules = build_rules_for_jd({"required_skills": []}, "sde_ii")
    result = evaluate_candidate("alice.docx", 0.05, {"skills": []}, {"total_experience_months": 0}, rules)
    assert REVIEW_THRESHOLD <= result["final_score"] < rules["min_score"]
    assert result["status"] == "Review"


def test_score_below_review_threshold_with_no_hard_rule_violation_is_rejected():
    rules = build_rules_for_jd({"required_skills": []}, "sde_ii")
    result = evaluate_candidate("alice.docx", 0.0, {"skills": []}, {"total_experience_months": 0}, rules)
    assert result["status"] == "Rejected"


def test_jd_with_no_mandatory_skills_cannot_fail_the_skills_check():
    rules = build_rules_for_jd({"required_skills": [{"name": "GraphQL", "mandatory": False}]}, "sde_ii")
    result = evaluate_candidate("alice.docx", 0.5, {"skills": []}, {"total_experience_months": 60}, rules)
    assert result["checks"]["mandatory_skills"]["passed"] is True


def test_jd_with_no_experience_requirement_cannot_fail_the_experience_check():
    rules = build_rules_for_jd({"required_skills": []}, "sde_ii")
    result = evaluate_candidate("alice.docx", 0.5, {"skills": []}, {"total_experience_months": 0}, rules)
    assert result["checks"]["experience"]["passed"] is True


def test_location_check_is_always_reported_as_not_evaluated():
    rules = build_rules_for_jd({"required_skills": []}, "sde_ii")
    result = evaluate_candidate("alice.docx", 0.5, {"skills": []}, {"total_experience_months": 0}, rules)
    assert result["checks"]["location"]["evaluated"] is False


# ---------- eligibility_tagger ----------

def test_evaluate_jd_writes_one_file_with_rules_and_candidates(tmp_path):
    scores_dir = tmp_path / "scores"
    scores_dir.mkdir()
    _write_json(scores_dir / "alice_docx_scores.json", {
        "resume": "alice.docx",
        "scores": [{"jd_file": "sde_ii", "final_score": 0.5, "breakdown": []}],
    })
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _write_json(skills_dir / "alice_docx_skills.json", {"skills": [{"skill": "React"}]})
    experience_dir = tmp_path / "experience"
    experience_dir.mkdir()
    _write_json(experience_dir / "alice_docx_experience.json", {"total_experience_months": 60})
    jds_dir = tmp_path / "jds"
    jds_dir.mkdir()
    _write_json(jds_dir / "sde_ii.json", {"required_skills": [{"name": "React", "mandatory": True}]})
    output_dir = tmp_path / "out"

    results = evaluate_jd(str(scores_dir), str(skills_dir), str(experience_dir), str(jds_dir), "sde_ii", str(output_dir))

    assert results[0]["status"] == "Eligible"
    saved = json.loads((output_dir / "sde_ii_eligibility.json").read_text(encoding="utf-8"))
    assert saved["jd_file"] == "sde_ii"
    assert saved["candidates"][0]["resume"] == "alice.docx"
    assert "rules" in saved


def test_candidate_with_no_score_for_this_jd_is_skipped(tmp_path):
    scores_dir = tmp_path / "scores"
    scores_dir.mkdir()
    _write_json(scores_dir / "alice_docx_scores.json", {
        "resume": "alice.docx", "scores": [{"jd_file": "other_jd", "final_score": 0.5, "breakdown": []}],
    })
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    experience_dir = tmp_path / "experience"
    experience_dir.mkdir()
    jds_dir = tmp_path / "jds"
    jds_dir.mkdir()
    _write_json(jds_dir / "sde_ii.json", {"required_skills": []})
    output_dir = tmp_path / "out"

    results = evaluate_jd(str(scores_dir), str(skills_dir), str(experience_dir), str(jds_dir), "sde_ii", str(output_dir))

    assert results == []


def test_evaluate_all_jds_writes_one_file_per_jd(tmp_path):
    scores_dir = tmp_path / "scores"
    scores_dir.mkdir()
    _write_json(scores_dir / "alice_docx_scores.json", {
        "resume": "alice.docx",
        "scores": [{"jd_file": "sde_ii", "final_score": 0.5, "breakdown": []}, {"jd_file": "hr", "final_score": 0.2, "breakdown": []}],
    })
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    experience_dir = tmp_path / "experience"
    experience_dir.mkdir()
    jds_dir = tmp_path / "jds"
    jds_dir.mkdir()
    _write_json(jds_dir / "sde_ii.json", {"required_skills": []})
    _write_json(jds_dir / "hr.json", {"required_skills": []})
    output_dir = tmp_path / "out"

    count = evaluate_all_jds(str(scores_dir), str(skills_dir), str(experience_dir), str(jds_dir), str(output_dir))

    assert count == 2
    assert (output_dir / "sde_ii_eligibility.json").exists()
    assert (output_dir / "hr_eligibility.json").exists()