import json

from scoring_engine.score_components import (
    skill_match_score,
    experience_relevance_score,
    education_alignment_score,
    semantic_similarity_score,
)
from scoring_engine.weight_profiles import WEIGHT_PROFILES, get_weight_profile
from scoring_engine.scoring_engine import compute_candidate_score, explain_score
from scoring_engine.candidate_score_generator import score_all_resumes


# ---------- score_components ----------

def test_skill_match_counts_mandatory_fully_and_optional_half():
    skill_profile = {"skills": [{"skill": "Python"}, {"skill": "SQL"}]}
    jd = {"required_skills": [
        {"name": "Python", "mandatory": True},
        {"name": "Java", "mandatory": True},
        {"name": "SQL", "mandatory": False},
    ]}
    # matched_weight = 1 (python) + 0.5 (sql) = 1.5; total_weight = 1+1+0.5 = 2.5
    assert skill_match_score(skill_profile, jd) == round(1.5 / 2.5, 4)


def test_skill_match_is_none_when_jd_has_no_required_skills():
    assert skill_match_score({"skills": []}, {"required_skills": []}) is None


def test_experience_relevance_is_none_when_no_jobs():
    assert experience_relevance_score({"jobs": []}, {"title": "Software Engineer"}, {"skills": []}) is None


def test_education_alignment_is_none_when_no_education_entries():
    assert education_alignment_score({"education": []}, {"title": "Marketing Manager"}) is None


def test_education_alignment_scores_real_overlap():
    education_record = {"education": [{"field_of_study": "Marketing"}]}
    jd = {"title": "Marketing Manager"}
    assert education_alignment_score(education_record, jd) == 0.5


def test_semantic_similarity_looks_up_the_right_jd_pair():
    semantic_record = {"matches": [
        {"jd_file": "sde_ii", "overall_similarity": 0.3},
        {"jd_file": "hr_manager", "overall_similarity": 0.1},
    ]}
    assert semantic_similarity_score(semantic_record, "hr_manager") == 0.1


def test_semantic_similarity_is_none_for_an_unprecomputed_pair():
    semantic_record = {"matches": [{"jd_file": "sde_ii", "overall_similarity": 0.3}]}
    assert semantic_similarity_score(semantic_record, "unknown_jd") is None


# ---------- weight_profiles ----------

def test_every_weight_profile_sums_to_one():
    for name, weights in WEIGHT_PROFILES.items():
        assert round(sum(weights.values()), 4) == 1.0


def test_unknown_jd_falls_back_to_default_profile():
    assert get_weight_profile("some_jd_never_seen_before") == WEIGHT_PROFILES["default"]


# ---------- scoring_engine: missing-data redistribution ----------

def test_missing_components_are_excluded_not_zeroed():
    # Only skill_match and semantic_similarity are available — the other two must
    # be marked unavailable and their weight redistributed, not silently scored 0.
    skills = {"skills": [{"skill": "Python"}]}
    experience = {"jobs": []}
    education = {"education": []}
    semantic = {"matches": [{"jd_file": "sde_ii", "overall_similarity": 0.5}]}
    jd = {"title": "Software Engineer", "required_skills": [{"name": "Python", "mandatory": True}]}

    result = compute_candidate_score(skills, experience, education, semantic, jd, "sde_ii")
    breakdown_by_name = {b["component"]: b for b in result["breakdown"]}

    assert breakdown_by_name["experience_relevance"]["available"] is False
    assert breakdown_by_name["education_alignment"]["available"] is False
    assert breakdown_by_name["skill_match"]["available"] is True
    assert breakdown_by_name["semantic_similarity"]["available"] is True


def test_available_components_weights_sum_to_one_after_redistribution():
    skills = {"skills": []}
    experience = {"jobs": []}
    education = {"education": []}
    semantic = {"matches": [{"jd_file": "sde_ii", "overall_similarity": 0.2}]}
    jd = {"title": "Software Engineer", "required_skills": [{"name": "Python", "mandatory": True}]}

    result = compute_candidate_score(skills, experience, education, semantic, jd, "sde_ii")
    total_normalized_weight = sum(b["normalized_weight"] for b in result["breakdown"] if b["available"])
    assert round(total_normalized_weight, 2) == 1.0


def test_final_score_matches_hand_calculated_weighted_sum():
    # Rohan vs sde_ii — all four components real and available, verified by hand:
    # 0.2*0.40 + 0.625*0.25 + 0.0*0.10 + 0.0976*0.25 = 0.2606
    skills = json.load(open('data/skills/rohan_mehta_docx_skills.json', encoding='utf-8'))
    experience = json.load(open('data/experience/rohan_mehta_docx_experience.json', encoding='utf-8'))
    education = json.load(open('data/education/rohan_mehta_docx_education.json', encoding='utf-8'))
    semantic = json.load(open('data/semantic_matches/rohan_mehta_docx_matches.json', encoding='utf-8'))
    jd = json.load(open('data/parsed_jds/sde_ii.json', encoding='utf-8'))

    result = compute_candidate_score(skills, experience, education, semantic, jd, 'sde_ii')
    assert result["final_score"] == 0.2606


def test_all_missing_components_gives_an_honest_zero_not_a_crash():
    empty_skills = {"skills": []}
    empty_experience = {"jobs": []}
    empty_education = {"education": []}
    empty_semantic = {"matches": []}
    jd = {"title": "Software Engineer", "required_skills": [{"name": "Python", "mandatory": True}]}

    result = compute_candidate_score(empty_skills, empty_experience, empty_education, empty_semantic, jd, "sde_ii")
    assert result["final_score"] == 0.0


def test_explain_score_produces_one_line_per_component_plus_final():
    jd = {"title": "Software Engineer", "required_skills": [{"name": "Python", "mandatory": True}]}
    result = compute_candidate_score({"skills": []}, {"jobs": []}, {"education": []}, {"matches": []}, jd, "sde_ii")
    lines = explain_score(result)
    assert len(lines) == 5  # 4 components + final score line
    assert "Final score" in lines[-1]


# ---------- candidate_score_generator ----------

def test_score_all_resumes_saves_one_file_per_resume(tmp_path):
    segmented_dir = tmp_path / "segmented"
    skills_dir = tmp_path / "skills"
    experience_dir = tmp_path / "experience"
    education_dir = tmp_path / "education"
    semantic_dir = tmp_path / "semantic"
    jds_dir = tmp_path / "jds"
    output_dir = tmp_path / "scores"
    for d in [segmented_dir, skills_dir, experience_dir, education_dir, semantic_dir, jds_dir]:
        d.mkdir()

    (segmented_dir / "alice_docx_sections.json").write_text(json.dumps({"source_file": "alice.docx"}), encoding="utf-8")
    (skills_dir / "alice_docx_skills.json").write_text(json.dumps({"source_file": "alice.docx", "skills": [{"skill": "Python"}]}), encoding="utf-8")
    (experience_dir / "alice_docx_experience.json").write_text(json.dumps({"jobs": []}), encoding="utf-8")
    (education_dir / "alice_docx_education.json").write_text(json.dumps({"education": []}), encoding="utf-8")
    (semantic_dir / "alice_docx_matches.json").write_text(json.dumps({"matches": [{"jd_file": "sde", "overall_similarity": 0.3}]}), encoding="utf-8")
    (jds_dir / "sde.json").write_text(json.dumps({"title": "Software Engineer", "required_skills": [{"name": "Python", "mandatory": True}]}), encoding="utf-8")

    count = score_all_resumes(
        str(segmented_dir), str(skills_dir), str(experience_dir),
        str(education_dir), str(semantic_dir), str(jds_dir), str(output_dir)
    )

    assert count == 1
    saved = json.loads((output_dir / "alice_docx_scores.json").read_text(encoding="utf-8"))
    assert saved["scores"][0]["jd_file"] == "sde"