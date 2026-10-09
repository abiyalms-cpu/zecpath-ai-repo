from scoring_engine.score_components import (
    skill_match_score,
    experience_relevance_score,
    education_alignment_score,
    semantic_similarity_score,
)
from scoring_engine.weight_profiles import get_weight_profile


def compute_candidate_score(skill_profile, experience_record, education_record, semantic_match_record, jd_record, jd_file):
    """Combines all four components into one explainable score. Any component that
    can't be computed (missing data) is left out entirely — its weight is
    redistributed proportionally across whatever components ARE available, rather
    than treating a missing piece as a silent zero."""

    raw_scores = {
        "skill_match": skill_match_score(skill_profile, jd_record),
        "experience_relevance": experience_relevance_score(experience_record, jd_record, skill_profile),
        "education_alignment": education_alignment_score(education_record, jd_record),
        "semantic_similarity": semantic_similarity_score(semantic_match_record, jd_file),
    }

    weights = get_weight_profile(jd_file)

    available = {name: score for name, score in raw_scores.items() if score is not None}
    available_weight_total = sum(weights[name] for name in available)

    breakdown = []
    final_score = 0.0

    for name, original_weight in weights.items():
        raw_score = raw_scores[name]
        is_available = raw_score is not None

        if is_available and available_weight_total > 0:
            normalized_weight = original_weight / available_weight_total
            contribution = round(raw_score * normalized_weight, 4)
            final_score += contribution
        else:
            normalized_weight = 0.0
            contribution = 0.0

        breakdown.append({
            "component": name,
            "raw_score": raw_score,
            "original_weight": original_weight,
            "normalized_weight": round(normalized_weight, 4),
            "contribution": contribution,
            "available": is_available,
        })

    return {
        "final_score": round(final_score, 4),
        "breakdown": breakdown,
    }


def explain_score(result):
    """Turns a score result into plain-English lines — the 'explainable' part of
    the brief, not just a number."""
    lines = []
    for item in result["breakdown"]:
        if item["available"]:
            lines.append(
                f"{item['component']}: {item['raw_score']} "
                f"(weight {item['normalized_weight']*100:.0f}%) -> contributed {item['contribution']}"
            )
        else:
            lines.append(f"{item['component']}: not available — weight redistributed to other components")
    lines.append(f"Final score: {result['final_score']}")
    return lines