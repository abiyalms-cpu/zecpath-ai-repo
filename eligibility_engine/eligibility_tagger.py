import glob
import json
from pathlib import Path

from eligibility_engine.eligibility_engine import evaluate_candidate
from eligibility_engine.eligibility_rules import build_rules_for_jd
from utils.logger import get_logger

logger = get_logger(__name__)


def _load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if Path(path).exists() else default


def evaluate_jd(candidate_scores_dir, skills_dir, experience_dir, jds_dir, jd_file, output_dir, min_score=None):
    """One JD, every candidate who has an ATS score for it. Mirrors how
    ranking_engine.rank_candidates_for_jd reads the same candidate_scores
    files — a candidate with no score on record for this JD is skipped here
    too, not guessed at."""
    jd_record = json.load(open(f"{jds_dir}/{jd_file}.json", encoding="utf-8"))
    rules = build_rules_for_jd(jd_record, jd_file, min_score=min_score)

    results = []
    for path in glob.glob(f"{candidate_scores_dir}/*_scores.json"):
        record = json.load(open(path, encoding="utf-8"))
        match = next((s for s in record["scores"] if s["jd_file"] == jd_file), None)
        if match is None:
            continue

        resume = record["resume"]
        stem = resume.replace(".", "_")
        skill_profile = _load_json(f"{skills_dir}/{stem}_skills.json", {"skills": []})
        experience_record = _load_json(f"{experience_dir}/{stem}_experience.json", {"total_experience_months": 0})

        results.append(evaluate_candidate(resume, match["final_score"], skill_profile, experience_record, rules))

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"{jd_file}_eligibility.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"jd_file": jd_file, "rules": rules, "candidates": results}, f, indent=2)
    logger.info(f"Saved {out_path}")

    return results


def evaluate_all_jds(candidate_scores_dir, skills_dir, experience_dir, jds_dir, output_dir, min_score=None):
    count = 0
    for path in Path(jds_dir).glob("*.json"):
        jd_file = path.stem
        evaluate_jd(candidate_scores_dir, skills_dir, experience_dir, jds_dir, jd_file, output_dir, min_score=min_score)
        count += 1
    return count