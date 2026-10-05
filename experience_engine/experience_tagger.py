"""
Runs the experience parser, calculator, and relevance scorer across a
whole folder of Day 8 section-tagged resumes and saves one structured
experience object per resume. Relevance scoring against a specific job
is optional — without a target JD, you still get jobs, total experience,
gaps, and overlaps for every resume.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from experience_engine.experience_parser import parse_experience_section
from experience_engine.experience_calculator import (
    total_experience_months,
    format_duration,
    find_gaps_and_overlaps,
)
from experience_engine.relevance_scorer import score_candidate_relevance
from utils.logger import get_logger

logger = get_logger(__name__)


def build_experience_record(segmented_record, target_jd=None, skill_profile=None):
    """
    segmented_record: full dict from a Day 8 *_sections.json file.
    target_jd / skill_profile: optional, to also score relevance against
    one specific job.
    """
    source_file = segmented_record.get("source_file")
    sections = segmented_record.get("sections", {})
    experience_lines = sections.get("EXPERIENCE", [])

    jobs = parse_experience_section(experience_lines)
    total_months = total_experience_months(jobs)
    years, months = format_duration(total_months)
    gaps, overlaps = find_gaps_and_overlaps(jobs)

    record = {
        "source_file": source_file,
        "jobs": jobs,
        "total_experience_months": total_months,
        "total_experience_display": f"{years}y {months}m",
        "gaps": gaps,
        "overlaps": overlaps,
        "relevance": None,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }

    if target_jd is not None:
        record["relevance"] = score_candidate_relevance(jobs, target_jd, skill_profile=skill_profile)

    return record


def tag_folder(segmented_dir, output_dir, skills_dir=None, target_jd=None):
    """
    Reads every *_sections.json in segmented_dir, builds a structured
    experience object for each, and saves one *_experience.json per
    resume in output_dir. If skills_dir and target_jd are given, each
    resume is also scored for relevance against that one job.
    """
    segmented_path = Path(segmented_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    count = 0
    for file_path in sorted(segmented_path.glob("*_sections.json")):
        with open(file_path, encoding="utf-8") as f:
            record = json.load(f)

        skill_profile = None
        if skills_dir is not None:
            skill_file = Path(skills_dir) / (file_path.stem.replace("_sections", "") + "_skills.json")
            if skill_file.exists():
                with open(skill_file, encoding="utf-8") as sf:
                    skill_profile = json.load(sf).get("skills")

        result = build_experience_record(record, target_jd=target_jd, skill_profile=skill_profile)

        out_name = file_path.stem.replace("_sections", "") + "_experience.json"
        out_path = output_path / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        logger.info("Saved %s", out_name)
        count += 1

    logger.info("%d resumes tagged with experience", count)
    return count