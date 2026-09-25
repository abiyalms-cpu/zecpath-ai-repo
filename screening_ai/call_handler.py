"""
Triggers and tracks the AI screening call to a candidate.
Real telephony integration comes later — this proves the module works.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def trigger_call(candidate_phone: str, questions: list) -> dict:
    """Queue an outbound screening call."""
    logger.info(f"Triggering screening call to {candidate_phone}")

    return {
        "call_status": "queued",
        "questions_to_ask": questions,
    }