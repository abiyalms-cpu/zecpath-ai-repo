"""
Turns a raw resume file into structured data the ATS engine can score.
This is a placeholder for now — real PDF/DOCX parsing comes later.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def parse_resume(file_path: str) -> dict:
    """Extract basic fields from a resume file."""
    logger.info(f"Parsing resume: {file_path}")

    return {
        "file_path": file_path,
        "skills": [],
        "experience_years": 0,
    }