"""
Main entry point of the JD parsing system.

Give it a job description (plain text) and it returns a structured job
requirement object matching Day 4's JD schema: role, location, department,
experience, education, skills and responsibilities, normalized against the
synonym tables so different wordings collapse into one form.
"""

import json
import os
from datetime import datetime

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
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_jd_text(raw_text: str, source_file: str = "") -> dict:
    """Turn raw JD text into a structured job requirement object."""
    text = clean_jd_text(raw_text)

    role = extract_role(text)
    if not role:
        logger.warning(f"No known role found in {source_file or 'JD text'}")

    return {
        # job_id is assigned by whatever system creates the posting - it
        # cannot be extracted from the JD text itself, so it stays null here.
        "job_id": None,
        "title": role,
        "department": extract_department(text),
        "employment_type": extract_employment_type(text),
        "location": extract_location(text),
        "experience_required": extract_experience(text),
        "required_skills": extract_skills(text),
        "education_requirements": extract_education(text),
        "responsibilities": extract_responsibilities(text),
        "salary_range": extract_salary_range(text),
        "source_file": source_file,
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
        "normalized_text": text,
    }


def parse_folder(input_dir: str, output_dir: str) -> list:
    """Parse every .txt JD in a folder and save each as a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for name in sorted(os.listdir(input_dir)):
        if not name.lower().endswith(".txt"):
            continue

        path = os.path.join(input_dir, name)
        raw_text = open(path, encoding="utf-8").read()
        result = parse_jd_text(raw_text, source_file=name)

        out_name = os.path.splitext(name)[0] + ".json"
        with open(os.path.join(output_dir, out_name), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {out_name}")
        results.append(result)

    return results