"""
Runs the transcript cleanup module (screening_ai/transcript_normalizer.py +
transcript_processor.py) against the representative sample inputs in
screening_ai/cleanup_test_cases.py, and writes a plain markdown report of
what passed and what didn't.

This is Day 24's "STT accuracy test report" deliverable, under its honest
name: there is no real speech-to-text provider integrated anywhere in this
repo yet (screening_ai/call_handler.py is still the Day 1 stub, so no audio
ever reaches this pipeline), so there's nothing to measure microphone-to-text
*accuracy* against. What this script actually measures -- and all it claims
to measure -- is whether the cleanup rules correctly handle realistic STT-style
output: filler words, run-on phrasing, spoken numbers, hedging, negation,
silence, partial and interrupted answers.

Run with: python transcript_cleanup_report.py
"""

from screening_ai.cleanup_test_cases import CLEANUP_TEST_CASES
from screening_ai.transcript_processor import process_transcript


def _run_case(case):
    record = process_transcript(
        transcript_id="report_case",
        candidate_id="report_candidate",
        job_id="report_job",
        question_id="report_question",
        raw_text=case["raw_text"],
        expected_answer_type=case["expected_answer_type"],
        canonical_skills=case.get("canonical_skills"),
        partial=case.get("partial", False),
        interrupted=case.get("interrupted", False),
    )

    checks = []

    if "expected_normalized_text" in case:
        checks.append(("normalized_text", case["expected_normalized_text"], record["normalized_text"]))
    if "expected_parsed_value" in case:
        checks.append(("parsed_value", case["expected_parsed_value"], record["parsed_value"]))
    if case.get("expected_unparsed"):
        checks.append(("parsed_value is None (unparsed)", None, record["parsed_value"]))
    if case.get("expected_silence"):
        checks.append(("silence_detected", True, record["silence_detected"]))

    passed = all(expected == actual for _, expected, actual in checks)
    return record, checks, passed


def build_report():
    results = [(_run_case(case) + (case,)) for case in CLEANUP_TEST_CASES]
    total = len(results)
    passed_count = sum(1 for _, _, passed, _ in results if passed)

    lines = []
    lines.append("# Transcript Cleanup Test Report")
    lines.append("")
    lines.append(
        "**What this tests:** the normalization and cleanup rules in "
        "`screening_ai/transcript_normalizer.py` and `transcript_processor.py`, "
        "against realistic speech-to-text-style text (filler words, spoken "
        "numbers, hedging, negation, silence, partial/interrupted answers)."
    )
    lines.append("")
    lines.append(
        "**What this does NOT test:** real speech-to-text accuracy. No STT "
        "provider is integrated anywhere in this repo yet, and no real phone "
        "call has ever happened (`screening_ai/call_handler.py` is still the "
        "Day 1 stub), so there is no audio-to-text accuracy to measure. Every "
        "input below is already text, standing in for what a provider would "
        "eventually return."
    )
    lines.append("")
    lines.append(f"**Result: {passed_count}/{total} cases passed.**")
    lines.append("")
    lines.append("| # | Case | Input (as STT would return it) | Result |")
    lines.append("|---|------|-------------------------------|--------|")

    for i, (record, checks, passed, case) in enumerate(results, start=1):
        status = "PASS" if passed else "FAIL"
        raw_display = case["raw_text"] if case["raw_text"].strip() else "(empty / silence)"
        lines.append(f"| {i} | {case['label']} | `{raw_display}` | {status} |")

    lines.append("")
    lines.append("## Detail per case")
    lines.append("")
    for i, (record, checks, passed, case) in enumerate(results, start=1):
        lines.append(f"### {i}. {case['label']} — {'PASS' if passed else 'FAIL'}")
        lines.append(f"- Input: `{case['raw_text'] if case['raw_text'].strip() else '(empty)'}`")
        lines.append(f"- Answer type: `{case['expected_answer_type']}`")
        lines.append(f"- normalized_text: `{record['normalized_text']}`")
        lines.append(f"- parsed_value: `{record['parsed_value']}`")
        if record["silence_detected"]:
            lines.append("- silence_detected: true")
        if record["partial_answer"]:
            lines.append("- partial_answer: true")
        if record["interrupted"]:
            lines.append("- interrupted: true")
        for check_name, expected, actual in checks:
            mark = "ok" if expected == actual else "MISMATCH"
            lines.append(f"- check `{check_name}`: expected `{expected}`, got `{actual}` -- {mark}")
        lines.append("")

    lines.append("## Honest gaps")
    lines.append("")
    lines.append(
        "- Confidence-level handling is untested here beyond the silence case "
        "(forcing it to 0.0) -- there's still no real STT provider to confirm "
        "what a given confidence number means in practice (same gap "
        "TRANSCRIPT_DATA_ARCHITECTURE.md already flagged)."
    )
    lines.append(
        "- `partial` and `interrupted` are tested only as explicit flags passed "
        "in -- there is no real call-event stream yet to detect either "
        "condition on its own, so this report cannot claim the module detects "
        "them automatically, only that it carries the flag through correctly "
        "once something else reports it."
    )
    lines.append(
        "- Negation handling in the `list` rule is a literal word-window check "
        "(a few words before a skill), not real sentence understanding -- a "
        "negation phrased further from the skill name than that window would "
        "be missed."
    )
    lines.append("")

    return "\n".join(lines), passed_count, total


if __name__ == "__main__":
    report_text, passed_count, total = build_report()
    with open("TRANSCRIPT_CLEANUP_TEST_REPORT.md", "w") as f:
        f.write(report_text)
    print(f"{passed_count}/{total} cases passed. Report written to TRANSCRIPT_CLEANUP_TEST_REPORT.md")