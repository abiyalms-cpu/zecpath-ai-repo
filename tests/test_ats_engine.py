from ats_engine.ats_scorer import score_resume


def test_full_skill_match():
    parsed = {"skills": ["Python", "SQL"]}
    result = score_resume(parsed, ["Python", "SQL"])
    assert result["ats_score"] == 100


def test_partial_skill_match():
    parsed = {"skills": ["Python"]}
    result = score_resume(parsed, ["Python", "SQL"])
    assert result["ats_score"] == 50
    assert result["missing_skills"] == ["SQL"]