"""
Automated tests for the JD parsing system.
"""

import json
from pathlib import Path

from parsers.jd_cleaner import clean_jd_text
from parsers.jd_extractor import (
    extract_department,
    extract_education,
    extract_employment_type,
    extract_experience,
    extract_location,
    extract_responsibilities,
    extract_role,
    extract_salary_range,
    extract_skills,
)
from parsers.jd_parser import parse_folder, parse_jd_text

JD_DIR = Path(__file__).resolve().parent.parent / "data" / "job_descriptions"


def read(name: str) -> str:
    return (JD_DIR / name).read_text(encoding="utf-8")


def cleaned(name: str) -> str:
    return clean_jd_text(read(name))


# ---------- cleaning ----------

def test_cleaner_normalizes_heading_variants():
    assert clean_jd_text("What You'll Need:\nsomething").startswith("REQUIREMENTS")


def test_cleaner_splits_inline_heading_from_content():
    result = clean_jd_text("Bonus: Google Ads certification")
    assert result == "NICE TO HAVE\n- Google Ads certification"


# ---------- role variation detection ----------

def test_two_worded_differently_are_the_same_role():
    assert extract_role(cleaned("software_developer.txt")) == extract_role(cleaned("sde_ii.txt")) == "Software Engineer"


def test_role_survives_word_boundary_fix():
    assert extract_role("Location: Mumbai, Maharashtra") is None


# ---------- location and department ----------

def test_location_from_label():
    assert extract_location(cleaned("hr_manager.txt")) == "Chennai, Tamil Nadu"


def test_location_from_title_line_when_no_label():
    assert extract_location(cleaned("digital_marketing.txt")) == "Hyderabad, Telangana"


def test_department_is_none_when_not_stated():
    assert extract_department(cleaned("hr_manager.txt")) is None


def test_department_from_label_when_present():
    assert extract_department(cleaned("financial_analyst.txt")) == "Finance"


# ---------- skill synonym detection and skill objects ----------

def test_skill_synonyms_map_to_one_canonical_object():
    skills = extract_skills(clean_jd_text("Experience with ReactJS and React required."))
    assert skills == [{"name": "React", "category": "technical", "mandatory": True}]


def test_java_is_not_falsely_found_inside_javascript():
    skills = extract_skills(clean_jd_text("Proficiency in JavaScript required."))
    names = [s["name"] for s in skills]
    assert "Java" not in names and "JavaScript" in names


def test_hris_is_not_falsely_found_inside_thrissur():
    skills = extract_skills(clean_jd_text("Location: Thrissur, Kerala"))
    assert not any(s["name"] == "HRIS" for s in skills)


def test_nice_to_have_skills_are_marked_not_mandatory():
    skills = extract_skills(cleaned("sde_ii.txt"))
    by_name = {s["name"]: s["mandatory"] for s in skills}
    assert by_name["React"] is True
    assert by_name["GraphQL"] is False


# ---------- experience extraction ----------

def test_plus_years_format():
    assert extract_experience("3+ years of experience") == {"min_years": 3, "max_years": None}


def test_range_years_format():
    assert extract_experience("2-4 years of experience") == {"min_years": 2, "max_years": 4}


def test_takes_the_primary_requirement_not_a_sub_clause():
    text = "5+ years of experience in HR, with at least 2 years in a managerial role"
    assert extract_experience(text) == {"min_years": 5, "max_years": None}


# ---------- education ----------

def test_mba_is_not_falsely_found_inside_mumbai():
    education = extract_education("Location: Mumbai, Maharashtra\nMBA required")
    assert education[0]["degree"] == "Master's"
    assert "Mumbai" not in (education[0].get("field_of_study") or "")


def test_education_is_a_list():
    assert isinstance(extract_education(cleaned("software_developer.txt")), list)


# ---------- employment type and salary: honest nulls ----------

def test_employment_type_detected_when_present():
    assert extract_employment_type("This is a Full-time role.") == "Full-time"


def test_salary_is_none_when_not_stated():
    assert extract_salary_range(cleaned("hr_manager.txt")) is None


def test_salary_does_not_false_match_on_years():
    # Regression test: "5+ years," must never be read as a salary figure
    assert extract_salary_range("5+ years, with strong communication skills") is None


def test_salary_detected_when_actually_present():
    assert extract_salary_range("CTC up to 12 LPA") == {"raw_text": "12 LPA"}


# ---------- responsibilities ----------

def test_responsibilities_are_extracted_as_a_list():
    items = extract_responsibilities(cleaned("hr_manager.txt"))
    assert len(items) == 4
    assert items[0] == "Lead end-to-end recruitment for multiple departments"


# ---------- end-to-end, matching Day 4's schema shape ----------

def test_parse_jd_text_matches_day_4_schema_fields():
    result = parse_jd_text(read("hr_manager.txt"), source_file="hr_manager.txt")
    for field in ("job_id", "title", "department", "employment_type", "location",
                  "experience_required", "required_skills", "education_requirements",
                  "responsibilities", "salary_range"):
        assert field in result

    assert result["title"] == "HR Manager"
    assert result["location"] == "Chennai, Tamil Nadu"
    assert result["experience_required"] == {"min_years": 5, "max_years": None}
    assert any(s["name"] == "HRIS" for s in result["required_skills"])
    assert result["job_id"] is None
    assert result["salary_range"] is None


def test_parse_folder_saves_one_json_per_jd(tmp_path):
    results = parse_folder(str(JD_DIR), str(tmp_path))
    assert len(results) == 8
    assert len(list(tmp_path.glob("*.json"))) == 8

    saved = json.loads((tmp_path / "sales_executive.json").read_text(encoding="utf-8"))
    assert saved["title"] == "Sales Executive"
    assert saved["department"] == "Sales"