"""
Decides eligibility for one candidate against one job role's rules, combining
the existing ATS score with two hard checks (mandatory skills, experience
range) the score alone doesn't enforce — a candidate can score well on
semantic similarity alone and still be missing every mandatory skill.

Candidate eligibility result structure (what evaluate_candidate returns) —
this IS the schema:
{
    "resume": "karthik_subramaniam.docx",
    "jd_file": "sde_ii",
    "final_score": 0.4086,
    "status": "Eligible" | "Review" | "Rejected",
    "checks": {
        "score": {"passed": bool, "value": 0.4086, "required_min": 0.15},
        "mandatory_skills": {"passed": bool, "missing": [...]},  # passes at >=50% matched, see _check_mandatory_skills
        "experience": {"passed": bool, "candidate_months": 82, "required": {...} or None},
        "location": {"evaluated": False, "reason": "..."},
    },
    "reasons": ["...human-readable lines explaining the status..."],
}
"""

from ranking_engine.shortlisting import REVIEW_THRESHOLD


def _check_score(final_score, rules):
    return {"passed": final_score >= rules["min_score"], "value": final_score, "required_min": rules["min_score"]}


def _check_mandatory_skills(skill_profile_record, rules):
    """Passes if at least half the mandatory skills were matched — not all of
    them. The skill dictionary (Day 9) doesn't cover every real tool name yet
    (Zendesk, Salesforce, SAP FICO, SolidWorks and several others aren't in it
    at all — the same gap recruiter_output.py already calls out for its
    Matched Skills column). Requiring every mandatory skill to match by exact
    name, against real resumes, gave 0% pass on 5 of 8 real job roles in
    testing — not because those candidates lack the skills, but because the
    dictionary can't recognize the skill name even when it's present on the
    resume. "At least half" keeps this a real, meaningful rule without
    silently vetoing every candidate over a pre-existing extraction gap that's
    out of scope for today."""
    mandatory = rules["mandatory_skills"]
    if not mandatory:
        return {"passed": True, "missing": []}  # nothing mandatory on this JD — can't fail what wasn't asked

    candidate_names = {s["skill"].strip().lower() for s in (skill_profile_record.get("skills") or [])}
    missing = [name for name in mandatory if name.strip().lower() not in candidate_names]
    matched_fraction = (len(mandatory) - len(missing)) / len(mandatory)
    return {"passed": matched_fraction >= 0.5, "missing": missing}


def _check_experience(experience_record, rules):
    required = rules["experience_range"]
    candidate_months = experience_record.get("total_experience_months", 0) or 0
    if not required:
        return {"passed": True, "candidate_months": candidate_months, "required": None}  # JD stated no range

    min_months = (required.get("min_years") or 0) * 12
    max_months = required.get("max_years") * 12 if required.get("max_years") is not None else None
    passed = candidate_months >= min_months and (max_months is None or candidate_months <= max_months)
    return {"passed": passed, "candidate_months": candidate_months, "required": required}


def _decide(score_check, skills_check, experience_check):
    """Rule-based + score-based, in that order: a hard rule failure (a missing
    mandatory skill, or experience outside the JD's stated range) rejects
    outright regardless of score, because those are the recruiter's own stated
    deal-breakers. Clearing both hard rules but missing the score cutoff is a
    softer call — Review, not Rejected, matching how ranking_engine already
    treats its middle zone as something a recruiter should look at themselves,
    not something the system silently drops."""
    if not skills_check["passed"] or not experience_check["passed"]:
        return "Rejected"
    if score_check["passed"]:
        return "Eligible"
    if score_check["value"] >= REVIEW_THRESHOLD:
        return "Review"
    return "Rejected"


def _explain(status, score_check, skills_check, experience_check):
    reasons = []
    if not skills_check["passed"]:
        reasons.append(f"Missing mandatory skills: {', '.join(skills_check['missing'])}")
    if not experience_check["passed"]:
        reasons.append(
            f"Experience ({experience_check['candidate_months']} months) outside required range "
            f"{experience_check['required']}"
        )
    if skills_check["passed"] and experience_check["passed"]:
        if score_check["passed"]:
            reasons.append(f"Score {score_check['value']} meets the {score_check['required_min']} cutoff")
        else:
            reasons.append(f"Score {score_check['value']} is below the {score_check['required_min']} cutoff")
    return reasons


def evaluate_candidate(resume_name, final_score, skill_profile_record, experience_record, rules):
    score_check = _check_score(final_score, rules)
    skills_check = _check_mandatory_skills(skill_profile_record, rules)
    experience_check = _check_experience(experience_record, rules)
    status = _decide(score_check, skills_check, experience_check)

    return {
        "resume": resume_name,
        "jd_file": rules["jd_file"],
        "final_score": final_score,
        "status": status,
        "checks": {
            "score": score_check,
            "mandatory_skills": skills_check,
            "experience": experience_check,
            "location": rules["location"],
        },
        "reasons": _explain(status, score_check, skills_check, experience_check),
    }