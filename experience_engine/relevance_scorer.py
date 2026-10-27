"""
Scores how relevant a candidate's past roles are to a target job, using
two signals:
  - role-to-role similarity: does a past job title match the target
    role, using Day 6's role synonym normalization (so "Frontend
    Developer" and "Frontend Engineer" are recognized as the same role)
  - skill overlap: how much of the target job's required skills show up
    in the candidate's Day 9 skill profile, when one is supplied

A candidate's strongest matching past job is what should count toward
relevance, not an average dragged down by one unrelated early job -- so
the role score is the best score across all their jobs, not a mean.
"""

from parsers.jd_extractor import normalize_role
from experience_engine.experience_calculator import total_experience_months

TARGET_SENIORITY_MONTHS = 60  # 5 years treated as "fully experienced" for this signal


def role_similarity(past_title, target_role):
    """
    0-1 similarity between a candidate's past job title and a target
    role. An exact canonical match (via Day 6's role synonyms) scores
    1.0; otherwise falls back to word overlap for a partial score.
    """
    if not past_title or not target_role:
        return 0.0

    past_norm = normalize_role(past_title)
    target_norm = normalize_role(target_role)

    if past_norm and target_norm and past_norm == target_norm:
        return 1.0

    past_words = set((past_norm or past_title).lower().split())
    target_words = set((target_norm or target_role).lower().split())
    if not past_words or not target_words:
        return 0.0

    overlap = past_words & target_words
    return round(len(overlap) / len(past_words | target_words), 3)


def experience_depth_factor(months):
    """0-1 signal for how much real tenure a candidate has: 0 months -> 0.0,
    60+ months -> 1.0, linear in between. This exists because total_experience_months
    was already being computed correctly by Day 10 but never used anywhere in
    scoring -- which let a multi-month intern match or beat a candidate with years
    of real, relevant experience purely on skill-name overlap."""
    if not months:
        return 0.0
    return round(min(months / TARGET_SENIORITY_MONTHS, 1.0), 3)


def score_candidate_relevance(jobs, target_jd, skill_profile=None, total_months=None):
    """
    jobs: parsed job entries from experience_parser.py
    target_jd: a Day 6 parsed JD dict (has 'title' and 'required_skills')
    skill_profile: optional Day 9 skill profile (list of {"skill": ...})
    total_months: optional precomputed total_experience_months (Day 10); if not
        given, it's computed here from jobs rather than left out.

    Returns the role-similarity score (best matching past job), the
    skill overlap ratio against the JD's mandatory required skills (if a
    skill_profile was given), the experience-depth factor, and an overall
    score combining all available signals.
    """
    per_job = []
    for job in jobs:
        per_job.append({
            "title": job.get("title"),
            "company": job.get("company"),
            "role_similarity": role_similarity(job.get("title"), target_jd.get("title")),
        })

    role_relevance = max((e["role_similarity"] for e in per_job), default=0.0)

    skill_overlap = None
    if skill_profile is not None:
        required = {
            s["name"].lower()
            for s in target_jd.get("required_skills", [])
            if s.get("mandatory")
        }
        if required:
            candidate_skills = {s["skill"].lower() for s in skill_profile}
            matched = required & candidate_skills
            skill_overlap = round(len(matched) / len(required), 3)

    if total_months is None:
        total_months = total_experience_months(jobs)
    depth = experience_depth_factor(total_months)

    components_to_average = [role_relevance, depth]
    if skill_overlap is not None:
        components_to_average.append(skill_overlap)
    overall = round(sum(components_to_average) / len(components_to_average), 3)

    return {
        "overall_relevance": overall,
        "role_relevance": role_relevance,
        "skill_overlap": skill_overlap,
        "experience_depth": depth,
        "per_job": per_job,
    }