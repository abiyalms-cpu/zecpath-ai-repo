"""
Tests for the Day 10 experience parsing and relevance engine: date-range
extraction from messy real-world header formats, total experience with
overlap merging, gap/overlap detection, and role/skill relevance scoring.
"""

from datetime import datetime

from experience_engine.experience_parser import parse_experience_line, parse_experience_section
from experience_engine.experience_calculator import (
    total_experience_months,
    format_duration,
    find_gaps_and_overlaps,
)
from experience_engine.relevance_scorer import role_similarity, score_candidate_relevance
from experience_engine.experience_tagger import build_experience_record, tag_folder

REF_DATE = datetime(2026, 10, 5)


def test_comma_separated_header_is_parsed():
    job = parse_experience_line("Frontend Developer, Brightloop Software — Jan 2024 – Present")
    assert job["title"] == "Frontend Developer"
    assert job["company"] == "Brightloop Software"
    assert job["is_current"] is True
    assert job["start_month"] == 1 and job["start_year"] == 2024


def test_at_separated_header_with_location_is_parsed():
    # Regression case: "Title at Company, Location, from Date to Date."
    # the location after the comma must not end up inside the company name.
    job = parse_experience_line(
        "Operations Lead at Swiftline Logistics, Bengaluru, from March 2021 to present."
    )
    assert job["title"] == "Operations Lead"
    assert job["company"] == "Swiftline Logistics"
    assert job["is_current"] is True


def test_bullet_line_with_no_date_is_skipped():
    assert parse_experience_line("- Built and maintained 4 internal dashboards") is None


def test_parse_experience_section_only_returns_dated_lines():
    lines = [
        "Frontend Developer, Brightloop Software — Jan 2024 – Present",
        "- Built and maintained 4 internal dashboards",
        "- Migrated a legacy jQuery UI to React",
    ]
    jobs = parse_experience_section(lines)
    assert len(jobs) == 1


def test_total_experience_counts_two_back_to_back_jobs_without_double_counting():
    jobs = [
        {"start_year": 2021, "start_month": 7, "end_year": 2023, "end_month": 5, "is_current": False},
        {"start_year": 2023, "start_month": 6, "end_year": None, "end_month": None, "is_current": True},
    ]
    months = total_experience_months(jobs, reference_date=REF_DATE)
    assert months == 64  # Jul 2021 -> Oct 2026 inclusive, no overlap to merge


def test_total_experience_merges_overlapping_jobs_instead_of_double_counting():
    jobs = [
        {"start_year": 2020, "start_month": 1, "end_year": 2021, "end_month": 6, "is_current": False},
        {"start_year": 2021, "start_month": 1, "end_year": 2021, "end_month": 12, "is_current": False},
    ]
    months = total_experience_months(jobs, reference_date=REF_DATE)
    assert months == 24  # Jan 2020 -> Dec 2021, overlap not counted twice


def test_back_to_back_jobs_are_not_flagged_as_a_gap():
    jobs = [
        {"raw_line": "A", "start_year": 2021, "start_month": 7, "end_year": 2023, "end_month": 5, "is_current": False},
        {"raw_line": "B", "start_year": 2023, "start_month": 6, "end_year": None, "end_month": None, "is_current": True},
    ]
    gaps, overlaps = find_gaps_and_overlaps(jobs, reference_date=REF_DATE)
    assert gaps == []
    assert overlaps == []


def test_real_gap_between_jobs_is_detected():
    jobs = [
        {"raw_line": "A", "start_year": 2019, "start_month": 1, "end_year": 2019, "end_month": 6, "is_current": False},
        {"raw_line": "B", "start_year": 2020, "start_month": 1, "end_year": 2020, "end_month": 12, "is_current": False},
    ]
    gaps, overlaps = find_gaps_and_overlaps(jobs, reference_date=REF_DATE)
    assert len(gaps) == 1
    assert gaps[0]["gap_months"] == 6
    assert overlaps == []


def test_real_overlap_between_jobs_is_detected():
    jobs = [
        {"raw_line": "A", "start_year": 2020, "start_month": 1, "end_year": 2021, "end_month": 6, "is_current": False},
        {"raw_line": "B", "start_year": 2021, "start_month": 1, "end_year": 2021, "end_month": 12, "is_current": False},
    ]
    gaps, overlaps = find_gaps_and_overlaps(jobs, reference_date=REF_DATE)
    assert overlaps[0]["overlap_months"] == 6
    assert gaps == []


def test_role_similarity_recognises_known_synonyms_as_an_exact_match():
    assert role_similarity("Software Engineer", "Software Developer") == 1.0


def test_role_similarity_falls_back_to_word_overlap_for_unrelated_titles():
    score = role_similarity("Frontend Developer", "Software Engineer")
    assert 0.0 <= score < 1.0


def test_role_similarity_is_zero_for_empty_input():
    assert role_similarity(None, "Software Engineer") == 0.0
    assert role_similarity("Developer", None) == 0.0


def test_relevance_combines_role_and_skill_scores_when_skill_profile_given():
    jobs = [{"title": "Software Engineer", "company": "X"}]
    jd = {"title": "Software Developer", "required_skills": [
        {"name": "Python", "mandatory": True},
        {"name": "SQL", "mandatory": True},
    ]}
    skill_profile = [{"skill": "Python"}]
    result = score_candidate_relevance(jobs, jd, skill_profile=skill_profile)
    assert result["role_relevance"] == 1.0
    assert result["skill_overlap"] == 0.5
    assert result["overall_relevance"] == 0.75


def test_relevance_uses_role_score_only_when_no_skill_profile_given():
    jobs = [{"title": "Software Engineer", "company": "X"}]
    jd = {"title": "Software Developer", "required_skills": []}
    result = score_candidate_relevance(jobs, jd)
    assert result["skill_overlap"] is None
    assert result["overall_relevance"] == result["role_relevance"] == 1.0


def test_resume_with_no_text_gets_an_honest_empty_record():
    record = build_experience_record({"source_file": "blank.pdf", "method": "skipped", "sections": {}})
    assert record["jobs"] == []
    assert record["total_experience_months"] == 0


def test_tag_folder_saves_one_json_per_resume(tmp_path):
    import json

    segmented_dir = tmp_path / "segmented"
    output_dir = tmp_path / "experience"
    segmented_dir.mkdir()

    sample = {
        "source_file": "sample.docx",
        "method": "heading",
        "sections": {"EXPERIENCE": ["Developer, Acme Corp — Jan 2020 – Present"]},
    }
    with open(segmented_dir / "sample_sections.json", "w", encoding="utf-8") as f:
        json.dump(sample, f)

    count = tag_folder(str(segmented_dir), str(output_dir))

    assert count == 1
    out_file = output_dir / "sample_experience.json"
    assert out_file.exists()