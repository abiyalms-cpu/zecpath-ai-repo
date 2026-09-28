"""
Automated tests for the resume text extraction engine.

Run from the project root with:  pytest
"""

import json
from pathlib import Path

import pytest

from parsers.extractor import extract_folder, extract_resume_text
from parsers.text_cleaner import clean_text

RESUME_DIR = Path(__file__).resolve().parent.parent / "data" / "resumes"

# Resumes that exist as both DOCX and PDF - the two must give identical text
PAIRED = [
    "aditya_rao", "anjali_suresh", "arun_kumar", "divya_menon", "fathima_rasheed",
    "karthik_subramaniam", "priya_nair", "rohan_mehta", "sneha_thomas", "vishnu_prasad",
]


def extract(file_name: str) -> dict:
    return extract_resume_text(str(RESUME_DIR / file_name))


# ---------- text cleaner ----------

def test_cleaner_standardises_bullets():
    assert clean_text("● one\n• two\n* three") == "- one\n- two\n- three"


def test_cleaner_collapses_repeated_spaces():
    assert clean_text("Pune  —  Jul 2021") == "Pune — Jul 2021"


def test_cleaner_normalises_section_headings():
    assert clean_text("Work Experience:\nTechnical Skills") == "EXPERIENCE\nSKILLS"


def test_cleaner_fixes_shouting_names():
    assert clean_text("ROHAN MEHTA") == "Rohan Mehta"


def test_cleaner_leaves_acronyms_alone():
    assert clean_text("AWS") == "AWS"


# ---------- DOCX and PDF must agree ----------

@pytest.mark.parametrize("name", PAIRED)
def test_docx_and_pdf_give_the_same_text(name):
    assert extract(f"{name}.docx")["text"] == extract(f"{name}.pdf")["text"]


# ---------- different layouts ----------

def test_table_contents_are_kept():
    text = extract("meera_iyer_table.docx")["text"]
    for expected in ["SQL | Advanced", "Power BI | Intermediate",
                     "B.Sc Statistics | Loyola College | 2020"]:
        assert expected in text


def test_two_columns_are_read_in_order():
    text = extract("nikhil_verma_two_column.pdf")["text"]
    assert text.index("SKILLS") < text.index("EDUCATION") < text.index("SUMMARY") < text.index("EXPERIENCE")


def test_two_column_lines_are_not_mixed_together():
    lines = extract("nikhil_verma_two_column.pdf")["text"].splitlines()
    assert "Full stack developer with 5 years of experience building web apps for fintech and retail clients." in lines
    assert "B.Tech, Information Technology" in lines


def test_photo_in_docx_does_not_break_extraction():
    result = extract("ishaan_kapoor_photo.docx")
    assert result["status"] == "ok"
    assert "Ishaan Kapoor" in result["text"]
    assert "- Reduced delivery delays by 27% across 4 regional hubs" in result["text"]


def test_scanned_pdf_is_flagged_not_crashed():
    result = extract("zoya_khan_scanned.pdf")
    assert result["status"] == "no_text_found"
    assert result["text"] == ""


# ---------- engine behaviour ----------

def test_unsupported_file_type_is_rejected(tmp_path):
    bad_file = tmp_path / "resume.txt"
    bad_file.write_text("not a resume")
    with pytest.raises(ValueError):
        extract_resume_text(str(bad_file))


def test_extract_folder_saves_one_json_per_resume(tmp_path):
    expected = len([p for p in RESUME_DIR.iterdir() if p.suffix.lower() in (".docx", ".pdf")])
    results = extract_folder(str(RESUME_DIR), str(tmp_path))

    assert len(results) == expected
    assert len(list(tmp_path.glob("*.json"))) == expected

    saved = json.loads((tmp_path / "rohan_mehta_pdf.json").read_text(encoding="utf-8"))
    assert saved["status"] == "ok"
    assert "Rohan Mehta" in saved["text"]