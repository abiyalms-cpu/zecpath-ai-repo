"""
Automated tests for the JD parsing system.
"""

import json
from pathlib import Path

from parsers.jd_cleaner import clean_jd_text
from parsers.jd_extractor import extract_education, extract_experience, extract_role, extract_skills
from parsers.jd_parser import parse_folder, parse_jd_text

JD_DIR = Path(__file__).resolve().parent.parent / "data" / "job_descriptions"


def read(name: str) -> str:
    return (JD_DIR / name).read_text(encoding="utf-8")


# ---------- cleaning ----------

def test_cleaner_normalizes_heading_variants():
    assert clean_jd_text("What You'll Need:\nsomething").startswith("REQUIREMENTS")


def test_cleaner_splits_inline_heading_from_content():
    result = clean_jd_text("Bonus: Google Ads certification")
    assert result == "NICE TO HAVE\n- Google Ads certification"


# ---------- role variation detection ----------

def test_two_worded_differently_are_the_same_role():
    role_a = extract_role(read("software_developer.txt"))
    role_b = extract_role(read("sde_ii.txt"))
    assert role_a == role_b == "Software Engineer"


def test_role_survives_word_boundary_fix():
    # "Mumbai" must not be mistaken for a role or skill match
    assert extract_role("Location: Mumbai, Maharashtra") is None


# ---------- skill synonym detection ----------

def test_skill_synonyms_map_to_one_canonical_name():
    skills = extract_skills("Experience with ReactJS and React required.")
    assert skills == ["React"]


def test_java_is_not_falsely_found_inside_javascript():
    skills = extract_skills("Proficiency in JavaScript required.")
    assert "Java" not in skills
    assert "JavaScript" in skills


def test_hris_is_not_falsely_found_inside_thrissur():
    skills = extract_skills("Location: Thrissur, Kerala")
    assert "HRIS" not in skills


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
    assert education["level"] == "Master's"
    assert "Mumbai" not in education["raw_text"]


# ---------- end-to-end ----------

def test_parse_jd_text_returns_a_complete_object():
    result = parse_jd_text(read("hr_manager.txt"), source_file="hr_manager.txt")
    assert result["title"] == "HR Manager"
    assert result["experience_required"] == {"min_years": 5, "max_years": None}
    assert result["education_requirement"]["level"] == "Master's"
    assert "HRIS" in result["required_skills"]


def test_parse_folder_saves_one_json_per_jd(tmp_path):
    results = parse_folder(str(JD_DIR), str(tmp_path))
    assert len(results) == 8
    assert len(list(tmp_path.glob("*.json"))) == 8

    saved = json.loads((tmp_path / "sales_executive.json").read_text(encoding="utf-8"))
    assert saved["title"] == "Sales Executive"