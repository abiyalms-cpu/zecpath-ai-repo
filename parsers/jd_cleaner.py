"""
Cleans and normalizes raw JD text: bullets, spacing, and section headings.
"""

import re

JD_HEADING_ALIASES = {
    "REQUIREMENTS": ["requirements", "required skills", "must have", "what you'll need",
                     "what we're looking for", "qualifications"],
    "RESPONSIBILITIES": ["responsibilities", "key responsibilities", "what you'll do",
                         "duties", "you will"],
    "NICE TO HAVE": ["nice to have", "good to have", "bonus", "preferred"],
}
ALIAS_TO_STANDARD = {
    alias: standard
    for standard, aliases in JD_HEADING_ALIASES.items()
    for alias in aliases
}


def normalize_heading(line: str):
    """Return either a standalone heading, or (heading, rest) for an inline one."""
    stripped = line.strip()

    # Whole line is just a heading, e.g. "Requirements" or "Requirements:"
    key = stripped.rstrip(":").strip().lower()
    if key in ALIAS_TO_STANDARD:
        return ALIAS_TO_STANDARD[key], None

    # Heading and content share one line, e.g. "Bonus: Google Ads certification"
    if ":" in stripped:
        label, rest = stripped.split(":", 1)
        label_key = label.strip().lower()
        if label_key in ALIAS_TO_STANDARD and rest.strip():
            return ALIAS_TO_STANDARD[label_key], rest.strip()

    return None, stripped


def clean_jd_text(text: str) -> str:
    """Return a cleaned version of raw JD text."""
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"^\s*[●•▪■◦○▫◆*]\s+", "- ", line)
        line = re.sub(r"[ \t]+", " ", line).strip()

        heading, rest = normalize_heading(line)
        if heading and rest:
            lines.append(heading)
            lines.append("- " + rest)
        elif heading:
            lines.append(heading)
        else:
            lines.append(rest)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()