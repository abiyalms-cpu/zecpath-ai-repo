from experience_engine.relevance_scorer import score_candidate_relevance
from education_engine.education_relevance import score_field_relevance


def skill_match_score(skill_profile_record, jd_record):
    """Weighted match of a candidate's extracted skills against a JD's required
    skills — mandatory skills count fully, nice-to-have skills count half."""
    required_skills = jd_record.get("required_skills") or []
    if not required_skills:
        return None  # JD has no stated skill requirements — can't score this honestly

    candidate_names = {s["skill"].strip().lower() for s in (skill_profile_record.get("skills") or [])}

    mandatory = [s for s in required_skills if s.get("mandatory")]
    optional = [s for s in required_skills if not s.get("mandatory")]

    matched_mandatory = sum(1 for s in mandatory if s["name"].strip().lower() in candidate_names)
    matched_optional = sum(1 for s in optional if s["name"].strip().lower() in candidate_names)

    total_weight = len(mandatory) * 1.0 + len(optional) * 0.5
    if total_weight == 0:
        return None

    matched_weight = matched_mandatory * 1.0 + matched_optional * 0.5
    return round(matched_weight / total_weight, 4)


def experience_relevance_score(experience_record, jd_record, skill_profile_record):
    """Reuses Day 10's role + skill relevance scorer directly rather than
    reimplementing title-matching logic a second time."""
    jobs = experience_record.get("jobs") or []
    if not jobs:
        return None  # no parsed work history — not guessed at as zero

    skills = skill_profile_record.get("skills") if skill_profile_record else None
    result = score_candidate_relevance(jobs, jd_record, skill_profile=skills)
    return result["overall_relevance"]


def education_alignment_score(education_record, jd_record):
    """Field-of-study relevance only (Day 11's role_similarity-based scorer).
    Certification-to-role-domain matching is intentionally left out — it would need
    a hand-built role-to-category mapping with too little real data to validate it."""
    education_entries = education_record.get("education") or []
    target_role = jd_record.get("title") or ""
    if not education_entries or not target_role:
        return None
    return score_field_relevance(education_entries, target_role)


def semantic_similarity_score(semantic_match_record, jd_file):
    """Looks up the precomputed Day 12 score for this specific resume/JD pair
    rather than recomputing the vector space model on the fly."""
    matches = semantic_match_record.get("matches") or []
    for m in matches:
        if m["jd_file"] == jd_file:
            return m["overall_similarity"]
    return None  # this resume/JD pair wasn't precomputed