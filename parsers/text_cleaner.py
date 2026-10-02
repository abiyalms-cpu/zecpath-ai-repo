"""
Cleans raw resume text: removes noise, standardises bullets, spacing,
section headings and capitalisation.
"""

import re

from utils.logger import get_logger

logger = get_logger(__name__)

# Different resumes name the same section differently. Map them to one name.
HEADING_ALIASES = {
    "SUMMARY": ["summary", "professional summary", "profile", "objective",
                "career objective", "about me"],
    "SKILLS": ["skills", "technical skills", "key skills", "core skills",
               "core competencies"],
    "EXPERIENCE": ["experience", "work experience", "professional experience",
                   "employment history", "work history"],
    "EDUCATION": ["education", "academic background",
                  "educational qualifications", "qualifications", "academics"],
    "CERTIFICATIONS": ["certifications", "certificates",
                       "licenses & certifications", "courses & certifications"],
    "PROJECTS": ["projects", "personal projects", "key projects", "academic projects", "project experience"],                   
}
ALIAS_TO_STANDARD = {
    alias: standard
    for standard, aliases in HEADING_ALIASES.items()
    for alias in aliases
}


def normalize_heading(line: str) -> str:
    """Turn 'Work Experience:' into 'EXPERIENCE' (and so on)."""
    key = line.strip().rstrip(":").strip().lower()
    return ALIAS_TO_STANDARD.get(key, line)


def fix_shouting(line: str) -> str:
    """Turn 'ROHAN MEHTA' into 'Rohan Mehta'. Headings are left alone."""
    if line.isupper() and len(line.split()) > 1 and line not in HEADING_ALIASES:
        return line.title()
    return line


def clean_text(text: str) -> str:
    """Return a cleaned version of raw extracted resume text."""
    # 1. Remove invisible and control characters
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    lines = []
    for line in text.split("\n"):
        # 2. Turn every bullet style into a plain "- "
        line = re.sub(r"^\s*[●•▪■◦○▫◆*–-]\s+", "- ", line)
        # 3. Collapse repeated spaces and trim the line
        line = re.sub(r"[ \t]+", " ", line).strip()
        # 4. Standard section headings and sensible capitalisation
        line = normalize_heading(line)
        line = fix_shouting(line)
        lines.append(line)

    text = "\n".join(lines)

    # 5. Never more than one blank line in a row
    text = re.sub(r"\n{3,}", "\n\n", text)

    logger.info("Cleaned text")
    return text.strip()