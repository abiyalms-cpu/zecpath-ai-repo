"""
Skill extraction engine.

Takes a block of resume text and finds which skills from the master
dictionary are actually present in it, and how each one was found:
exact name, a known synonym, a known spelling variant, inferred from a
stack name (MERN -> Mongo/Express/React/Node), or a fuzzy near-match for
a spelling variation we never thought to list.
"""

import re
import difflib

from skills_engine.skill_dictionary import SKILL_CATALOG, SKILL_STACKS

# Confidence by how the skill was found.
CONFIDENCE = {
    "exact_canonical": 0.97,
    "exact_synonym": 0.93,
    "spelling_variant": 0.85,
    "stack_inferred": 0.75,
    "fuzzy_match": 0.65,
}

FUZZY_CUTOFF = 0.84  # how close a word has to be to count as a fuzzy match


def _build_lookup():
    """
    Build two lookups from SKILL_CATALOG:
      - exact_lookup: lowercased canonical name/synonym -> (canonical, match_type)
      - variant_lookup: lowercased spelling variant -> canonical
    """
    exact_lookup = {}
    variant_lookup = {}

    for canonical, info in SKILL_CATALOG.items():
        exact_lookup[canonical.lower()] = (canonical, "exact_canonical")
        for synonym in info["synonyms"]:
            exact_lookup[synonym.lower()] = (canonical, "exact_synonym")
        for variant in info["spelling_variants"]:
            variant_lookup[variant.lower()] = canonical

    return exact_lookup, variant_lookup


EXACT_LOOKUP, VARIANT_LOOKUP = _build_lookup()

# All known surface forms, longest first, so a multi-word skill is checked
# before a shorter one that happens to be a substring of it.
ALL_TERMS = sorted(
    list(EXACT_LOOKUP.keys()) + list(VARIANT_LOOKUP.keys()),
    key=len,
    reverse=True,
)


def _contains_word(text, phrase):
    """Word-boundary-safe 'is this phrase present' check — same fix as
    Day 6's Java-in-JavaScript bug. A plain substring check isn't safe here
    either (e.g. 'R' inside 'React')."""
    pattern = r"\b" + re.escape(phrase) + r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _find_direct_matches(text):
    """
    Scan text for exact canonical/synonym/spelling-variant hits.

    Longer terms are checked first (ALL_TERMS is sorted that way). Once a
    term matches, its exact character span is "claimed" so a shorter term
    that happens to sit inside it — e.g. plain "CSS" inside "Tailwind CSS" —
    isn't counted a second time as its own separate skill.
    """
    matches = {}
    consumed_spans = []

    def overlaps_consumed(start, end):
        return any(s < end and e > start for s, e in consumed_spans)

    for term in ALL_TERMS:
        pattern = r"\b" + re.escape(term) + r"\b"
        matched_here = False
        for m in re.finditer(pattern, text, re.IGNORECASE):
            if overlaps_consumed(m.start(), m.end()):
                continue
            matched_here = True
            consumed_spans.append((m.start(), m.end()))

        if not matched_here:
            continue

        if term in EXACT_LOOKUP:
            canonical, match_type = EXACT_LOOKUP[term]
        else:
            canonical, match_type = VARIANT_LOOKUP[term], "spelling_variant"

        existing = matches.get(canonical)
        if existing is None or CONFIDENCE[match_type] > CONFIDENCE[existing["match_type"]]:
            matches[canonical] = {"match_type": match_type, "matched_text": term}

    return matches


def _find_stack_matches(text):
    """Look for stack names (MERN, MEAN, LAMP) and expand them into their
    component skills."""
    matches = {}
    for stack_name, components in SKILL_STACKS.items():
        if _contains_word(text, stack_name):
            for canonical in components:
                matches.setdefault(
                    canonical, {"match_type": "stack_inferred", "matched_text": stack_name}
                )
    return matches


FUZZY_CUTOFF = 0.80  # how close a word has to be to count as a fuzzy match

# Suffixes that turn a skill name into an ordinary inflected English word
# (e.g. "react" + "ed" = "reacted") rather than a misspelling of it.
INFLECTION_SUFFIXES = ("ed", "ing", "s", "es", "er", "ers")


def _is_inflection_not_typo(word, candidate):
    """True if `word` is just `candidate` with a normal English ending
    glued on — i.e. it's grammar, not a misspelling, and should NOT be
    treated as a fuzzy skill match."""
    for suffix in INFLECTION_SUFFIXES:
        if word == candidate + suffix:
            return True
    return False

def _find_fuzzy_matches(text, already_found):
    """
    Catch spelling variations we didn't think to list explicitly. Checks
    each word in the text against every known canonical/synonym name
    using difflib, and only accepts a hit if it's close enough, starts
    with the same letter (a real typo almost never changes the first
    letter — "Sigma" vs "Figma" do, which is why that false match needed
    this guard), not already found some other way, and not just an
    inflected real word (e.g. "reacted" is not a typo of "React").
    """
    matches = {}
    words = re.findall(r"[A-Za-z][A-Za-z.+#]*", text)
    candidates = list(EXACT_LOOKUP.keys())

    for word in set(w.lower().rstrip(".") for w in words):
        if len(word) < 4:
            continue  # too short to fuzzy-match safely
        close = difflib.get_close_matches(word, candidates, n=1, cutoff=FUZZY_CUTOFF)
        if not close or close[0] == word:
            continue  # no close hit, or an exact hit already handled above

        candidate = close[0]
        if word[0] != candidate[0]:
            continue  # different first letter: not how real typos behave
        if _is_inflection_not_typo(word, candidate):
            continue

        canonical, _ = EXACT_LOOKUP[candidate]
        if canonical in already_found or canonical in matches:
            continue
        matches[canonical] = {"match_type": "fuzzy_match", "matched_text": word}

    return matches

def find_skills_in_text(text):
    """
    Find every skill in a block of text. Returns:
        {canonical_name: {"match_type": ..., "matched_text": ...}, ...}
    """
    if not text:
        return {}

    direct = _find_direct_matches(text)
    stacks = _find_stack_matches(text)
    fuzzy = _find_fuzzy_matches(text, already_found=set(direct) | set(stacks))

    combined = dict(direct)
    for canonical, info in stacks.items():
        combined.setdefault(canonical, info)
    for canonical, info in fuzzy.items():
        combined.setdefault(canonical, info)

    return combined