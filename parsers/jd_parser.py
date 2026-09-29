"""
Main entry point of the JD parsing system.

Give it a job description (plain text) and it returns a structured job
requirement object: role, experience, education and skills, normalized
against the synonym tables, in the shape Day 4's JD schema defined.
"""

import json
import os
from datetime import datetime

from parsers.jd_cleaner import clean_jd_text
from parsers.jd_extractor import extract_education, extract_experience, extract_role, extract_skills
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_jd_text(raw_text: str, source_file: str = "") -> dict:
    """Turn raw JD text into a structured job requirement object."""
    text = clean_jd_text(raw_text)

    role = extract_role(text)
    experience = extract_experience(text)
    education = extract_education(text)
    skills = extract_skills(text)

    if not role:
        logger.warning(f"No known role found in {source_file or 'JD text'}")

    return {
        "source_file": source_file,
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
        "title": role,
        "experience_required": experience,
        "education_requirement": education,
        "required_skills": skills,
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