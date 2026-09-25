"""
Combines scores from ATS, screening, and interview into one recommendation.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def compute_final_score(scores: dict) -> dict:
    """Average the incoming scores and turn that into a recommendation."""
    values = [v for v in scores.values() if isinstance(v, (int, float))]
    final_score = round(sum(values) / len(values), 1) if values else 0

    if final_score >= 75:
        recommendation = "Selected"
    elif final_score >= 50:
        recommendation = "On Hold"
    else:
        recommendation = "Rejected"

    logger.info(f"Final score: {final_score} -> {recommendation}")

    return {
        "final_score": final_score,
        "recommendation": recommendation,
    }