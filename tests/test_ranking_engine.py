import csv
import json
from pathlib import Path

from ranking_engine.ranking import rank_candidates_for_jd
from ranking_engine.shortlisting import classify_zone, apply_shortlisting, SHORTLIST_THRESHOLD, REVIEW_THRESHOLD
from ranking_engine.top_candidates import top_candidates_for_jd
from ranking_engine.recruiter_output import export_jd_csv, export_all_jds


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _fake_candidate_scores(tmp_path, entries):
    """entries: list of (resume_name, {jd_file: final_score})"""
    d = tmp_path / "scores"
    d.mkdir()
    for resume_name, jd_scores in entries:
        scores = [
            {"jd_file": jd_file, "final_score": score, "breakdown": [
                {"component": "skill_match", "raw_score": score},
                {"component": "experience_relevance", "raw_score": score},
                {"component": "education_alignment", "raw_score": score},
                {"component": "semantic_similarity", "raw_score": score},
            ]}
            for jd_file, score in jd_scores.items()
        ]
        _write_json(d / f"{resume_name.replace('.', '_')}_scores.json", {"resume": resume_name, "scores": scores})
    return d


# ---------- ranking ----------

def test_rank_candidates_sorts_descending_by_final_score(tmp_path):
    scores_dir = _fake_candidate_scores(tmp_path, [
        ("alice.docx", {"sde": 0.3}),
        ("bob.docx", {"sde": 0.8}),
        ("carol.docx", {"sde": 0.1}),
    ])
    ranked = rank_candidates_for_jd(str(scores_dir), "sde")
    assert [r["resume"] for r in ranked] == ["bob.docx", "alice.docx", "carol.docx"]


def test_rank_candidates_assigns_sequential_rank_numbers(tmp_path):
    scores_dir = _fake_candidate_scores(tmp_path, [("alice.docx", {"sde": 0.5}), ("bob.docx", {"sde": 0.9})])
    ranked = rank_candidates_for_jd(str(scores_dir), "sde")
    assert ranked[0]["rank"] == 1
    assert ranked[1]["rank"] == 2


def test_candidate_with_no_score_for_this_jd_is_skipped(tmp_path):
    scores_dir = _fake_candidate_scores(tmp_path, [("alice.docx", {"other_jd": 0.5})])
    ranked = rank_candidates_for_jd(str(scores_dir), "sde")
    assert ranked == []


# ---------- shortlisting ----------

def test_classify_zone_boundaries():
    assert classify_zone(0.15) == "shortlist"
    assert classify_zone(0.1499) == "review"
    assert classify_zone(0.03) == "review"
    assert classify_zone(0.0299) == "auto_reject"
    assert classify_zone(0.0) == "auto_reject"


def test_apply_shortlisting_tags_every_candidate():
    candidates = [{"resume": "a", "final_score": 0.2}, {"resume": "b", "final_score": 0.01}]
    zoned = apply_shortlisting(candidates)
    assert zoned[0]["zone"] == "shortlist"
    assert zoned[1]["zone"] == "auto_reject"


def test_shortlisting_does_not_remove_any_candidates():
    # A recruiter should see the full list with zones marked, not a filtered list.
    candidates = [{"resume": "a", "final_score": 0.0}]
    zoned = apply_shortlisting(candidates)
    assert len(zoned) == 1


# ---------- top_candidates ----------

def test_top_candidates_respects_top_n(tmp_path):
    scores_dir = _fake_candidate_scores(tmp_path, [
        ("a.docx", {"sde": 0.9}), ("b.docx", {"sde": 0.8}), ("c.docx", {"sde": 0.7}),
    ])
    top = top_candidates_for_jd(str(scores_dir), "sde", top_n=2)
    assert len(top) == 2
    assert top[0]["resume"] == "a.docx"


# ---------- recruiter_output (CSV) ----------

def test_export_jd_csv_includes_component_breakdown_columns(tmp_path):
    scores_dir = _fake_candidate_scores(tmp_path, [("alice.docx", {"sde": 0.6})])
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _write_json(skills_dir / "alice_docx_skills.json", {"skills": [{"skill": "Python"}]})
    jds_dir = tmp_path / "jds"
    jds_dir.mkdir()
    _write_json(jds_dir / "sde.json", {"title": "SDE", "required_skills": [{"name": "Python"}]})
    output_dir = tmp_path / "out"

    out_path = export_jd_csv(str(scores_dir), str(skills_dir), str(jds_dir), "sde", str(output_dir))

    rows = list(csv.DictReader(open(out_path, encoding="utf-8")))
    assert rows[0]["Candidate"] == "alice.docx"
    assert rows[0]["Matched Skills"] == "Python"
    assert "Skill Match" in rows[0]
    assert "Semantic Similarity" in rows[0]


def test_matched_skills_is_blank_not_crashed_when_no_overlap(tmp_path):
    # Regression: Divya Menon's real case — zero exact skill-name overlap (Day 9's
    # dictionary doesn't cover tool names like "Google Ads") must not blank-crash
    # the CSV, just leave that one column empty while the others stay populated.
    scores_dir = _fake_candidate_scores(tmp_path, [("alice.docx", {"marketing": 0.3})])
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _write_json(skills_dir / "alice_docx_skills.json", {"skills": [{"skill": "Digital Marketing"}]})
    jds_dir = tmp_path / "jds"
    jds_dir.mkdir()
    _write_json(jds_dir / "marketing.json", {"title": "Marketing", "required_skills": [{"name": "Google Ads"}]})
    output_dir = tmp_path / "out"

    out_path = export_jd_csv(str(scores_dir), str(skills_dir), str(jds_dir), "marketing", str(output_dir))

    rows = list(csv.DictReader(open(out_path, encoding="utf-8")))
    assert rows[0]["Matched Skills"] == ""
    assert rows[0]["Final Score"] == "0.3"


def test_export_all_jds_writes_one_csv_per_jd(tmp_path):
    scores_dir = _fake_candidate_scores(tmp_path, [("alice.docx", {"sde": 0.5, "hr": 0.2})])
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _write_json(skills_dir / "alice_docx_skills.json", {"skills": []})
    jds_dir = tmp_path / "jds"
    jds_dir.mkdir()
    _write_json(jds_dir / "sde.json", {"title": "SDE", "required_skills": []})
    _write_json(jds_dir / "hr.json", {"title": "HR", "required_skills": []})
    output_dir = tmp_path / "out"

    count = export_all_jds(str(scores_dir), str(skills_dir), str(jds_dir), str(output_dir))

    assert count == 2
    assert (output_dir / "sde_ranked.csv").exists()
    assert (output_dir / "hr_ranked.csv").exists()