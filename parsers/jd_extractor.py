"""
Pulls structured facts out of cleaned job description text:
role, location, department, experience, education, skills and responsibilities.
"""

import re

from parsers.jd_synonyms import ROLE_LOOKUP, SKILL_CATEGORIES, SKILL_LOOKUP

TITLE_LABEL = re.compile(r"^(?:job title|title|position|role)\s*:\s*(.+)$", re.IGNORECASE)
LOCATION_LABEL = re.compile(r"^location\s*:\s*(.+)$", re.IGNORECASE)
DEPARTMENT_LABEL = re.compile(r"^department\s*:\s*(.+)$", re.IGNORECASE)
EMPLOYMENT_TYPE_PATTERN = re.compile(r"\b(full-time|part-time|contract|internship)\b", re.IGNORECASE)
SALARY_PATTERN = re.compile(r"(?:₹|\brs\.?|\binr)\s*\d[\d,]*|\b\d+(?:\.\d+)?\s*lpa\b", re.IGNORECASE)

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


def extract_location(text: str) -> str | None:
    """Find the location, from a 'Location:' label or a 'Title - Location' first line."""
    for line in text.splitlines()[:5]:
        match = LOCATION_LABEL.match(line.strip())
        if match:
            return match.group(1).strip()

    first_line = text.splitlines()[0].strip()
    if " - " in first_line:
        return first_line.split(" - ", 1)[1].strip()
    return None


def extract_department(text: str) -> str | None:
    """Find the department, from a 'Department:' label. Not every JD has one."""
    for line in text.splitlines()[:6]:
        match = DEPARTMENT_LABEL.match(line.strip())
        if match:
            return match.group(1).strip()
    return None


def extract_employment_type(text: str) -> str | None:
    """Find Full-time / Part-time / Contract / Internship, if stated at all."""
    match = EMPLOYMENT_TYPE_PATTERN.search(text)
    return match.group(1).capitalize() if match else None


def extract_salary_range(text: str):
    """Find a salary figure, if the JD states one at all."""
    match = SALARY_PATTERN.search(text)
    return {"raw_text": match.group(0)} if match else None


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


def extract_education(text: str) -> list:
    """Find the education requirement and return it as a structured list.

    Only the first / primary degree mention is structured into an entry.
    When a JD lists several acceptable degrees on one line, the rest stay
    visible in normalized_text but are not split into separate entries.
    """
    for line in text.splitlines():
        lowered = line.lower()
        if any(_contains_word(lowered, keyword) for keyword in EDUCATION_KEYWORDS):
            level = "Master's" if any(_contains_word(lowered, k) for k in ("mba", "master's degree", "m.com")) else "Bachelor's"
            field_match = re.search(r"\bin ([^,.]+)", line, re.IGNORECASE)
            field = field_match.group(1).strip() if field_match else None
            return [{"degree": level, "field_of_study": field, "mandatory": True}]
    return []


def extract_skills(text: str) -> list:
    """Find every known skill mentioned, as objects with category and mandatory.

    'mandatory' is True if the skill appears in the REQUIREMENTS section,
    False if it only appears under NICE TO HAVE.
    """
    required_zone, optional_zone = _split_into_zones(text)

    found = {}
    for zone_text, mandatory in ((required_zone, True), (optional_zone, False)):
        lowered = zone_text.lower()
        for variant in sorted(SKILL_LOOKUP, key=len, reverse=True):
            if _contains_word(lowered, variant):
                canonical = SKILL_LOOKUP[variant]
                found[canonical] = found.get(canonical, mandatory) or mandatory

    return [
        {"name": name, "category": SKILL_CATEGORIES.get(name, "domain"), "mandatory": mandatory}
        for name, mandatory in found.items()
    ]


def extract_responsibilities(text: str) -> list:
    """Return each bullet under the RESPONSIBILITIES heading."""
    lines = text.splitlines()
    if "RESPONSIBILITIES" not in lines:
        return []

    start = lines.index("RESPONSIBILITIES") + 1
    responsibilities = []
    for line in lines[start:]:
        if line.isupper():
            break
        if line.startswith("- "):
            responsibilities.append(line[2:].strip())
    return responsibilities


def _split_into_zones(text: str):
    """Split cleaned text into (requirements-zone, nice-to-have-zone)."""
    lines = text.splitlines()
    required, optional = [], []
    current = required

    for line in lines:
        if line == "REQUIREMENTS":
            current = required
            continue
        if line == "NICE TO HAVE":
            current = optional
            continue
        if line.isupper() and line not in ("REQUIREMENTS", "NICE TO HAVE"):
            current = required
            continue
        current.append(line)

    return "\n".join(required), "\n".join(optional)