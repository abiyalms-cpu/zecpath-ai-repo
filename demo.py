"""
Zecpath AI — Day 20 live demo.

Runs the full real pipeline on the full real candidate pool (so rankings are
genuine, not staged against an artificially small pool), then prints a clean,
readable report for a curated set of 8 candidates chosen to show the system's
range: a strong senior match, a fresher, a noisy/edge-case resume, a scanned
(unreadable) resume, and a couple of borderline/partial-match cases -- against
three JDs, one from each weight profile (technical / education_heavy / default).

Run from the project root:  python demo.py
"""

import json
from pathlib import Path

from parsers.extractor import extract_folder
from parsers.section_tagger import tag_folder as section_tag_folder
from parsers.jd_parser import parse_folder as parse_jd_folder
from skills_engine.skill_tagger import tag_folder as skill_tag_folder
from experience_engine.experience_tagger import tag_folder as experience_tag_folder
from education_engine.education_tagger import tag_folder as education_tag_folder
from semantic_engine.matching_report import tag_folder as semantic_tag_folder
from scoring_engine.candidate_score_generator import score_all_resumes
from ranking_engine.ranking import rank_candidates_for_jd
from ranking_engine.shortlisting import apply_shortlisting

BASE = "demo_run"

# One JD per weight profile, so the demo shows all three in action.
DEMO_JDS = [
    ("sde_ii", "Senior Development Engineer II", "technical"),
    ("financial_analyst", "Financial Analyst", "education_heavy"),
    ("customer_support", "Customer Support Representative", "default"),
]

# A deliberately varied set of real candidates from data/resumes:
DEMO_CANDIDATES = {
    "karthik_subramaniam.docx": "Senior profile, strong real match for Financial Analyst",
    "kunal_bhatia_fresher_docx.docx": "Fresher (software engineering intern)",
    "no_headings_vikram.docx": "No section headings, prose-style education (Day 18 fix)",
    "nikhil_verma_two_column.pdf": "Two-column PDF layout (parsing edge case)",
    "zoya_khan_scanned.pdf": "Scanned/unreadable PDF (failure-handling case)",
    "meera_iyer_table.docx": "Data Analyst, table-based resume (borderline skill-overlap case)",
    "abiyal_ms_fresher_docx.docx": "Fresher data scientist, no job history (open backlog case)",
    "rohan_mehta.docx": "General mid-career profile",
}


def run_pipeline():
    extract_folder("data/resumes", f"{BASE}/extracted")
    section_tag_folder(f"{BASE}/extracted", f"{BASE}/segmented")
    parse_jd_folder("data/job_descriptions", f"{BASE}/parsed_jds")
    skill_tag_folder(f"{BASE}/segmented", f"{BASE}/skills")
    experience_tag_folder(f"{BASE}/segmented", f"{BASE}/experience")
    education_tag_folder(f"{BASE}/segmented", f"{BASE}/education")
    semantic_tag_folder(f"{BASE}/segmented", f"{BASE}/parsed_jds", f"{BASE}/semantic_matches")
    score_all_resumes(
        f"{BASE}/segmented", f"{BASE}/skills", f"{BASE}/experience",
        f"{BASE}/education", f"{BASE}/semantic_matches", f"{BASE}/parsed_jds",
        f"{BASE}/candidate_scores",
    )


def one_line_why(breakdown):
    parts = []
    for b in breakdown:
        if b["available"]:
            parts.append(f"{b['component']}={b['raw_score']}")
        else:
            parts.append(f"{b['component']}=n/a")
    return ", ".join(parts)


def print_report():
    total_pool = len(list(Path("data/resumes").glob("*")))
    print("=" * 78)
    print("  ZECPATH AI — LIVE DEMO")
    print("=" * 78)
    print(f"Full candidate pool: {total_pool} resumes (PDF + DOCX, 33 total files)")
    print(f"Demo highlights {len(DEMO_CANDIDATES)} of them against {len(DEMO_JDS)} JDs")
    print(f"(real rank shown is each candidate's position across the FULL pool, not just this demo set)\n")

    for jd_file, jd_title, profile in DEMO_JDS:
        ranked = rank_candidates_for_jd(f"{BASE}/candidate_scores", jd_file)
        zoned = apply_shortlisting(ranked)

        print("-" * 78)
        print(f"JD: {jd_title}  ({jd_file})   [weight profile: {profile}]")
        print("-" * 78)
        print(f"{'Rank':<6}{'Candidate':<32}{'Score':<8}{'Zone':<12}{'Note'}")

        shown = [c for c in zoned if c["resume"] in DEMO_CANDIDATES]
        shown.sort(key=lambda c: c["rank"])
        for c in shown:
            note = DEMO_CANDIDATES[c["resume"]]
            print(f"{c['rank']:<6}{c['resume']:<32}{c['final_score']:<8}{c['zone']:<12}{note}")
        print()
        for c in shown:
            print(f"  {c['resume']}: {one_line_why(c['breakdown'])}")
        print()


if __name__ == "__main__":
    run_pipeline()
    print_report()