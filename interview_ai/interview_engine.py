"""
Handles the AI video interview session.
Real video/speech analysis comes later.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def run_interview(session_id: str, video_url: str) -> dict:
    """Start processing an interview session."""
    logger.info(f"Starting interview session {session_id}")

    return {
        "session_id": session_id,
        "status": "pending_analysis",
    }