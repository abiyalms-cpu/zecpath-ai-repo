import re

DEGREE_CATALOG = {
    "B.Tech": ["B.Tech", "BTech", "Bachelor of Technology"],
    "B.E.": ["B.E.", "BE", "Bachelor of Engineering"],
    "B.Sc": ["B.Sc", "BSc", "Bachelor of Science"],
    "B.A.": ["B.A.", "BA", "Bachelor of Arts"],
    "B.Com": ["B.Com", "BCom", "Bachelor of Commerce"],
    "B.Des": ["B.Des", "BDes", "Bachelor of Design"],
    "B.Ed": ["B.Ed", "BEd", "Bachelor of Education"],
    "BBA": ["BBA"],
    "MBA": ["MBA"],
    "M.Tech": ["M.Tech", "MTech", "Master of Technology"],
    "M.Sc": ["M.Sc", "MSc", "Master of Science"],
    "M.A.": ["M.A.", "MA", "Master of Arts"],
    "M.Com": ["M.Com", "MCom", "Master of Commerce"],
    "PhD": ["PhD", "Ph.D", "Doctor of Philosophy"],
    "Diploma": ["Diploma"],
}

# Flat lookup: variant text (lowercase) -> canonical degree name.
# Sorted longest-variant-first so "B.Tech" is tried before a shorter clash.
_DEGREE_LOOKUP = sorted(
    ((variant.lower(), canonical) for canonical, variants in DEGREE_CATALOG.items() for variant in variants),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

YEAR_PATTERN = re.compile(r"(19|20)\d{2}")
# "—"/"|" are the structured-line separators (e.g. "B.Tech — IIT Delhi — 2020").
# The word "from" is just as unambiguous a marker in a plain sentence
# ("B.Com from Madras University, completed in 2018") -- unlike a bare comma,
# which is too ambiguous to split on (see test_prose_style_line_is_skipped).
SEPARATOR_PATTERN = re.compile(r"\s*[—|]\s*|\s+from\s+", re.IGNORECASE)

# Trailing filler a prose sentence leaves behind right before the year, once
# the year itself has been stripped out -- e.g. "...University, completed in"
# left over from "...University, completed in 2018."
TRAILING_FILLER_PATTERN = re.compile(
    r",?\s*(completed|graduated|passed(?:\s+out)?)\s+in\s*$", re.IGNORECASE
)


def _extract_year(text):
    match = YEAR_PATTERN.search(text)
    if not match:
        return None, text
    year = int(match.group(0))
    # drop the year and any surrounding parentheses from the text
    cleaned = text[:match.start()] + text[match.end():]
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = cleaned.strip()
    cleaned = TRAILING_FILLER_PATTERN.sub("", cleaned)  # "...University, completed in" -> "...University"
    cleaned = cleaned.rstrip(" |—,")  # drop a dangling separator left behind (e.g. "A | B | 2020")
    return year, cleaned.strip()


def _split_degree_and_field(head):
    head = head.strip()
    if "," in head:
        degree_raw, field = head.split(",", 1)
        return degree_raw.strip(), field.strip()
     # no comma: see if a known degree abbreviation is a prefix, rest is the field
    for variant_lower, canonical in _DEGREE_LOOKUP:
        if head.lower().startswith(variant_lower):
            remainder = head[len(variant_lower):].strip()
            remainder = re.sub(r"^in\s+", "", remainder, flags=re.IGNORECASE)  # "Diploma in X" -> field "X"
            return head[:len(variant_lower)].strip(), (remainder or None)
    return head, None  


def _normalize_degree(degree_raw):
    degree_lower = degree_raw.strip().lower().rstrip(".")
    for variant_lower, canonical in _DEGREE_LOOKUP:
        if degree_lower == variant_lower.rstrip("."):
            return canonical
    return degree_raw.strip()


def parse_education_line(line):
    raw_line = line.strip()
    text = raw_line.rstrip(".")

    year, text = _extract_year(text)
    if year is None:
        return None  # no graduation year found — not confident this is a parseable entry

    if not SEPARATOR_PATTERN.search(text):
        return None  # no institution separator — can't split degree from institution reliably

    head, institution = SEPARATOR_PATTERN.split(text, maxsplit=1)
    degree_raw, field = _split_degree_and_field(head)

    return {
        "raw_line": raw_line,
        "degree_raw": degree_raw,
        "degree_normalized": _normalize_degree(degree_raw),
        "field_of_study": field,
        "institution": institution.strip() or None,
        "graduation_year": year,
    }


# Splits "...2018. Diploma in..." into two sentences, only ever used below when a
# single section entry turns out to hold more than one degree (see parse_education_section).
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=\.)\s+(?=[A-Z])")


def parse_education_section(lines):
    results = []
    for line in lines or []:
        if not line:
            continue
        candidates = [line]
        if len(YEAR_PATTERN.findall(line)) > 1:
            # A no-headings resume's section classifier sometimes joins several
            # degree sentences into one array entry (two years in one string is
            # the tell). Splitting on sentence boundaries only in that case keeps
            # every ordinary one-degree-per-line resume completely untouched.
            candidates = _SENTENCE_SPLIT_PATTERN.split(line.strip())
        for candidate in candidates:
            parsed = parse_education_line(candidate)
            if parsed is not None:
                results.append(parsed)
    return results


BULLET_PREFIX_PATTERN = re.compile(r"^[\-\u2022]\s*")


def parse_certification_line(line):
    raw_line = line.strip()
    text = BULLET_PREFIX_PATTERN.sub("", raw_line).rstrip(".")
    year, text = _extract_year(text)
    name = text.strip(" -")
    if not name:
        return None
    return {
        "raw_line": raw_line,
        "certification_name": name,
        "year": year,
    }


def parse_certification_section(lines):
    results = []
    for line in lines or []:
        parsed = parse_certification_line(line)
        if parsed is not None:
            results.append(parsed)
    return results