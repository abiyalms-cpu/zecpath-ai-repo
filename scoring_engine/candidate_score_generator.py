import glob
import json
from pathlib import Path

from scoring_engine.scoring_engine import compute_candidate_score
from utils.logger import get_logger

logger = get_logger(__name__)


def _load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if Path(path).exists() else default


def score_all_resumes(segmented_dir, skills_dir, experience_dir, education_dir, semantic_dir, jds_dir, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    jds = {}
    for path in glob.glob(f"{jds_dir}/*.json"):
        jd_file = Path(path).stem
        jds[jd_file] = json.load(open(path, encoding="utf-8"))

    count = 0
    for path in glob.glob(f"{segmented_dir}/*.json"):
        stem = Path(path).stem.replace("_sections", "")

        skill_profile = _load_json(f"{skills_dir}/{stem}_skills.json", {"skills": []})
        experience_record = _load_json(f"{experience_dir}/{stem}_experience.json", {"jobs": []})
        education_record = _load_json(f"{education_dir}/{stem}_education.json", {"education": []})
        semantic_match_record = _load_json(f"{semantic_dir}/{stem}_matches.json", {"matches": []})

        resume_scores = []
        for jd_file, jd_record in jds.items():
            result = compute_candidate_score(
                skill_profile, experience_record, education_record, semantic_match_record, jd_record, jd_file
            )
            resume_scores.append({
                "jd_file": jd_file,
                "jd_title": jd_record.get("title"),
                "final_score": result["final_score"],
                "breakdown": result["breakdown"],
            })

        resume_scores.sort(key=lambda r: -r["final_score"])

        out_path = Path(output_dir) / f"{stem}_scores.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"resume": skill_profile.get("source_file", stem), "scores": resume_scores}, f, indent=2)
        logger.info(f"Saved {out_path}")
        count += 1

    logger.info(f"Scored {count} resumes across {len(jds)} JDs")
    return count