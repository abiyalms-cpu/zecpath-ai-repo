"""
Pulls structured facts out of cleaned job description text:
role, required experience, education preference, and skills.
"""

import re

from parsers.jd_synonyms import ROLE_LOOKUP, SKILL_LOOKUP

TITLE_LABEL = re.compile(r"^(?:job title|title|position|role)\s*:\s*(.+)$", re.IGNORECASE)

EXPERIENCE_PATTERN = re.compile(
    r"(?P<plus>\d+)\s*\+\s*years"
    r"|(?P<lo>\d+)\s*(?:-|to)\s*(?P<hi>\d+)\s*years"
    r"|(?:minimum|at least)\s*(?P<min>\d+)\s*years",
    re.IGNORECASE,
)

EDUCATION_KEYWORDS = [
    "bachelor's degree", "bachelor degree", "b.tech", "b.e", "bba",
    "any graduate", "master's degree", "mba", "m.com", "degree in",
]


def _contains_word(text: str, phrase: str) -> bool:
    """Whole-word/phrase match, so "MBA" doesn't match inside "Mumbai"."""
    return re.search(r"\b" + re.escape(phrase) + r"\b", text) is not None


def extract_role(text: str) -> str | None:
    """Find the role name and return its canonical form."""
    for line in text.splitlines()[:3]:
        match = TITLE_LABEL.match(line.strip())
        if match:
            return normalize_role(match.group(1))

    first_line = text.splitlines()[0].strip()
    if " - " in first_line:
        candidate = first_line.split(" - ")[0]
        normalized = normalize_role(candidate)
        if normalized:
            return normalized

    return normalize_role(text)


def normalize_role(fragment: str) -> str | None:
    """Match a chunk of text against known role variants, longest first."""
    lowered = fragment.lower()
    for variant in sorted(ROLE_LOOKUP, key=len, reverse=True):
        if _contains_word(lowered, variant):
            return ROLE_LOOKUP[variant]
    return None


def extract_experience(text: str):
    """Return the first (earliest, i.e. primary) years-of-experience requirement."""
    match = EXPERIENCE_PATTERN.search(text)
    if not match:
        return None

    if match.group("plus"):
        return {"min_years": int(match.group("plus")), "max_years": None}
    if match.group("lo"):
        return {"min_years": int(match.group("lo")), "max_years": int(match.group("hi"))}
    if match.group("min"):
        return {"min_years": int(match.group("min")), "max_years": None}
    return None


def extract_education(text: str):
    """Find the line mentioning education and return its raw text + level."""
    for line in text.splitlines():
        lowered = line.lower()
        if any(_contains_word(lowered, keyword) for keyword in EDUCATION_KEYWORDS):
            level = "Master's" if any(_contains_word(lowered, k) for k in ("mba", "master's degree", "m.com")) else "Bachelor's"
            return {"raw_text": line.strip(), "level": level}
    return None


def extract_skills(text: str) -> list:
    """Find every known skill mentioned, normalized, in first-seen order."""
    lowered = text.lower()
    found = []
    for variant in sorted(SKILL_LOOKUP, key=len, reverse=True):
        if _contains_word(lowered, variant) and SKILL_LOOKUP[variant] not in found:
            found.append(SKILL_LOOKUP[variant])
    return found