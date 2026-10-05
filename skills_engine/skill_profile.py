"""
Builds one structured "skill profile" for a resume, using the section-tagged
output from Day 8 (section_classifier / section_tagger) plus the matching
engine in skill_extractor.py.

A skill mentioned in the SKILLS section itself is stronger evidence than the
same word turning up once in a paragraph of EXPERIENCE text, so each section
carries its own weight. The same skill found in several sections keeps its
single best (highest-confidence) score, but we remember every section it
showed up in — that's the dedup/normalize step the brief asks for.
"""

from skills_engine.skill_extractor import find_skills_in_text, CONFIDENCE
from skills_engine.skill_dictionary import SKILL_CATALOG

# How much we trust a skill mention, depending on which resume section it
# came from. SKILLS is the most direct declaration; a mention only in
# HEADER contact-info text is the weakest.
SECTION_WEIGHT = {
    "SKILLS": 1.00,
    "PROJECTS": 0.95,
    "EXPERIENCE": 0.90,
    "CERTIFICATIONS": 0.90,
    "EDUCATION": 0.85,
    "SUMMARY": 0.85,
    "UNCLASSIFIED": 0.80,
    "HEADER": 0.75,
}

DEFAULT_SECTION_WEIGHT = 0.80  # fallback for any section name not listed above


def build_skill_profile(sections):
    """
    sections: the "sections" dict from a Day 8 *_sections.json file, e.g.
        {"SKILLS": ["JavaScript, React, ..."], "EXPERIENCE": [...], ...}
    Each value is a list of lines (that's how section_tagger saves them).

    Returns a list of skill entries, most confident first:
        [{"skill": "React", "category": "technical", "confidence": 0.97,
          "match_type": "exact_canonical", "matched_text": "react",
          "found_in": ["SKILLS", "PROJECTS"]}, ...]
    """
    found = {}  # canonical -> best entry so far

    for section_name, lines in sections.items():
        section_text = " ".join(lines)
        weight = SECTION_WEIGHT.get(section_name, DEFAULT_SECTION_WEIGHT)
        section_matches = find_skills_in_text(section_text)

        for canonical, info in section_matches.items():
            score = round(CONFIDENCE[info["match_type"]] * weight, 3)
            entry = found.get(canonical)

            if entry is None:
                found[canonical] = {
                    "skill": canonical,
                    "category": SKILL_CATALOG[canonical]["category"],
                    "confidence": score,
                    "match_type": info["match_type"],
                    "matched_text": info["matched_text"],
                    "found_in": [section_name],
                }
            else:
                entry["found_in"].append(section_name)
                if score > entry["confidence"]:
                    entry["confidence"] = score
                    entry["match_type"] = info["match_type"]
                    entry["matched_text"] = info["matched_text"]

    profile = list(found.values())
    profile.sort(key=lambda e: e["confidence"], reverse=True)
    return profile