"""
Builds the eligibility rule set for one job role (one JD) out of data that
already exists elsewhere in the pipeline, so a recruiter never has to type
the same requirement twice.

Rule config format (what build_rules_for_jd returns) — this IS the schema:
{
    "jd_file": "sde_ii",
    "min_score": 0.15,                       # recruiter override, or the
                                              # existing shortlist threshold
    "mandatory_skills": ["JavaScript", ...], # from the JD's own required_skills,
                                              # filtered to mandatory: true
    "experience_range": {"min_years": 3, "max_years": None},  # from the JD, as-is
    "location": {
        "evaluated": False,
        "reason": "..."
    }
}
"""

from ranking_engine.shortlisting import SHORTLIST_THRESHOLD

# Candidate resumes have no parsed location or availability/notice-period field
# anywhere in this pipeline today (confirmed by searching every parser module).
# The PRD itself explains why: that data is captured later, by the AI screening
# call (Phase 5 — "Current location", "Notice period"), not by resume parsing
# (Phase 2). So this rule's slot exists in the config for when that data is
# wired up, but it is honestly marked unevaluated rather than guessed at from
# unstructured resume text.
LOCATION_NOT_YET_AVAILABLE = {
    "evaluated": False,
    "reason": (
        "No resume-side location/availability field exists yet. Per the PRD, "
        "this is captured later via the AI screening call (Phase 5), not from "
        "resume parsing (Phase 2)."
    ),
}


def build_rules_for_jd(jd_record, jd_file, min_score=None):
    """jd_record is the parsed JD dict (data/parsed_jds/<jd_file>.json).
    min_score lets a recruiter override the default cutoff for this role;
    if they haven't set one, we fall back to the existing shortlist threshold
    so eligibility stays consistent with what ranking_engine already calls
    a real match."""
    required_skills = jd_record.get("required_skills") or []
    mandatory_skills = [s["name"] for s in required_skills if s.get("mandatory")]

    return {
        "jd_file": jd_file,
        "min_score": min_score if min_score is not None else SHORTLIST_THRESHOLD,
        "mandatory_skills": mandatory_skills,
        "experience_range": jd_record.get("experience_required"),
        "location": dict(LOCATION_NOT_YET_AVAILABLE),
    }