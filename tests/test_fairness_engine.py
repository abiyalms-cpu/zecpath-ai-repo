import json

from fairness_engine.bias_analysis import (
    check_header_independence,
    format_bias_check,
    keyword_dependence_check,
)


# ---------- header independence ----------

def test_scoring_components_do_not_reference_header():
    # Real check against the actual scoring_engine source, not a synthetic stand-in —
    # this is a structural guarantee, so it's tested against the real code.
    result = check_header_independence()
    assert result["component_source_references_header"] is False
    assert result["verdict"].startswith("PASS")


# ---------- format bias check ----------

def _write_segmented(segmented_dir, stem, method):
    record = {"source_file": f"{stem}.docx", "method": method, "sections": {}}
    (segmented_dir / f"{stem}_sections.json").write_text(json.dumps(record), encoding="utf-8")


def _write_skills(skills_dir, stem, skills):
    (skills_dir / f"{stem}_skills.json").write_text(json.dumps({"skills": skills}), encoding="utf-8")


def _write_experience(experience_dir, stem, jobs):
    (experience_dir / f"{stem}_experience.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")


def test_skipped_resumes_are_excluded_from_format_comparison(tmp_path):
    segmented_dir = tmp_path / "segmented"
    skills_dir = tmp_path / "skills"
    experience_dir = tmp_path / "experience"
    segmented_dir.mkdir()
    skills_dir.mkdir()
    experience_dir.mkdir()

    _write_segmented(segmented_dir, "scanned_resume", "skipped")

    result = format_bias_check(str(segmented_dir), str(skills_dir), str(experience_dir))

    assert result["heading_method_count"] == 0
    assert result["heuristic_method_count"] == 0


def test_averages_computed_correctly_per_method(tmp_path):
    segmented_dir = tmp_path / "segmented"
    skills_dir = tmp_path / "skills"
    experience_dir = tmp_path / "experience"
    segmented_dir.mkdir()
    skills_dir.mkdir()
    experience_dir.mkdir()

    _write_segmented(segmented_dir, "candidate_a", "heading")
    _write_skills(skills_dir, "candidate_a", ["Python", "SQL"])
    _write_experience(experience_dir, "candidate_a", [{"title": "Dev"}])

    _write_segmented(segmented_dir, "candidate_b", "heading")
    _write_skills(skills_dir, "candidate_b", ["Python", "SQL", "React", "Git"])
    _write_experience(experience_dir, "candidate_b", [{"title": "Dev"}, {"title": "Lead"}])

    _write_segmented(segmented_dir, "candidate_c", "heuristic")
    _write_skills(skills_dir, "candidate_c", ["Excel"])
    _write_experience(experience_dir, "candidate_c", [])

    result = format_bias_check(str(segmented_dir), str(skills_dir), str(experience_dir))

    assert result["heading_method_count"] == 2
    assert result["heuristic_method_count"] == 1
    assert result["avg_skills_found_heading"] == 3.0
    assert result["avg_jobs_parsed_heading"] == 1.5
    assert result["avg_skills_found_heuristic"] == 1.0
    assert result["avg_jobs_parsed_heuristic"] == 0.0


def test_missing_skill_or_experience_file_counts_as_zero(tmp_path):
    segmented_dir = tmp_path / "segmented"
    skills_dir = tmp_path / "skills"
    experience_dir = tmp_path / "experience"
    segmented_dir.mkdir()
    skills_dir.mkdir()
    experience_dir.mkdir()

    _write_segmented(segmented_dir, "no_downstream_files", "heading")
    # No matching _skills.json or _experience.json written for this stem

    result = format_bias_check(str(segmented_dir), str(skills_dir), str(experience_dir))

    assert result["avg_skills_found_heading"] == 0.0
    assert result["avg_jobs_parsed_heading"] == 0.0


# ---------- keyword dependence check ----------

def _write_scores(candidate_scores_dir, resume, jd_file, skill_match, final_score):
    record = {
        "resume": resume,
        "scores": [
            {
                "jd_file": jd_file,
                "final_score": final_score,
                "breakdown": [
                    {"component": "skill_match", "raw_score": skill_match},
                ],
            }
        ],
    }
    (candidate_scores_dir / f"{resume}_scores.json").write_text(json.dumps(record), encoding="utf-8")


def test_identifies_promoted_and_dropped_candidates(tmp_path):
    candidate_scores_dir = tmp_path / "candidate_scores"
    candidate_scores_dir.mkdir()

    # High skill-match, but blending pulls it out of the top spot
    _write_scores(candidate_scores_dir, "keyword_stuffed.docx", "sde_ii", skill_match=0.9, final_score=0.1)
    # Low skill-match, but strong on other signals so blending promotes it
    _write_scores(candidate_scores_dir, "real_fit.docx", "sde_ii", skill_match=0.1, final_score=0.9)

    result = keyword_dependence_check(str(candidate_scores_dir), "sde_ii", top_n=1)

    assert result["skill_match_only_top"] == ["keyword_stuffed.docx"]
    assert result["blended_top"] == ["real_fit.docx"]
    assert result["promoted_by_blending"] == ["real_fit.docx"]
    assert result["dropped_by_blending"] == ["keyword_stuffed.docx"]


def test_returns_empty_when_jd_not_found_in_any_record(tmp_path):
    candidate_scores_dir = tmp_path / "candidate_scores"
    candidate_scores_dir.mkdir()
    _write_scores(candidate_scores_dir, "candidate_a.docx", "hr_manager", skill_match=0.5, final_score=0.5)

    result = keyword_dependence_check(str(candidate_scores_dir), "sde_ii", top_n=5)

    assert result["skill_match_only_top"] == []
    assert result["blended_top"] == []


def test_missing_skill_match_component_defaults_to_zero(tmp_path):
    candidate_scores_dir = tmp_path / "candidate_scores"
    candidate_scores_dir.mkdir()
    record = {
        "resume": "no_skill_component.docx",
        "scores": [
            {"jd_file": "sde_ii", "final_score": 0.3, "breakdown": []},
        ],
    }
    (candidate_scores_dir / "no_skill_component.docx_scores.json").write_text(
        json.dumps(record), encoding="utf-8"
    )

    result = keyword_dependence_check(str(candidate_scores_dir), "sde_ii", top_n=1)

    assert result["blended_top"] == ["no_skill_component.docx"]