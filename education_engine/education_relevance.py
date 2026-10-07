from experience_engine.relevance_scorer import role_similarity


def score_field_relevance(education_entries, target_role):
    """Best-match relevance of a candidate's field of study / degree to a target role.
    Reuses Day 10's role_similarity (canonical synonyms + Jaccard word-overlap fallback)
    rather than building a second matching system."""
    if not education_entries or not target_role:
        return 0.0
    best = 0.0
    for entry in education_entries:
        field = entry.get("field_of_study") or entry.get("degree_normalized") or ""
        if not field:
            continue
        score = role_similarity(field, target_role)
        if score > best:
            best = score
    return best


def tag_certification_relevance(certifications, relevant_categories):
    """Flags each certification as relevant if its category is in the caller-supplied
    list of categories that matter for the target role (e.g. ["Technology"] for an SDE role)."""
    relevant_categories = {c.lower() for c in (relevant_categories or [])}
    tagged = []
    for cert in certifications:
        is_relevant = cert["category"].lower() in relevant_categories
        tagged.append({**cert, "relevant": is_relevant})
    return tagged