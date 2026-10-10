# Thresholds chosen from the real score distribution across two JDs with different
# weight profiles (digital_marketing, sde_ii) — both showed the same three-tier shape:
# a cluster of genuine matches, a mid-tier partial match, then a long tail of noise.
SHORTLIST_THRESHOLD = 0.15
REVIEW_THRESHOLD = 0.03


def classify_zone(final_score):
    if final_score >= SHORTLIST_THRESHOLD:
        return "shortlist"
    if final_score >= REVIEW_THRESHOLD:
        return "review"
    return "auto_reject"


def apply_shortlisting(ranked_candidates):
    """Tags each ranked candidate with its zone. Does not filter anything out —
    a recruiter should be able to see the full ranked list with zones marked,
    not have auto-rejected candidates silently disappear."""
    for candidate in ranked_candidates:
        candidate["zone"] = classify_zone(candidate["final_score"])
    return ranked_candidates
