"""
Tests for the Day 9 skill extraction engine: direct/synonym/stack/fuzzy
matching, section-weighted scoring and dedup, and the folder-level runner.
"""

import json

from skills_engine.skill_extractor import find_skills_in_text
from skills_engine.skill_profile import build_skill_profile
from skills_engine.skill_tagger import tag_skills, tag_folder


def test_exact_canonical_match_is_found():
    matches = find_skills_in_text("I have strong Python and Git experience.")
    assert "Python" in matches
    assert matches["Python"]["match_type"] == "exact_canonical"
    assert "Git" in matches


def test_synonym_maps_to_canonical_name():
    matches = find_skills_in_text("Built the backend with NodeJS.")
    assert "Node.js" in matches
    assert matches["Node.js"]["match_type"] == "exact_synonym"


def test_mern_stack_expands_to_its_four_skills():
    matches = find_skills_in_text("Built a MERN stack application.")
    for skill in ["MongoDB", "Express.js", "React", "Node.js"]:
        assert skill in matches
        assert matches[skill]["match_type"] == "stack_inferred"


def test_known_spelling_variant_is_recognised():
    matches = find_skills_in_text("Worked mostly in phyton for data scripts.")
    assert "Python" in matches
    assert matches["Python"]["match_type"] == "spelling_variant"


def test_unlisted_typo_is_caught_by_fuzzy_matching():
    matches = find_skills_in_text("Comfortable coding in Pyhton.")
    assert "Python" in matches
    assert matches["Python"]["match_type"] == "fuzzy_match"


def test_inflected_real_word_is_not_a_false_fuzzy_match():
    # Regression test: "reacted"/"designed" are ordinary English words,
    # not misspellings of "React"/"Design".
    matches = find_skills_in_text("I reacted quickly and designed a fix.")
    assert "React" not in matches
    assert "UI/UX Design" not in matches


def test_sigma_does_not_falsely_match_figma():
    # Regression test: "Six Sigma Green Belt" was fuzzy-matching "Figma"
    # before the first-letter guard was added.
    matches = find_skills_in_text("Six Sigma Green Belt certified in 2022.")
    assert "Figma" not in matches


def test_tailwind_css_is_not_also_counted_as_plain_css():
    # Regression test: "css" inside "Tailwind CSS" was double-counting as
    # a separate standalone CSS skill.
    matches = find_skills_in_text("Skills: Tailwind CSS, React, Git")
    assert "Tailwind CSS" in matches
    assert "CSS" not in matches


def test_skill_in_skills_section_outranks_same_skill_in_experience_only():
    sections = {
        "SKILLS": ["Python, Git"],
        "EXPERIENCE": ["Used Python daily to build pipelines."],
    }
    profile = build_skill_profile(sections)
    python_entry = next(e for e in profile if e["skill"] == "Python")
    assert python_entry["confidence"] == 0.97  # SKILLS weight is 1.0
    assert set(python_entry["found_in"]) == {"SKILLS", "EXPERIENCE"}


def test_same_skill_across_sections_is_deduplicated_into_one_entry():
    sections = {
        "SKILLS": ["React"],
        "PROJECTS": ["Built a React app."],
        "SUMMARY": ["React developer."],
    }
    profile = build_skill_profile(sections)
    react_entries = [e for e in profile if e["skill"] == "React"]
    assert len(react_entries) == 1
    assert len(react_entries[0]["found_in"]) == 3


def test_category_is_attached_from_the_dictionary():
    sections = {"SKILLS": ["Figma, Sales"]}
    profile = build_skill_profile(sections)
    by_skill = {e["skill"]: e for e in profile}
    assert by_skill["Figma"]["category"] == "creative"
    assert by_skill["Sales"]["category"] == "business"


def test_resume_with_no_text_is_skipped_not_guessed():
    record = {"source_file": "blank.pdf", "method": "skipped", "sections": {}}
    result = tag_skills(record)
    assert result["method"] == "skipped"
    assert result["skills"] == []
    assert result["total_skills_found"] == 0


def test_tag_folder_saves_one_json_per_resume(tmp_path):
    segmented_dir = tmp_path / "segmented"
    output_dir = tmp_path / "skills"
    segmented_dir.mkdir()

    sample = {
        "source_file": "sample.docx",
        "method": "heading",
        "sections": {"SKILLS": ["Python, Git"]},
    }
    with open(segmented_dir / "sample_sections.json", "w", encoding="utf-8") as f:
        json.dump(sample, f)

    count = tag_folder(str(segmented_dir), str(output_dir))

    assert count == 1
    out_file = output_dir / "sample_skills.json"
    assert out_file.exists()

    with open(out_file, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["total_skills_found"] == 2