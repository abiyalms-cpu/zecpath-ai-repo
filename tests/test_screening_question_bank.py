import json

from screening_ai.question_categories import CATEGORIES, CATEGORY_KEYS, category_label
from screening_ai.question_templates import QUESTION_TEMPLATES, ANSWER_TYPES
from screening_ai.question_builder import build_question_bank_for_jd
from screening_ai.question_bank_generator import build_bank_for_jd, build_all_banks
from screening_ai.call_handler import trigger_call


# ---------- question_categories ----------

def test_categories_match_the_prd_order():
    # PRD Phase 5 / Day 22's own task list, in this exact order.
    assert CATEGORY_KEYS == [
        "introduction", "education", "experience", "skills", "location", "salary", "notice_period",
    ]


def test_category_label_returns_readable_name():
    assert category_label("notice_period") == "Notice Period"


def test_category_label_is_none_for_unknown_key():
    assert category_label("made_up") is None


# ---------- question_templates ----------

def test_every_template_has_a_known_category():
    for t in QUESTION_TEMPLATES:
        assert t["category"] in CATEGORY_KEYS, t


def test_every_template_has_a_known_answer_type():
    for t in QUESTION_TEMPLATES:
        assert t["expected_answer_type"] in ANSWER_TYPES, t


def test_every_category_has_at_least_one_template():
    covered = {t["category"] for t in QUESTION_TEMPLATES}
    assert covered == set(CATEGORY_KEYS)


def test_role_specific_templates_contain_a_placeholder():
    # A template marked role_specific must actually have something for the
    # builder to fill in -- otherwise the flag is just wrong.
    for t in QUESTION_TEMPLATES:
        if t["role_specific"]:
            assert "{" in t["text"], t


# ---------- question_builder ----------

def _sample_jd():
    return {
        "title": "SDE II",
        "location": "Remote (India)",
        "required_skills": [
            {"name": "React", "mandatory": True},
            {"name": "Node.js", "mandatory": True},
            {"name": "GraphQL", "mandatory": False},
        ],
    }


def test_build_question_bank_fills_role_specific_placeholders():
    questions = build_question_bank_for_jd(_sample_jd(), "sde_ii")
    experience_q = next(q for q in questions if q["id"] == "sde_ii_experience_01")
    assert "SDE II" in experience_q["text"]

    skills_q = next(q for q in questions if q["id"] == "sde_ii_skills_01")
    assert "React" in skills_q["text"] and "Node.js" in skills_q["text"]
    assert "GraphQL" not in skills_q["text"]  # optional skill, not asked as a must-have

    location_q = next(q for q in questions if q["id"] == "sde_ii_location_01")
    assert "Remote (India)" in location_q["text"]


def test_build_question_bank_leaves_no_unfilled_placeholders():
    questions = build_question_bank_for_jd(_sample_jd(), "sde_ii")
    for q in questions:
        assert "{" not in q["text"] and "}" not in q["text"], q


def test_non_role_specific_question_text_is_identical_across_roles():
    jd_a = _sample_jd()
    jd_b = {"title": "HR Manager", "location": "Chennai", "required_skills": []}
    q_a = build_question_bank_for_jd(jd_a, "sde_ii")
    q_b = build_question_bank_for_jd(jd_b, "hr_manager")
    intro_a = next(q for q in q_a if q["category"] == "introduction")
    intro_b = next(q for q in q_b if q["category"] == "introduction")
    assert intro_a["text"] == intro_b["text"]


def test_jd_with_no_mandatory_skills_gets_an_honest_fallback_phrase():
    jd = {"title": "Generalist", "location": "Pune", "required_skills": []}
    questions = build_question_bank_for_jd(jd, "generalist")
    skills_q = next(q for q in questions if q["id"] == "generalist_skills_01")
    assert "the skills listed in the job description" in skills_q["text"]


def test_every_question_is_tagged_with_mandatory_and_scoring_importance():
    for q in build_question_bank_for_jd(_sample_jd(), "sde_ii"):
        assert isinstance(q["mandatory"], bool)
        assert 0.0 <= q["scoring_importance"] <= 1.0


def test_every_question_carries_a_language_tag_ready_for_future_translation():
    for q in build_question_bank_for_jd(_sample_jd(), "sde_ii"):
        assert q["language"] == "en"


# ---------- question_bank_generator ----------

def test_build_bank_for_jd_writes_one_file(tmp_path):
    jds_dir = tmp_path / "jds"
    jds_dir.mkdir()
    (jds_dir / "sde_ii.json").write_text(json.dumps(_sample_jd()), encoding="utf-8")
    output_dir = tmp_path / "out"

    questions = build_bank_for_jd(str(jds_dir), "sde_ii", str(output_dir))

    assert len(questions) == len(QUESTION_TEMPLATES)
    saved = json.loads((output_dir / "sde_ii_questions.json").read_text(encoding="utf-8"))
    assert saved["jd_file"] == "sde_ii"
    assert saved["role_title"] == "SDE II"
    assert len(saved["questions"]) == len(QUESTION_TEMPLATES)


def test_build_all_banks_writes_one_file_per_jd(tmp_path):
    jds_dir = tmp_path / "jds"
    jds_dir.mkdir()
    (jds_dir / "sde_ii.json").write_text(json.dumps(_sample_jd()), encoding="utf-8")
    (jds_dir / "hr_manager.json").write_text(
        json.dumps({"title": "HR Manager", "location": "Chennai", "required_skills": []}), encoding="utf-8"
    )
    output_dir = tmp_path / "out"

    count = build_all_banks(str(jds_dir), str(output_dir))

    assert count == 2
    assert (output_dir / "sde_ii_questions.json").exists()
    assert (output_dir / "hr_manager_questions.json").exists()


# ---------- integration with the existing (Day 1) screening_ai stub ----------

def test_question_bank_output_plugs_directly_into_trigger_call():
    # call_handler.trigger_call already expects a `questions` list -- today's
    # bank is that list, produced for real instead of left as a placeholder.
    questions = build_question_bank_for_jd(_sample_jd(), "sde_ii")
    result = trigger_call("+91-9000000000", questions)
    assert result["call_status"] == "queued"
    assert result["questions_to_ask"] == questions