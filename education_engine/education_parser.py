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
SEPARATOR_PATTERN = re.compile(r"\s*[—|]\s*")


def _extract_year(text):
    match = YEAR_PATTERN.search(text)
    if not match:
        return None, text
    year = int(match.group(0))
    # drop the year and any surrounding parentheses from the text
    cleaned = text[:match.start()] + text[match.end():]
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = cleaned.strip()
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


def parse_education_section(lines):
    results = []
    for line in lines or []:
        parsed = parse_education_line(line)
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