import re
import glob
from pathlib import Path

EMAIL_PATTERN = re.compile(r"[\w.\-]+@[\w.\-]+\.\w+")
PHONE_PATTERN = re.compile(r"\+?\d[\d\-\s]{7,}\d")
LINKEDIN_PATTERN = re.compile(r"linkedin\.com/\S+", re.IGNORECASE)


def redact_header(header_lines):
    """Masks name, email, phone, and LinkedIn URL from a resume's HEADER section.
    The first line is assumed to be the candidate's name (consistent with every
    real HEADER we've seen since Day 5/8) and is replaced outright; the rest is
    scrubbed of contact-detail patterns but keeps non-identifying content like
    job title and location."""
    if not header_lines:
        return []

    redacted = ["[Candidate name redacted]"]
    for line in header_lines[1:]:
        line = EMAIL_PATTERN.sub("[email redacted]", line)
        line = PHONE_PATTERN.sub("[phone redacted]", line)
        line = LINKEDIN_PATTERN.sub("[linkedin redacted]", line)
        redacted.append(line)
    return redacted


def build_candidate_id_map(segmented_dir):
    """Stable anonymized IDs (CAND-001, CAND-002, ...), assigned by sorting every
    resume's filename alphabetically. Known limit: adding a new resume later
    would shift every ID after it — a production system would persist explicit
    assignments instead of recomputing them from a sorted list each time."""
    stems = sorted(Path(p).stem.replace("_sections", "") for p in glob.glob(f"{segmented_dir}/*.json"))
    return {stem: f"CAND-{i+1:03d}" for i, stem in enumerate(stems)}