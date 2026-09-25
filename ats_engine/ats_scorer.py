"""
Scores a parsed resume against a job's required skills.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def score_resume(parsed_resume: dict, required_skills: list) -> dict:
    """Compare a parsed resume's skills against what the role needs."""
    candidate_skills = parsed_resume.get("skills", [])
    matched = [s for s in required_skills if s in candidate_skills]
    missing = [s for s in required_skills if s not in candidate_skills]

    score = round((len(matched) / len(required_skills)) * 100) if required_skills else 0

    logger.info(f"ATS score computed: {score} (matched {len(matched)}/{len(required_skills)})")

    return {
        "ats_score": score,
        "matched_skills": matched,
        "missing_skills": missing,
    }