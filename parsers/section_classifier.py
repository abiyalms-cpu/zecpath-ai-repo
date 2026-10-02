"""
Splits cleaned resume text into labeled sections.

Two strategies, tried in order:
1. Heading-based (rule-based): split on the standard headings Day 5's
   cleaner already produces. Fast and reliable whenever headings exist.
2. Content-based (heuristic): when a resume has too few headings to split
   on reliably, classify each line by what it looks like instead of what
   it's labeled as.
"""

import re

KNOWN_HEADINGS = {"SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION", "CERTIFICATIONS", "PROJECTS"}

# Minimum number of real headings found before we trust heading-based
# splitting. Below this, a resume is treated as "missing headings".
MIN_HEADINGS_TO_TRUST = 2

DATE_RANGE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}\b"
    r".{0,15}(?:–|-|to)\s*(?:present|\d{4}|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))",
    re.IGNORECASE,
)
DEGREE_KEYWORDS = re.compile(
    r"\b(b\.?tech|b\.?e|b\.?sc|b\.?com|b\.?a|b\.?des|m\.?tech|m\.?sc|m\.?com|m\.?des|mba|"
    r"university|college|institute|diploma)\b",
    re.IGNORECASE,
)
CERT_KEYWORDS = re.compile(r"\b(certified|certificate|certification)\b", re.IGNORECASE)
SKILLS_LIST_PATTERN = re.compile(r"^[\w][\w .+#/&()-]*(,\s*[\w][\w .+#/&()-]*){3,}\.?$")


def split_by_headings(text: str) -> dict:
    """Split text into {heading: [lines]} wherever standard headings appear."""
    sections = {}
    current = "HEADER"
    for line in text.splitlines():
        if line in KNOWN_HEADINGS:
            current = line
            sections.setdefault(current, [])
            continue
        if line.strip():
            sections.setdefault(current, []).append(line)
    return sections


def count_real_headings(sections: dict) -> int:
    return len([h for h in sections if h in KNOWN_HEADINGS])


def classify_line_by_content(line: str) -> str:
    """Guess a section for one line, based only on what it looks like."""
    if CERT_KEYWORDS.search(line):
        return "CERTIFICATIONS"
    if DEGREE_KEYWORDS.search(line):
        return "EDUCATION"
    if DATE_RANGE.search(line):
        return "EXPERIENCE"
    if SKILLS_LIST_PATTERN.match(line.strip()):
        return "SKILLS"
    return "UNCLASSIFIED"


def classify_by_content(text: str) -> dict:
    """Fallback for resumes with no (or almost no) headings.

    A bullet line under a job entry (e.g. "- Led usability testing...")
    rarely has its own date or keyword signal, so on its own it would
    always land in UNCLASSIFIED. Instead, a bullet inherits the label of
    the most recent confidently-classified line above it.
    """
    sections = {}
    lines = [l for l in text.splitlines() if l.strip()]

    header, body = lines[:2], lines[2:]
    sections["HEADER"] = header

    last_confident_label = None
    for line in body:
        if line.strip().startswith("-") and last_confident_label in ("EXPERIENCE", "PROJECTS"):
            label = last_confident_label
        else:
            label = classify_line_by_content(line)
            if label != "UNCLASSIFIED":
                last_confident_label = label

        sections.setdefault(label, []).append(line)

    return sections


def classify_sections(text: str) -> dict:
    """Return {"method": "heading" | "heuristic", "sections": {...}}."""
    heading_sections = split_by_headings(text)

    if count_real_headings(heading_sections) >= MIN_HEADINGS_TO_TRUST:
        return {"method": "heading", "sections": heading_sections}

    return {"method": "heuristic", "sections": classify_by_content(text)}