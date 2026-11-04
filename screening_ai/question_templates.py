"""
Reusable question templates — role-agnostic text with named placeholders
({role_title}, {mandatory_skills}, {jd_location}) that question_builder.py
fills in from a JD's own already-parsed data, so no role's question bank is
typed out by hand.

Each template is tagged with the three things Day 22 asked for directly:
expected_answer_type, mandatory, and scoring_importance (a 0-1 relative
weight for a future scoring day to consume -- nothing is computed from it
here, it is metadata only). role_specific marks a template whose text
depends on JD data; the others are asked exactly as written for every role.
"""

# A small, fixed vocabulary on purpose -- a future AI scoring step needs to
# know how to parse a transcribed answer, and "a number" parses differently
# from "a yes/no".
ANSWER_TYPES = ["free_text", "number", "list", "yes_no", "currency", "duration"]

QUESTION_TEMPLATES = [
    {
        "id": "introduction_01",
        "category": "introduction",
        "text": "Could you briefly introduce yourself and walk me through your professional background?",
        "expected_answer_type": "free_text",
        "mandatory": True,
        "scoring_importance": 0.05,
        "role_specific": False,
    },
    {
        "id": "education_01",
        "category": "education",
        "text": "What is your highest educational qualification, and which field was it in?",
        "expected_answer_type": "free_text",
        "mandatory": True,
        "scoring_importance": 0.10,
        "role_specific": False,
    },
    {
        "id": "education_02",
        "category": "education",
        "text": "Do you hold any certifications relevant to this role?",
        "expected_answer_type": "free_text",
        "mandatory": False,
        "scoring_importance": 0.05,
        "role_specific": False,
    },
    {
        "id": "experience_01",
        "category": "experience",
        "text": "You're applying for the {role_title} position — could you walk me through your total years of relevant experience?",
        "expected_answer_type": "number",
        "mandatory": True,
        "scoring_importance": 0.20,
        "role_specific": True,
    },
    {
        "id": "experience_02",
        "category": "experience",
        "text": "Have you worked in a {role_title} role, or something close to it, before? For how long?",
        "expected_answer_type": "free_text",
        "mandatory": False,
        "scoring_importance": 0.10,
        "role_specific": True,
    },
    {
        "id": "skills_01",
        "category": "skills",
        "text": "This role expects hands-on experience with {mandatory_skills}. Which of these have you personally worked with?",
        "expected_answer_type": "list",
        "mandatory": True,
        "scoring_importance": 0.25,
        "role_specific": True,
    },
    {
        "id": "skills_02",
        "category": "skills",
        "text": "Is there anything on that list you haven't used yet but would be confident picking up quickly?",
        "expected_answer_type": "free_text",
        "mandatory": False,
        "scoring_importance": 0.05,
        "role_specific": False,
    },
    {
        "id": "location_01",
        "category": "location",
        "text": "This role is based in {jd_location}. Are you currently located there, or would relocation be needed?",
        "expected_answer_type": "yes_no",
        "mandatory": True,
        "scoring_importance": 0.10,
        "role_specific": True,
    },
    {
        "id": "salary_01",
        "category": "salary",
        "text": "What are your salary expectations for this role?",
        "expected_answer_type": "currency",
        "mandatory": True,
        "scoring_importance": 0.05,
        "role_specific": False,
    },
    {
        "id": "notice_period_01",
        "category": "notice_period",
        "text": "What's your current notice period, or how soon would you be available to join?",
        "expected_answer_type": "duration",
        "mandatory": True,
        "scoring_importance": 0.10,
        "role_specific": False,
    },
]