"""
Extracts job entries (company, title, start date, end date) out of a
resume's EXPERIENCE section lines (the output of Day 8's section tagger).

Only lines that actually contain a date range are treated as job-header
lines; bullet points describing that job ("- Built ...") have no date of
their own and are skipped at this stage — the same approach Day 8 used
before it taught bullets to inherit a label from the job entry above.
"""

import re

MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

MONTH_TOKEN = r"[A-Za-z]+\.?\s+\d{4}"

DATE_RANGE_PATTERN = re.compile(
    r"(?P<start>" + MONTH_TOKEN + r")"
    r"\s*(?:\u2013|-|\u2014|to)\s*"
    r"(?P<end>present|current|" + MONTH_TOKEN + r")",
    re.IGNORECASE,
)

SINGLE_DATE_PATTERN = re.compile(
    r"(?P<month>[A-Za-z]+)\.?\s+(?P<year>\d{4})", re.IGNORECASE
)


def _parse_single_date(text):
    """'March 2021' -> (3, 2021). Returns None if the month name isn't
    one we recognize."""
    match = SINGLE_DATE_PATTERN.search(text)
    if not match:
        return None
    month_name = match.group("month").lower().rstrip(".")
    month_num = MONTH_NAMES.get(month_name)
    if month_num is None:
        return None
    return month_num, int(match.group("year"))


def _clean_header(header):
    """Strip the leftover separators/connector words between a job title
    and the date range once the date range itself has been cut off, e.g.
    'Frontend Developer, Brightloop Software \u2014' or
    'Operations Lead at Swiftline Logistics, Bengaluru, from'."""
    header = header.strip()
    header = re.sub(r"[\s,\-\u2013\u2014]+$", "", header)
    header = re.sub(r"\bfrom$", "", header, flags=re.IGNORECASE).strip()
    header = re.sub(r"[\s,\-\u2013\u2014]+$", "", header)
    return header.strip()


def _split_title_and_company(header):
    """
    Handles the two header shapes seen in real resumes:
      "Title, Company"            -> split on the first comma
      "Title at Company, Place"   -> split on ' at ', then drop any
                                      trailing ', Place' from the company
    Returns (title, company). Either can be None if the header doesn't
    confidently split into both parts.
    """
    at_match = re.search(r"\bat\b", header, re.IGNORECASE)
    if at_match:
        title = header[:at_match.start()].strip().rstrip(",")
        rest = header[at_match.end():].strip()
        company = rest.split(",")[0].strip()
        return (title or None), (company or None)

    if "," in header:
        title, company = header.split(",", 1)
        return title.strip() or None, company.strip() or None

    return None, None


def parse_experience_line(line):
    """
    Returns a structured job entry if `line` contains a recognizable date
    range, otherwise None (e.g. a bullet point with no date of its own).
    """
    match = DATE_RANGE_PATTERN.search(line)
    if not match:
        return None

    header = _clean_header(line[:match.start()])
    title, company = _split_title_and_company(header)

    start = _parse_single_date(match.group("start"))
    if start is None:
        return None  # couldn't make sense of the start date, don't guess

    end_text = match.group("end").lower()
    if end_text in ("present", "current"):
        end = None
        is_current = True
    else:
        end = _parse_single_date(match.group("end"))
        is_current = False

    return {
        "raw_line": line.strip(),
        "title": title,
        "company": company,
        "start_month": start[0],
        "start_year": start[1],
        "end_month": end[0] if end else None,
        "end_year": end[1] if end else None,
        "is_current": is_current,
    }


def parse_experience_section(lines):
    """
    lines: the list of strings under the EXPERIENCE key of a Day 8
    *_sections.json file. Bullet lines without their own date are simply
    skipped here; only lines that look like a job header are returned.
    """
    jobs = []
    for line in lines:
        job = parse_experience_line(line)
        if job is not None:
            jobs.append(job)
    return jobs