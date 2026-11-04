"""
Fills the role-agnostic templates in question_templates.py with a specific
JD's own already-parsed data (title, required_skills, location) to produce
one AI conversation-ready question bank per role -- nothing about a role is
typed out by hand twice.
"""

from screening_ai.question_templates import QUESTION_TEMPLATES


def _placeholders_for_jd(jd_record):
    required_skills = jd_record.get("required_skills") or []
    mandatory_names = [s["name"] for s in required_skills if s.get("mandatory")]
    return {
        "role_title": jd_record.get("title") or "this role",
        "mandatory_skills": ", ".join(mandatory_names) if mandatory_names else "the skills listed in the job description",
        "jd_location": jd_record.get("location") or "the role's location",
    }


def build_question_bank_for_jd(jd_record, jd_file):
    """Returns a list of AI conversation-ready question objects for one role --
    the exact shape screening_ai.call_handler.trigger_call already expects as
    its `questions` argument."""
    placeholders = _placeholders_for_jd(jd_record)
    questions = []
    for template in QUESTION_TEMPLATES:
        text = template["text"].format(**placeholders) if template["role_specific"] else template["text"]
        questions.append({
            "id": f"{jd_file}_{template['id']}",
            "category": template["category"],
            "text": text,
            "expected_answer_type": template["expected_answer_type"],
            "mandatory": template["mandatory"],
            "scoring_importance": template["scoring_importance"],
            # Schema is translation-ready -- only English text exists today,
            # a future pass can add parallel objects with language: "hi" etc.
            # without restructuring anything.
            "language": "en",
        })
    return questions