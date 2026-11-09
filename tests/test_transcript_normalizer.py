import pytest

from screening_ai.transcript_normalizer import (
    strip_filler_words,
    spoken_number_to_digit,
    normalize_free_text,
    normalize_number_answer,
    normalize_yes_no_answer,
    normalize_currency_answer,
    normalize_duration_answer,
    normalize_list_answer,
    normalize_answer,
)

CANONICAL_SKILLS = ["JavaScript", "React", "Node.js", "MongoDB"]


# ---------- strip_filler_words ----------

def test_strips_standalone_filler_words():
    assert strip_filler_words("um so I studied computer science") == "I studied computer science"


def test_does_not_strip_filler_word_as_a_substring():
    # "like" must not eat the "like" inside "likely" or "unlike"
    assert "likely" in strip_filler_words("it will likely take two weeks")


def test_collapses_repeated_whitespace():
    assert strip_filler_words("hello   world") == "hello world"


def test_empty_input_returns_empty_string():
    assert strip_filler_words("") == ""
    assert strip_filler_words(None) == ""


# ---------- spoken_number_to_digit ----------

@pytest.mark.parametrize("phrase,expected", [
    ("five", 5),
    ("twenty", 20),
    ("twenty one", 21),
    ("twenty-five", 25),
    ("ninety nine", 99),
    ("0", 0),
    ("42", 42),
])
def test_spoken_number_to_digit_recognized_phrases(phrase, expected):
    assert spoken_number_to_digit(phrase) == expected


@pytest.mark.parametrize("phrase", ["a hundred", "banana", "twenty thirty", "100"])
def test_spoken_number_to_digit_unrecognized_returns_none(phrase):
    assert spoken_number_to_digit(phrase) is None


# ---------- normalize_free_text ----------

def test_free_text_strips_fillers_keeps_content():
    assert normalize_free_text("um so basically I studied computer science") == "I studied computer science"


# ---------- normalize_number_answer ----------

def test_number_answer_parses_spoken_years():
    result = normalize_number_answer("um like twenty five years")
    assert result == {"value": 25, "unparsed": False}


def test_number_answer_parses_plain_digit():
    assert normalize_number_answer("5 years") == {"value": 5, "unparsed": False}


def test_number_answer_out_of_range_is_flagged_not_coerced():
    result = normalize_number_answer("a couple of years")
    assert result["unparsed"] is True
    assert result["value"]  # original text kept, not silently zeroed


# ---------- normalize_yes_no_answer ----------

@pytest.mark.parametrize("phrase,expected", [
    ("yes", True),
    ("uh yeah sure, definitely", True),
    ("of course", True),
    ("no", False),
    ("nope", False),
    ("not really", False),
])
def test_yes_no_recognized_variants(phrase, expected):
    assert normalize_yes_no_answer(phrase) is expected


def test_yes_no_hedging_answer_stays_null():
    assert normalize_yes_no_answer("maybe, depends") is None


def test_yes_no_empty_answer_stays_null():
    assert normalize_yes_no_answer("") is None


# ---------- normalize_currency_answer ----------

def test_currency_parses_lakhs():
    assert normalize_currency_answer("um around 12 lakhs per annum") == {
        "amount": 1_200_000, "currency": "INR", "unparsed": False,
    }


def test_currency_parses_crores():
    assert normalize_currency_answer("1.5 crores") == {
        "amount": 15_000_000, "currency": "INR", "unparsed": False,
    }


def test_currency_parses_plain_number():
    assert normalize_currency_answer("800000 rupees") == {
        "amount": 800_000, "currency": "INR", "unparsed": False,
    }


def test_currency_vague_answer_kept_as_text():
    result = normalize_currency_answer("market rate")
    assert result == {"value": "market rate", "unparsed": True}


# ---------- normalize_duration_answer ----------

@pytest.mark.parametrize("phrase,expected_days", [
    ("one month", 30),
    ("2 months", 60),
    ("two weeks", 14),
    ("15 days", 15),
    ("immediately", 0),
    ("I can join right away", 0),
])
def test_duration_recognized_phrases(phrase, expected_days):
    result = normalize_duration_answer(phrase)
    assert result == {"days": expected_days, "unparsed": False}


def test_duration_unparseable_kept_as_text():
    result = normalize_duration_answer("whenever works for the team")
    assert result["unparsed"] is True


# ---------- normalize_list_answer ----------

def test_list_matches_canonical_skills_from_a_sentence():
    raw = "uh yeah so I've worked with react and node js mostly, not so much mongo"
    assert normalize_list_answer(raw, CANONICAL_SKILLS) == ["React", "Node.js"]


def test_list_negation_excludes_the_denied_skill():
    # MongoDB is mentioned but denied -- it must not appear as a match
    raw = "not much experience with mongo"
    assert "MongoDB" not in normalize_list_answer(raw, CANONICAL_SKILLS)


def test_list_matches_regardless_of_spacing_and_case():
    assert normalize_list_answer("javascript and NODEJS", CANONICAL_SKILLS) == ["JavaScript", "Node.js"]


def test_list_without_canonical_skills_falls_back_to_plain_split():
    assert normalize_list_answer("Python, Django and SQL") == ["Python", "Django", "SQL"]


def test_list_no_mentioned_skills_returns_empty():
    assert normalize_list_answer("I mostly do backend work in Python", CANONICAL_SKILLS) == []


# ---------- normalize_answer dispatcher ----------

def test_dispatcher_routes_to_the_right_rule():
    assert normalize_answer("yes", "yes_no") is True
    assert normalize_answer("five", "number") == {"value": 5, "unparsed": False}


def test_dispatcher_rejects_unknown_answer_type():
    with pytest.raises(ValueError):
        normalize_answer("whatever", "essay")