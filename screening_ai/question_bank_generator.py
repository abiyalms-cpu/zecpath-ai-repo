import json
from pathlib import Path

from screening_ai.question_builder import build_question_bank_for_jd
from utils.logger import get_logger

logger = get_logger(__name__)


def build_bank_for_jd(jds_dir, jd_file, output_dir):
    """One JD, one saved question bank -- mirrors how every other *_tagger.py
    in this repo reads one JD/resume record and writes one output file."""
    jd_record = json.load(open(f"{jds_dir}/{jd_file}.json", encoding="utf-8"))
    questions = build_question_bank_for_jd(jd_record, jd_file)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"{jd_file}_questions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"jd_file": jd_file, "role_title": jd_record.get("title"), "questions": questions}, f, indent=2)
    logger.info(f"Saved {out_path}")

    return questions


def build_all_banks(jds_dir, output_dir):
    count = 0
    for path in Path(jds_dir).glob("*.json"):
        jd_file = path.stem
        build_bank_for_jd(jds_dir, jd_file, output_dir)
        count += 1
    return count