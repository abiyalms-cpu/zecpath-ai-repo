"""
Representative sample inputs for the Transcript Cleanup Test Report
(Day 24's "STT accuracy test report" deliverable -- see that report's own
opening note for why it's named "cleanup", not "accuracy").

Each case is a raw_text string shaped like a real speech-to-text artifact
(filler words, missing punctuation, run-together casing, spoken numbers,
hedging, negation) rather than already-clean text -- a normalizer that only
gets tested on clean input never proves anything.

`expected` is what process_transcript must return for `normalized_text` and
`parsed_value` so the report can show a real pass/fail, not just a printout.
"""

CANONICAL_SKILLS = ["JavaScript", "React", "Node.js", "MongoDB"]

CLEANUP_TEST_CASES = [
    {
        "label": "filler words, informal self-introduction",
        "raw_text": "um so uh basically I'm a software engineer with like five years of experience",
        "expected_answer_type": "free_text",
        "expected_normalized_text": "I'm a software engineer with five years of experience",
    },
    {
        "label": "spoken number, with unit spoken back",
        "raw_text": "um like twenty five years",
        "expected_answer_type": "number",
        "expected_parsed_value": 25,
    },
    {
        "label": "plain digit already spoken as a number",
        "raw_text": "5 years",
        "expected_answer_type": "number",
        "expected_parsed_value": 5,
    },
    {
        "label": "number phrase outside recognizable range -- must not be coerced to 0",
        "raw_text": "around a hundred projects or so",
        "expected_answer_type": "number",
        "expected_unparsed": True,
    },
    {
        "label": "clear yes with filler and hedge words around it",
        "raw_text": "uh yeah sure, definitely",
        "expected_answer_type": "yes_no",
        "expected_parsed_value": True,
    },
    {
        "label": "soft no phrased conversationally",
        "raw_text": "not really, no",
        "expected_answer_type": "yes_no",
        "expected_parsed_value": False,
    },
    {
        "label": "genuinely ambiguous answer -- must stay null, not guessed",
        "raw_text": "maybe, it depends on the team",
        "expected_answer_type": "yes_no",
        "expected_parsed_value": None,
    },
    {
        "label": "currency in lakhs with filler and unit words",
        "raw_text": "um around 12 lakhs per annum",
        "expected_answer_type": "currency",
        "expected_parsed_value": {"amount": 1_200_000, "currency": "INR"},
    },
    {
        "label": "currency, vague non-numeric answer kept as text",
        "raw_text": "it's negotiable, market rate basically",
        "expected_answer_type": "currency",
        "expected_unparsed": True,
    },
    {
        "label": "notice period in weeks",
        "raw_text": "uh two weeks notice",
        "expected_answer_type": "duration",
        "expected_parsed_value": 14,
    },
    {
        "label": "notice period, immediate joiner phrasing",
        "raw_text": "I can join right away",
        "expected_answer_type": "duration",
        "expected_parsed_value": 0,
    },
    {
        "label": "skills list spoken as a sentence, one skill explicitly denied",
        "raw_text": "uh yeah so I've worked with react and node js mostly, not so much mongo",
        "expected_answer_type": "list",
        "canonical_skills": CANONICAL_SKILLS,
        "expected_parsed_value": ["React", "Node.js"],
    },
    {
        "label": "skills list with spacing/casing differences from the canonical names",
        "raw_text": "javascript and NODEJS, that's about it",
        "expected_answer_type": "list",
        "canonical_skills": CANONICAL_SKILLS,
        "expected_parsed_value": ["JavaScript", "Node.js"],
    },
    {
        "label": "silence -- candidate said nothing",
        "raw_text": "",
        "expected_answer_type": "free_text",
        "expected_silence": True,
    },
    {
        "label": "silence -- STT returned only dead air / noise markers",
        "raw_text": "   ",
        "expected_answer_type": "free_text",
        "expected_silence": True,
    },
    {
        "label": "partial answer -- call cut off mid-sentence",
        "raw_text": "I have around three years of experience in",
        "expected_answer_type": "free_text",
        "partial": True,
        "expected_normalized_text": "I have around three years of experience in",
    },
    {
        "label": "interrupted -- candidate started answering, then talked over",
        "raw_text": "I worked at",
        "expected_answer_type": "free_text",
        "interrupted": True,
        "expected_normalized_text": "I worked at",
    },
]