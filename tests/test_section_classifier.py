"""
Automated tests for the resume section classifier.
"""

import json
from pathlib import Path

from parsers.section_classifier import classify_sections
from parsers.section_tagger import tag_folder
from parsers.text_cleaner import clean_text

EXTRACTED_DIR = Path(__file__).resolve().parent.parent / "data" / "extracted"


def extracted_text(name: str) -> str:
    return json.loads((EXTRACTED_DIR / name).read_text(encoding="utf-8"))["text"]


# ---------- heading-based (rule-based) path ----------

def test_standard_resume_splits_into_five_sections():
    result = classify_sections(extracted_text("rohan_mehta_docx.json"))
    assert result["method"] == "heading"
    assert set(result["sections"]) == {"HEADER", "SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION", "CERTIFICATIONS"}


def test_projects_section_is_detected():
    result = classify_sections(extracted_text("ananya_rao_docx.json"))
    assert result["method"] == "heading"
    assert "PROJECTS" in result["sections"]
    assert len(result["sections"]["PROJECTS"]) == 6


def test_resume_missing_a_section_does_not_invent_it():
    # Ishaan's real resume has no SUMMARY at all - it should stay absent, not guessed.
    result = classify_sections(extracted_text("ishaan_kapoor_photo_docx.json"))
    assert "SUMMARY" not in result["sections"]


# ---------- heuristic fallback path ----------

def test_no_headings_resume_falls_back_to_heuristic():
    result = classify_sections(extracted_text("no_headings_vikram_docx.json"))
    assert result["method"] == "heuristic"


def test_heuristic_finds_skills_from_a_comma_list():
    result = classify_sections(extracted_text("no_headings_vikram_docx.json"))
    assert any("SAP ERP" in line for line in result["sections"]["SKILLS"])


def test_heuristic_finds_experience_from_a_date_range():
    result = classify_sections(extracted_text("no_headings_vikram_docx.json"))
    assert len(result["sections"]["EXPERIENCE"]) == 2


def test_heuristic_finds_education_including_uncommon_degrees():
    # Regression test: "B.Des ... National Institute of Design" was missed
    # until the degree keyword list was widened to include b.des/institute.
    result = classify_sections(extracted_text("no_headings_meena_docx.json"))
    assert any("B.Des" in line for line in result["sections"]["EDUCATION"])


def test_bullets_inherit_the_job_entry_above_them():
    # Regression test: bullet lines under a job entry used to have no date
    # or keyword of their own and fell into UNCLASSIFIED.
    result = classify_sections(extracted_text("no_headings_meena_docx.json"))
    assert len(result["sections"]["EXPERIENCE"]) == 7  # 2 job lines + 5 bullets


def test_summary_without_a_heading_is_left_unclassified_not_guessed():
    result = classify_sections(extracted_text("no_headings_vikram_docx.json"))
    assert len(result["sections"]["UNCLASSIFIED"]) == 1


# ---------- scanned / no-text resumes ----------

def test_resume_with_no_text_is_skipped_not_crashed():
    from parsers.section_tagger import tag_resume
    result = tag_resume({"source_file": "zoya_khan_scanned.pdf", "text": ""})
    assert result["method"] == "skipped"
    assert result["sections"] == {}


# ---------- end to end ----------

def test_tag_folder_saves_one_json_per_resume(tmp_path):
    results = tag_folder(str(EXTRACTED_DIR), str(tmp_path))
    assert len(results) == len(list(EXTRACTED_DIR.glob("*.json")))
    assert len(list(tmp_path.glob("*_sections.json"))) == len(results)

    saved = json.loads((tmp_path / "ananya_rao_docx_sections.json").read_text(encoding="utf-8"))
    assert saved["method"] == "heading"
    assert "PROJECTS" in saved["sections"]