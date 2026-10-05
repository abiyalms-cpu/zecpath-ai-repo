"""
Scores how relevant a candidate's past roles are to a target job, using
two signals:
  - role-to-role similarity: does a past job title match the target
    role, using Day 6's role synonym normalization (so "Frontend
    Developer" and "Frontend Engineer" are recognized as the same role)
  - skill overlap: how much of the target job's required skills show up
    in the candidate's Day 9 skill profile, when one is supplied

A candidate's strongest matching past job is what should count toward
relevance, not an average dragged down by one unrelated early job — so
the role score is the best score across all their jobs, not a mean.
"""

from parsers.jd_extractor import normalize_role


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


def score_candidate_relevance(jobs, target_jd, skill_profile=None):
    """
    jobs: parsed job entries from experience_parser.py
    target_jd: a Day 6 parsed JD dict (has 'title' and 'required_skills')
    skill_profile: optional Day 9 skill profile (list of {"skill": ...})

    Returns the role-similarity score (best matching past job), the
    skill overlap ratio against the JD's mandatory required skills (if a
    skill_profile was given), and an overall score combining both.
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

    if skill_overlap is not None:
        overall = round((role_relevance + skill_overlap) / 2, 3)
    else:
        overall = role_relevance

    return {
        "overall_relevance": overall,
        "role_relevance": role_relevance,
        "skill_overlap": skill_overlap,
        "per_job": per_job,
    }