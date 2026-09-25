from scoring.decision_engine import compute_final_score


def test_high_scores_are_selected():
    result = compute_final_score({"ats": 80, "screening": 85, "interview": 90})
    assert result["recommendation"] == "Selected"


def test_low_scores_are_rejected():
    result = compute_final_score({"ats": 30, "screening": 20})
    assert result["recommendation"] == "Rejected"