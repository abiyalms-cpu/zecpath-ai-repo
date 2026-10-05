"""
Runs the skill engine across a whole folder of Day 8 section-tagged
resumes and saves one structured skill profile per resume.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from skills_engine.skill_profile import build_skill_profile
from utils.logger import get_logger

logger = get_logger(__name__)


def tag_skills(segmented_record):
    """
    segmented_record: the full dict loaded from a Day 8 *_sections.json
    file (source_file, method, sections).

    Returns a dict with the extracted skill profile added. A resume with
    no text at all (method == "skipped") is passed through honestly —
    no skills are invented for it.
    """
    source_file = segmented_record.get("source_file")
    method = segmented_record.get("method")
    sections = segmented_record.get("sections", {})

    if method == "skipped" or not sections:
        return {
            "source_file": source_file,
            "method": "skipped",
            "skills": [],
            "total_skills_found": 0,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

    profile = build_skill_profile(sections)

    return {
        "source_file": source_file,
        "method": method,
        "skills": profile,
        "total_skills_found": len(profile),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }


def tag_folder(segmented_dir, output_dir):
    """
    Reads every *_sections.json file in segmented_dir, runs the skill
    engine on each, and saves one matching *_skills.json file per resume
    in output_dir.
    """
    segmented_path = Path(segmented_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    count = 0
    for file_path in sorted(segmented_path.glob("*_sections.json")):
        with open(file_path, encoding="utf-8") as f:
            record = json.load(f)

        result = tag_skills(record)

        out_name = file_path.stem.replace("_sections", "") + "_skills.json"
        out_path = output_path / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        logger.info("Saved %s", out_name)
        count += 1

    logger.info("%d resumes tagged with skills", count)
    return count