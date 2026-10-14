import csv
import json
from pathlib import Path

from ranking_engine.ranking import rank_candidates_for_jd
from ranking_engine.shortlisting import apply_shortlisting
from ranking_engine.recruiter_output import _matched_skill_names
from fairness_engine.anonymizer import build_candidate_id_map


def export_anonymized_jd_csv(candidate_scores_dir, skills_dir, jds_dir, jd_file, output_dir, id_map):
    """Same ranked output as Day 14's recruiter CSV, but with the candidate's
    filename (which leaks their real name) replaced by a stable anonymized ID —
    reuses Day 14's ranking and shortlisting logic rather than duplicating it."""
    jd_record = json.load(open(f"{jds_dir}/{jd_file}.json", encoding="utf-8"))
    ranked = rank_candidates_for_jd(candidate_scores_dir, jd_file)
    zoned = apply_shortlisting(ranked)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"{jd_file}_ranked_anonymized.csv"

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Rank", "Candidate ID", "Final Score", "Zone", "Matched Skills",
            "Skill Match", "Experience Relevance", "Education Alignment", "Semantic Similarity",
        ])
        for c in zoned:
            stem = c["resume"].replace(".", "_")
            candidate_id = id_map.get(stem, stem)
            matched = _matched_skill_names(skills_dir, c["resume"], jd_record)
            by_component = {b["component"]: b["raw_score"] for b in c["breakdown"]}
            writer.writerow([
                c["rank"], candidate_id, c["final_score"], c["zone"], matched,
                by_component.get("skill_match"),
                by_component.get("experience_relevance"),
                by_component.get("education_alignment"),
                by_component.get("semantic_similarity"),
            ])

    return out_path


def export_all_anonymized(candidate_scores_dir, skills_dir, segmented_dir, jds_dir, output_dir, id_map_output_path):
    """Builds the ID map once, saves it as the re-identification key (kept separate
    from the recruiter-facing CSVs — a recruiter should never receive this file),
    then exports one anonymized CSV per JD."""
    id_map = build_candidate_id_map(segmented_dir)

    Path(id_map_output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(id_map_output_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2)

    count = 0
    for path in Path(jds_dir).glob("*.json"):
        jd_file = path.stem
        export_anonymized_jd_csv(candidate_scores_dir, skills_dir, jds_dir, jd_file, output_dir, id_map)
        count += 1
    return count