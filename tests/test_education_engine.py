import json
from pathlib import Path

from education_engine.education_parser import (
    parse_education_line,
    parse_education_section,
    parse_certification_line,
    parse_certification_section,
)
from education_engine.certification_tagger import categorize_certification, tag_certifications
from education_engine.education_tagger import build_education_record, tag_folder
from education_engine.education_relevance import score_field_relevance, tag_certification_relevance


# ---------- education line parsing ----------

def test_parses_comma_separated_degree_field_institution_year():
    result = parse_education_line("B.Tech, Computer Science — Visvesvaraya Technological University (2021)")
    assert result["degree_normalized"] == "B.Tech"
    assert result["field_of_study"] == "Computer Science"
    assert result["institution"] == "Visvesvaraya Technological University"
    assert result["graduation_year"] == 2021


def test_parses_degree_with_no_comma_field_attached():
    result = parse_education_line("B.Sc Mathematics — Bharathiar University (2013)")
    assert result["degree_normalized"] == "B.Sc"
    assert result["field_of_study"] == "Mathematics"


def test_parses_degree_with_no_field_at_all():
    result = parse_education_line("B.Com — Loyola College, Chennai (2016)")
    assert result["degree_normalized"] == "B.Com"
    assert result["field_of_study"] is None
    assert result["institution"] == "Loyola College, Chennai"


def test_pipe_separated_three_part_line_does_not_leave_dangling_separator():
    # Regression: "A | B | 2020" used to leave institution as "B |"
    result = parse_education_line("B.Sc Statistics | Loyola College | 2020")
    assert result["institution"] == "Loyola College"
    assert result["graduation_year"] == 2020


def test_line_with_no_year_is_skipped_not_guessed():
    assert parse_education_line("B.Tech, Information Technology") is None


def test_two_column_split_entry_is_skipped_honestly():
    # Real case: nikhil_verma's two-column resume split one entry across two list lines
    assert parse_education_line("JNTU Hyderabad (2020)") is None


def test_prose_style_line_is_skipped_not_misparsed():
    # Real case: no_headings_meena's resume, written as a sentence not a structured line
    assert parse_education_line("B.Des in Interaction Design, National Institute of Design, 2019.") is None


def test_empty_or_missing_education_section_returns_empty_list():
    assert parse_education_section(None) == []
    assert parse_education_section([]) == []


# ---------- certification line parsing ----------

def test_parses_bulleted_certification_with_year():
    result = parse_certification_line("- AWS Certified Cloud Practitioner (2023)")
    assert result["certification_name"] == "AWS Certified Cloud Practitioner"
    assert result["year"] == 2023


def test_parses_certification_without_year():
    result = parse_certification_line("- Basic Life Support (BLS) Certified")
    assert result["certification_name"] == "Basic Life Support (BLS) Certified"
    assert result["year"] is None


def test_parses_certification_without_bullet_prefix():
    result = parse_certification_line("AWS Certified Developer (2023)")
    assert result["certification_name"] == "AWS Certified Developer"


# ---------- certification categorization ----------

def test_categorizes_known_certifications_correctly():
    assert categorize_certification("AWS Certified Cloud Practitioner") == "Technology"
    assert categorize_certification("Shrm-Cp") == "Business"
    assert categorize_certification("CFA Level I Cleared") == "Finance"
    assert categorize_certification("Basic Life Support (BLS) Certified") == "Healthcare"
    assert categorize_certification("Certified SolidWorks Associate (CSWA)") == "Engineering"
    assert categorize_certification("Google UX Design Certificate") == "Design"


def test_unknown_certification_is_honestly_uncategorized():
    assert categorize_certification("Zorblax Master Practitioner") == "Uncategorized"


def test_tag_certifications_attaches_category_to_each():
    parsed = parse_certification_section(["- AWS Certified Developer (2023)"])
    tagged = tag_certifications(parsed)
    assert tagged[0]["category"] == "Technology"


# ---------- combined record building ----------

def test_build_education_record_for_normal_resume():
    segmented_record = {
        "source_file": "test.docx",
        "method": "heading",
        "sections": {
            "EDUCATION": ["B.Tech, Computer Science — Test University (2021)"],
            "CERTIFICATIONS": ["- AWS Certified Developer (2023)"],
        },
    }
    record = build_education_record(segmented_record)
    assert len(record["education"]) == 1
    assert len(record["certifications"]) == 1
    assert record["certifications"][0]["category"] == "Technology"


def test_build_education_record_for_skipped_resume_is_honestly_empty():
    segmented_record = {"source_file": "scanned.pdf", "method": "skipped", "sections": {}}
    record = build_education_record(segmented_record)
    assert record["education"] == []
    assert record["certifications"] == []
    assert record["method"] == "skipped"


def test_tag_folder_saves_one_file_per_resume(tmp_path):
    segmented_dir = tmp_path / "segmented"
    output_dir = tmp_path / "education"
    segmented_dir.mkdir()

    record = {
        "source_file": "sample.docx",
        "method": "heading",
        "sections": {"EDUCATION": ["MBA, Marketing — Sample University (2020)"]},
    }
    (segmented_dir / "sample_sections.json").write_text(json.dumps(record), encoding="utf-8")

    count = tag_folder(str(segmented_dir), str(output_dir))

    assert count == 1
    saved = json.loads((output_dir / "sample_education.json").read_text(encoding="utf-8"))
    assert saved["education"][0]["degree_normalized"] == "MBA"


# ---------- education relevance ----------

def test_field_relevance_scores_overlapping_words():
    score = score_field_relevance([{"field_of_study": "Marketing"}], "Marketing Manager")
    assert score == 0.5


def test_field_relevance_is_zero_for_empty_input():
    assert score_field_relevance([], "Software Engineer") == 0.0
    assert score_field_relevance([{"field_of_study": "Marketing"}], "") == 0.0


def test_certification_relevance_flags_matching_category():
    certs = [{"certification_name": "AWS Certified Developer", "category": "Technology"}]
    tagged = tag_certification_relevance(certs, ["Technology"])
    assert tagged[0]["relevant"] is True


def test_certification_relevance_flags_non_matching_category_false():
    certs = [{"certification_name": "CFA Level I", "category": "Finance"}]
    tagged = tag_certification_relevance(certs, ["Technology"])
    assert tagged[0]["relevant"] is False