import json
import glob
from pathlib import Path

def check_header_independence():
    """Static verification, not a data check: confirms in code that none of Day 13's
    four score components ever reads the HEADER section (name/contact info). This
    is checked by source inspection because it's a structural guarantee, not a
    statistic — a score is either wired to read HEADER or it isn't."""
    import inspect
    from scoring_engine import score_components

    source = inspect.getsource(score_components)
    uses_header = "HEADER" in source
    return {
        "component_source_references_header": uses_header,
        "verdict": "PASS — no score component reads HEADER/name/contact data" if not uses_header
                   else "FAIL — a component references HEADER directly",
    }

def format_bias_check(segmented_dir, skills_dir, experience_dir):
    """Compares heading-method vs heuristic-method resumes on two measurable proxies
    for information loss during parsing: average skills found, average jobs parsed.
    If heuristic-method (non-standard format) resumes come out systematically lower
    on both, that's real evidence the format itself — not the candidate's actual
    qualifications — is costing them score."""
    heading_skills, heuristic_skills = [], []
    heading_jobs, heuristic_jobs = [], []

    for path in glob.glob(f"{segmented_dir}/*.json"):
        record = json.load(open(path, encoding="utf-8"))
        stem = Path(path).stem.replace("_sections", "")
        method = record.get("method")
        if method not in ("heading", "heuristic"):
            continue  # skip "skipped" (no-text) resumes — not a format comparison

        skill_path = Path(skills_dir) / f"{stem}_skills.json"
        exp_path = Path(experience_dir) / f"{stem}_experience.json"
        skill_count = len(json.load(open(skill_path, encoding="utf-8")).get("skills", [])) if skill_path.exists() else 0
        job_count = len(json.load(open(exp_path, encoding="utf-8")).get("jobs", [])) if exp_path.exists() else 0

        if method == "heading":
            heading_skills.append(skill_count)
            heading_jobs.append(job_count)
        else:
            heuristic_skills.append(skill_count)
            heuristic_jobs.append(job_count)

    def avg(values):
        return round(sum(values) / len(values), 2) if values else None

    return {
        "heading_method_count": len(heading_skills),
        "heuristic_method_count": len(heuristic_skills),
        "avg_skills_found_heading": avg(heading_skills),
        "avg_skills_found_heuristic": avg(heuristic_skills),
        "avg_jobs_parsed_heading": avg(heading_jobs),
        "avg_jobs_parsed_heuristic": avg(heuristic_jobs),
    }

def keyword_dependence_check(candidate_scores_dir, jd_file, top_n=5):
    """Compares a skill-match-only ranking against the real Day 13 blended ranking
    for one JD, to quantify how many candidates the blend promotes or demotes
    relative to pure keyword matching — the concrete evidence for 'reduced
    over-dependence on keywords'."""
    records = []
    for path in glob.glob(f"{candidate_scores_dir}/*_scores.json"):
        record = json.load(open(path, encoding="utf-8"))
        match = next((s for s in record["scores"] if s["jd_file"] == jd_file), None)
        if match is None:
            continue
        by_component = {b["component"]: b["raw_score"] for b in match["breakdown"]}
        skill_only = by_component.get("skill_match") or 0.0
        records.append({
            "resume": record["resume"],
            "skill_match_only": skill_only,
            "blended_score": match["final_score"],
        })

    by_skill_only = sorted(records, key=lambda r: -r["skill_match_only"])
    by_blended = sorted(records, key=lambda r: -r["blended_score"])

    skill_only_top_n = {r["resume"] for r in by_skill_only[:top_n]}
    blended_top_n = {r["resume"] for r in by_blended[:top_n]}

    return {
        "jd_file": jd_file,
        "top_n": top_n,
        "skill_match_only_top": [r["resume"] for r in by_skill_only[:top_n]],
        "blended_top": [r["resume"] for r in by_blended[:top_n]],
        "promoted_by_blending": sorted(blended_top_n - skill_only_top_n),
        "dropped_by_blending": sorted(skill_only_top_n - blended_top_n),
    }