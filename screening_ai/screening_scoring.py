"""
Day 26 -- Screening Scoring Engine.

Days 24-25 decided what a candidate said (transcript_processor) and whether
it was usable (answer_understanding). This module decides how GOOD each
usable answer was, and rolls that up into one final screening score per
candidate -- the "AI screening report" PRD Phase 5 names as this phase's
output.

Named screening_scoring.py, not scoring_engine.py, on purpose: this repo
already has a scoring_engine/ package (the resume-vs-JD ATS score from
Phase 2). That one scores a resume against a job description; this one
scores a screening CALL against the candidate's own answers. Different
inputs, different question, so it gets its own name rather than overloading
an existing one.

Same two-level design as scoring_engine/scoring_engine.py on purpose, so
anyone who already understands that module understands this one:
- compute one explainable score per answer, with weights redistributed
  proportionally across whatever components are actually available
  (scoring_engine/scoring_engine.py already established this pattern for
  the resume ATS score -- reused here rather than inventing a second way
  to handle a missing component)
- then roll per-question scores into one final score, weighted by each
  question's own `scoring_importance` (Day 22's question bank already has
  this field -- no new weighting scheme invented for it)
"""

import json
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------- resume cross-check data (for the Consistency component) ----------

def _load_record_by_source_file(directory, candidate_id):
    """Scans a data/ directory (skills, experience, ...) for the record whose
    source_file matches this candidate. Filenames in those directories don't
    follow a predictable pattern from the candidate_id alone (e.g.
    "aarav_nair_fresher_docx_docx_skills.json" for source_file
    "aarav_nair_fresher_docx.docx"), so this matches on the field inside the
    file rather than guessing a filename -- same approach
    scoring_engine/score_components.py already uses for semantic_match_record
    lookups ("for m in matches: if m['jd_file'] == jd_file")."""
    folder = Path(directory)
    if not folder.exists():
        return None
    for path in folder.glob("*.json"):
        try:
            record = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if record.get("source_file") == candidate_id:
            return record
    return None


def load_resume_cross_check(candidate_id, skills_dir="data/skills", experience_dir="data/experience"):
    """Everything the Consistency component needs about what the candidate's
    resume already says, bundled together so callers pass one object instead
    of two directory paths through every function. Either half can come back
    None -- not every candidate has both files, and that's reported honestly
    rather than guessed at."""
    skills_record = _load_record_by_source_file(skills_dir, candidate_id)
    experience_record = _load_record_by_source_file(experience_dir, candidate_id)
    return {
        "resume_skills": {s["skill"] for s in (skills_record or {}).get("skills", [])} or None,
        "resume_experience_months": (experience_record or {}).get("total_experience_months"),
    }


# ---------- the four scoring parameters ----------

def clarity_score(answer):
    """How clearly the answer conveyed a value -- not whether it was the
    right value (that's Relevance) or a full one (that's Completeness), just
    whether it was unambiguous. A structured type the normalizer could
    actually parse is clear by definition; free text is judged by how much
    real content it carries."""
    if answer["intent"] == "no_answer":
        return None  # nothing was said -- there's no clarity to measure

    expected_type = answer["expected_answer_type"]
    if expected_type in ("yes_no", "number", "currency", "duration"):
        return 1.0 if answer["value"] is not None else 0.3
    if expected_type == "list":
        if answer["value"]:
            return 1.0
        # An empty list from a genuinely engaged answer (Day 25's "declined
        # every listed skill but clearly addressed the question" case) is
        # still a clear answer -- it's just a clear "none of these."
        return 0.7 if answer["intent"] == "answered" else 0.3

    # free_text: judged by substance, same word-count signal Day 25 already
    # uses to separate real content from a thin one.
    word_count = len((answer["normalized_text"] or "").split())
    if word_count >= 8:
        return 1.0
    if word_count >= 4:
        return 0.7
    return 0.3


def relevance_score(answer):
    """Whether the answer addressed the question that was actually asked.
    This is Day 25's off_topic flag, turned into a score instead of a
    label -- not recomputed from scratch, since Day 25 already did the real
    work of deciding that."""
    if answer["intent"] == "no_answer":
        return None  # nothing was said -- relevance isn't the right word for that, Completeness covers it
    return 0.0 if answer["intent"] == "off_topic" else 1.0


def completeness_score(answer):
    """Whether the candidate fully answered, not just clearly or relevantly.
    Always available, even for silence -- "nothing was said" is itself a
    measurable completeness fact, not a missing data point, so this is the
    one component that's never None."""
    return {
        "no_answer": 0.0,
        "partial_answer": 0.4,
        "vague": 0.5,
        "off_topic": 0.3,
        "answered": 1.0,
    }[answer["intent"]]


# Tolerance bands for comparing a stated number against the resume's own
# number -- a little slack for honest rounding ("about five years" vs a
# resume that works out to 4.6), a real penalty for a genuine mismatch.
_EXPERIENCE_CLOSE_YEARS = 1.0
_EXPERIENCE_FAR_YEARS = 2.0


def consistency_score(answer, category, resume_skills=None, resume_experience_months=None):
    """The one genuinely new component: does what the candidate said on the
    call match what their own resume already says? Only available where
    there's real resume data to check against -- everywhere else (salary,
    notice period, introduction, location, education) this is honestly None,
    not guessed at, because this repo has no independently verifiable source
    for those."""
    if category == "experience" and answer["expected_answer_type"] == "number":
        if answer["value"] is None or resume_experience_months is None:
            return None
        stated_years = answer["value"]
        resume_years = resume_experience_months / 12
        diff = abs(stated_years - resume_years)
        if diff <= _EXPERIENCE_CLOSE_YEARS:
            return 1.0
        if diff <= _EXPERIENCE_FAR_YEARS:
            return 0.6
        return 0.2

    if category == "skills" and answer["expected_answer_type"] == "list":
        if resume_skills is None:
            return None
        claimed = answer["value"] or []
        if not claimed:
            # A clear "none of these" doesn't contradict the resume either
            # way -- nothing claimed, nothing to check.
            return 1.0
        resume_skills_lower = {s.lower() for s in resume_skills}
        matched = sum(1 for skill in claimed if skill.lower() in resume_skills_lower)
        return round(matched / len(claimed), 4)

    return None  # no resume ground truth exists for this category


# ---------- per-question scoring, with proportional redistribution ----------

DEFAULT_COMPONENT_WEIGHTS = {
    "clarity": 0.25,
    "relevance": 0.25,
    "completeness": 0.25,
    "consistency": 0.25,
}
# Equal weighting by default -- the brief names all four parameters without
# ranking them, and no other day's work implies a different split. If a
# real screening round later shows one component should matter more, this
# is the one place to change it.


def score_answer(answer, category, resume_skills=None, resume_experience_months=None,
                  weights=None):
    """One explainable per-question score. Same redistribution pattern as
    scoring_engine/scoring_engine.py's compute_candidate_score: a component
    that isn't available for this answer has its weight redistributed
    proportionally across the components that are, rather than counted as a
    silent zero."""
    weights = weights or DEFAULT_COMPONENT_WEIGHTS

    raw_scores = {
        "clarity": clarity_score(answer),
        "relevance": relevance_score(answer),
        "completeness": completeness_score(answer),
        "consistency": consistency_score(answer, category, resume_skills, resume_experience_months),
    }

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
        "question_id": answer["question_id"],
        "category": category,
        "intent": answer["intent"],
        "final_score": round(final_score, 4),
        "breakdown": breakdown,
    }


# ---------- aggregate screening score, weighted by scoring_importance ----------

def aggregate_screening_score(per_question_results, scoring_importance_by_question):
    """Rolls every per-question score into one final screening score,
    weighted by each question's own `scoring_importance` from Day 22's
    question bank -- not a new weighting scheme, the same one the question
    bank already carries. A question this candidate wasn't asked (missing
    from per_question_results) has its weight redistributed across the
    questions that were actually scored, same proportional-redistribution
    logic as everywhere else in this file."""
    weight_total = sum(
        scoring_importance_by_question.get(r["question_id"], 0) for r in per_question_results
    )

    breakdown = []
    final_score = 0.0
    for result in per_question_results:
        original_weight = scoring_importance_by_question.get(result["question_id"], 0)
        normalized_weight = (original_weight / weight_total) if weight_total > 0 else 0.0
        contribution = round(result["final_score"] * normalized_weight, 4)
        final_score += contribution
        breakdown.append({
            "question_id": result["question_id"],
            "category": result["category"],
            "intent": result["intent"],
            "question_score": result["final_score"],
            "original_weight": original_weight,
            "normalized_weight": round(normalized_weight, 4),
            "contribution": contribution,
        })

    return {
        "final_screening_score": round(final_score, 4),
        "questions_scored": len(per_question_results),
        "breakdown": breakdown,
    }


def score_screening_session(semantic_answers, categories_by_question, scoring_importance_by_question,
                              resume_skills=None, resume_experience_months=None, weights=None):
    """The screening scoring engine, top to bottom: every semantic answer
    from Day 25 in, one explainable final screening score object out."""
    per_question_results = [
        score_answer(
            answer, categories_by_question[answer["question_id"]],
            resume_skills=resume_skills, resume_experience_months=resume_experience_months,
            weights=weights,
        )
        for answer in semantic_answers
    ]
    return aggregate_screening_score(per_question_results, scoring_importance_by_question)


# ---------- explainable output ----------

def explain_question_score(result):
    """Plain-English lines for one question's score -- same style as
    scoring_engine/scoring_engine.py's explain_score, so a reader who
    already knows that report format recognizes this one."""
    lines = [f"{result['question_id']} ({result['category']}, intent: {result['intent']})"]
    for item in result["breakdown"]:
        if item["available"]:
            lines.append(
                f"  {item['component']}: {item['raw_score']} "
                f"(weight {item['normalized_weight']*100:.0f}%) -> contributed {item['contribution']}"
            )
        else:
            lines.append(f"  {item['component']}: not available -- weight redistributed")
    lines.append(f"  Question score: {result['final_score']}")
    return lines


def explain_screening_score(aggregate_result):
    lines = [f"Final screening score: {aggregate_result['final_screening_score']}",
             f"({aggregate_result['questions_scored']} questions scored)", ""]
    for item in aggregate_result["breakdown"]:
        lines.append(
            f"{item['question_id']}: score={item['question_score']} "
            f"weight={item['normalized_weight']*100:.0f}% -> contributed {item['contribution']}"
        )
    return lines


# ---------- Honest gaps ----------
#
# - Consistency only covers experience and skills, because those are the
#   only two categories this repo has independently verifiable resume data
#   for. Salary expectation, notice period, location and self-introduction
#   have no resume-derived ground truth to check against, so their
#   Consistency component is honestly None and its weight is redistributed
#   -- not scored against a made-up baseline.
# - The experience tolerance bands (within 1 year = consistent, within 2 =
#   partially consistent, beyond = inconsistent) are a reasonable starting
#   point, not a validated threshold -- there's no labeled "this candidate
#   lied" dataset in this repo to calibrate against.
# - Component weights are equal (25% each) because the brief doesn't rank
#   the four parameters and nothing else in this repo implies a different
#   split. That's a stated assumption, not a finding.
# - Consistency only checks each answer against the resume -- it does NOT
#   cross-check two of the candidate's own answers against each other.
#   Caught live during build: a test candidate said "seven years" for
#   financial_analyst_experience_01 (number) and, two questions later,
#   "worked ... for six years" in financial_analyst_experience_02
#   (free_text) -- a real internal contradiction this module does not
#   currently catch, because experience_02 is free_text and consistency_score
#   only runs against the number-type experience question. Flagged rather
#   than silently left looking more thorough than it is; a future day could
#   add within-session cross-checks as a fifth signal.