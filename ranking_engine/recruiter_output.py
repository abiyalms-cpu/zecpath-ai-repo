import csv
import json
from pathlib import Path

from ranking_engine.ranking import rank_candidates_for_jd
from ranking_engine.shortlisting import apply_shortlisting


def _matched_skill_names(skills_dir, resume, jd_record, limit=3):
    """Recomputes the actual matched skill names (not just the score) for a
    recruiter-readable column — Day 13's score doesn't carry the names themselves."""
    stem = resume.replace(".", "_")
    skill_path = Path(skills_dir) / f"{stem}_skills.json"
    if not skill_path.exists():
        return ""

    skill_profile = json.load(open(skill_path, encoding="utf-8"))
    candidate_lookup = {s["skill"].lower(): s["skill"] for s in skill_profile.get("skills", [])}
    required_names = [s["name"] for s in jd_record.get("required_skills", [])]
    matched = [name for name in required_names if name.lower() in candidate_lookup]
    return ", ".join(matched[:limit])


def export_jd_csv(candidate_scores_dir, skills_dir, jds_dir, jd_file, output_dir):
    """One CSV per JD: rank, candidate, final score, zone, matched skills, and each
    component score — a blank Matched Skills column (real for non-technical roles,
    since Day 9's dictionary doesn't cover every tool name) still shows a recruiter
    WHY a candidate ranked where they did via the other components."""
    jd_record = json.load(open(f"{jds_dir}/{jd_file}.json", encoding="utf-8"))

    ranked = rank_candidates_for_jd(candidate_scores_dir, jd_file)
    zoned = apply_shortlisting(ranked)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"{jd_file}_ranked.csv"

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Rank", "Candidate", "Final Score", "Zone", "Matched Skills",
            "Skill Match", "Experience Relevance", "Education Alignment", "Semantic Similarity",
        ])
        for c in zoned:
            matched = _matched_skill_names(skills_dir, c["resume"], jd_record)
            by_component = {b["component"]: b["raw_score"] for b in c["breakdown"]}
            writer.writerow([
                c["rank"], c["resume"], c["final_score"], c["zone"], matched,
                by_component.get("skill_match"),
                by_component.get("experience_relevance"),
                by_component.get("education_alignment"),
                by_component.get("semantic_similarity"),
            ])

    return out_path

def export_all_jds(candidate_scores_dir, skills_dir, jds_dir, output_dir):
    count = 0
    for path in Path(jds_dir).glob("*.json"):
        jd_file = path.stem
        export_jd_csv(candidate_scores_dir, skills_dir, jds_dir, jd_file, output_dir)
        count += 1
    return count
