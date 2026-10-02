"""
Main entry point of the resume section classifier.

Reads already-extracted resume text (from Day 5's extractor), tags each
line with the section it belongs to, and saves one JSON per resume.
"""

import json
import os

from parsers.section_classifier import classify_sections
from utils.logger import get_logger

logger = get_logger(__name__)


def tag_resume(extracted_record: dict) -> dict:
    """Classify an already-extracted resume's text into labeled sections."""
    if not extracted_record.get("text"):
        return {
            "source_file": extracted_record.get("source_file"),
            "method": "skipped",
            "sections": {},
        }

    result = classify_sections(extracted_record["text"])
    return {
        "source_file": extracted_record.get("source_file"),
        "method": result["method"],
        "sections": result["sections"],
    }


def tag_folder(extracted_dir: str, output_dir: str) -> list:
    """Tag every extracted resume JSON in a folder and save the labeled result."""
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for name in sorted(os.listdir(extracted_dir)):
        if not name.endswith(".json"):
            continue

        record = json.load(open(os.path.join(extracted_dir, name), encoding="utf-8"))
        tagged = tag_resume(record)

        out_name = os.path.splitext(name)[0] + "_sections.json"
        with open(os.path.join(output_dir, out_name), "w", encoding="utf-8") as f:
            json.dump(tagged, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {out_name}")
        results.append(tagged)

    return results
