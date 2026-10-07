import glob
import json
from pathlib import Path
from datetime import datetime, timezone

from education_engine.education_parser import parse_education_section, parse_certification_section
from education_engine.certification_tagger import tag_certifications
from utils.logger import get_logger

logger = get_logger(__name__)


def build_education_record(segmented_record):
    method = segmented_record.get("method", "unknown")
    sections = segmented_record.get("sections") or {}

    education = parse_education_section(sections.get("EDUCATION"))
    certifications = tag_certifications(parse_certification_section(sections.get("CERTIFICATIONS")))

    return {
        "source_file": segmented_record.get("source_file"),
        "method": method,
        "education": education,
        "certifications": certifications,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }


def tag_folder(segmented_dir, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    count = 0
    for path in glob.glob(f"{segmented_dir}/*_sections.json"):
        with open(path, encoding="utf-8") as f:
            segmented_record = json.load(f)

        record = build_education_record(segmented_record)

        out_name = Path(path).stem.replace("_sections", "_education") + ".json"
        out_path = Path(output_dir) / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        logger.info(f"Saved {out_path}")
        count += 1

    logger.info(f"Tagged {count} resumes")
    return count