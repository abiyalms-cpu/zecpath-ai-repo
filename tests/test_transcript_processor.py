from screening_ai.transcript_processor import process_transcript

BASE = dict(
    transcript_id="sde_ii_karthik_subramaniam.docx_skills_01_a1",
    candidate_id="karthik_subramaniam.docx",
    job_id="sde_ii",
    question_id="sde_ii_skills_01",
)


def test_builds_the_full_day23_schema_shape():
    record = process_transcript(
        **BASE,
        raw_text="uh yeah so I've worked with react and node js mostly, not so much mongo",
        expected_answer_type="list",
        confidence_level=0.87,
        canonical_skills=["JavaScript", "React", "Node.js", "MongoDB"],
    )
    expected_keys = {
        "transcript_id", "candidate_id", "job_id", "question_id", "timestamp",
        "raw_text", "normalized_text", "parsed_value", "confidence_level",
        "expected_answer_type", "language", "silence_detected",
        "partial_answer", "interrupted",
    }
    assert set(record.keys()) == expected_keys


def test_raw_text_is_never_modified():
    raw = "uh yeah so I've worked with react, not so much mongo"
    record = process_transcript(
        **BASE, raw_text=raw, expected_answer_type="list",
        canonical_skills=["React", "MongoDB"],
    )
    assert record["raw_text"] == raw


def test_list_answer_normalizes_and_parses():
    record = process_transcript(
        **BASE,
        raw_text="uh yeah so I've worked with react and node js mostly, not so much mongo",
        expected_answer_type="list",
        confidence_level=0.87,
        canonical_skills=["JavaScript", "React", "Node.js", "MongoDB"],
    )
    assert record["normalized_text"] == "React, Node.js"
    assert record["parsed_value"] == ["React", "Node.js"]
    assert record["confidence_level"] == 0.87


def test_number_answer_parses_to_an_int():
    record = process_transcript(
        **BASE, raw_text="um like twenty five years", expected_answer_type="number",
    )
    assert record["normalized_text"] == "25"
    assert record["parsed_value"] == 25


def test_unparsed_number_keeps_text_and_null_parsed_value():
    record = process_transcript(
        **BASE, raw_text="a couple of years", expected_answer_type="number",
    )
    assert record["parsed_value"] is None
    assert record["normalized_text"]  # original text kept, not dropped


def test_yes_no_answer_renders_as_yes_or_no_text():
    record = process_transcript(**BASE, raw_text="yeah sure", expected_answer_type="yes_no")
    assert record["normalized_text"] == "Yes"
    assert record["parsed_value"] is True


def test_currency_answer_renders_formatted_text_and_structured_value():
    record = process_transcript(
        **BASE, raw_text="around 12 lakhs per annum", expected_answer_type="currency",
    )
    assert record["normalized_text"] == "INR 1,200,000"
    assert record["parsed_value"] == {"amount": 1_200_000, "currency": "INR"}


def test_duration_answer_renders_days():
    record = process_transcript(**BASE, raw_text="one month", expected_answer_type="duration")
    assert record["normalized_text"] == "30 days"
    assert record["parsed_value"] == 30


# ---------- silence detection ----------

def test_empty_raw_text_is_flagged_as_silence():
    record = process_transcript(
        **BASE, raw_text="", expected_answer_type="free_text", confidence_level=0.9,
    )
    assert record["silence_detected"] is True
    assert record["normalized_text"] is None
    assert record["parsed_value"] is None


def test_whitespace_only_raw_text_is_flagged_as_silence():
    record = process_transcript(
        **BASE, raw_text="   ", expected_answer_type="free_text",
    )
    assert record["silence_detected"] is True


def test_silence_forces_confidence_to_zero_even_if_provider_sent_a_value():
    # A provider might still return some confidence number on empty audio --
    # that number is not meaningful for recognizing silence, so it's not
    # trusted here.
    record = process_transcript(
        **BASE, raw_text="", expected_answer_type="free_text", confidence_level=0.6,
    )
    assert record["confidence_level"] == 0.0


def test_non_silent_answer_is_not_flagged():
    record = process_transcript(**BASE, raw_text="yes", expected_answer_type="yes_no")
    assert record["silence_detected"] is False


# ---------- partial / interrupted flags ----------

def test_partial_flag_is_carried_onto_the_record():
    record = process_transcript(
        **BASE, raw_text="I have three years of exp", expected_answer_type="free_text",
        partial=True,
    )
    assert record["partial_answer"] is True
    # a partial answer is still normalized -- it's not treated as silence
    assert record["normalized_text"] == "I have three years of exp"


def test_interrupted_flag_is_carried_onto_the_record():
    record = process_transcript(
        **BASE, raw_text="I worked at", expected_answer_type="free_text", interrupted=True,
    )
    assert record["interrupted"] is True


def test_flags_default_to_false():
    record = process_transcript(**BASE, raw_text="yes", expected_answer_type="yes_no")
    assert record["partial_answer"] is False
    assert record["interrupted"] is False


def test_timestamp_defaults_to_now_in_iso_format_with_offset():
    record = process_transcript(**BASE, raw_text="yes", expected_answer_type="yes_no")
    # same shape as education_tagger.py / experience_tagger.py's extracted_at
    assert "T" in record["timestamp"]
    assert "+" in record["timestamp"] or record["timestamp"].endswith("Z")


def test_explicit_timestamp_is_kept_as_given():
    record = process_transcript(
        **BASE, raw_text="yes", expected_answer_type="yes_no",
        timestamp="2026-11-05T10:42:17+00:00",
    )
    assert record["timestamp"] == "2026-11-05T10:42:17+00:00"