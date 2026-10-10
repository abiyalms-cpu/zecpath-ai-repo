import glob
import json


def rank_candidates_for_jd(candidate_scores_dir, jd_file):
    """Loads every candidate's Day 13 score for a specific JD and sorts descending.
    A candidate with no score on record for this JD is skipped, not guessed at."""
    ranked = []
    for path in glob.glob(f"{candidate_scores_dir}/*_scores.json"):
        record = json.load(open(path, encoding="utf-8"))
        match = next((s for s in record["scores"] if s["jd_file"] == jd_file), None)
        if match is None:
            continue
        ranked.append({
            "resume": record["resume"],
            "final_score": match["final_score"],
            "breakdown": match["breakdown"],
        })

    ranked.sort(key=lambda r: -r["final_score"])
    for i, entry in enumerate(ranked, start=1):
        entry["rank"] = i

    return ranked