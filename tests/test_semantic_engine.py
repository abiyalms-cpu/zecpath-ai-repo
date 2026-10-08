import json
from pathlib import Path

from semantic_engine.text_vectorizer import tokenize, TfidfVectorizer
from semantic_engine.similarity_scorer import cosine_similarity, text_similarity
from semantic_engine.semantic_matcher import resume_text_blocks, jd_text_blocks, score_match
from semantic_engine.matching_report import (
    compute_all_matches,
    top_matches_for_jd,
    score_distribution,
    tag_folder,
    build_accuracy_report,
)


# ---------- tokenizer ----------

def test_tokenize_lowercases_and_splits_on_punctuation():
    assert tokenize("Python, Java!") == ["python", "java"]


def test_tokenize_keeps_dotted_terms_like_nodejs():
    assert "node.js" in tokenize("I know Node.js well")


def test_tokenize_empty_text_returns_empty_list():
    assert tokenize("") == []
    assert tokenize(None) == []


# ---------- TF-IDF vectorizer ----------

def test_rare_term_gets_higher_weight_than_common_term():
    corpus = ["python python python", "python and java", "python and sql", "python and html"]
    vec = TfidfVectorizer().fit(corpus)
    result = vec.transform("python java")
    # "java" appears in only 1 of 4 docs, "python" appears in all 4 — java should weigh more
    assert result["java"] > result["python"]


def test_out_of_vocabulary_term_is_ignored_not_guessed():
    vec = TfidfVectorizer().fit(["python and java"])
    result = vec.transform("python and zorblax")
    assert "zorblax" not in result


def test_empty_text_transforms_to_empty_vector():
    vec = TfidfVectorizer().fit(["python java"])
    assert vec.transform("") == {}


# ---------- cosine similarity ----------

def test_identical_vectors_have_similarity_one():
    v = {"python": 0.8, "java": 0.4}
    assert round(cosine_similarity(v, v), 4) == 1.0


def test_disjoint_vectors_have_similarity_zero():
    assert cosine_similarity({"python": 1.0}, {"excel": 1.0}) == 0.0


def test_empty_vector_has_similarity_zero():
    assert cosine_similarity({}, {"python": 1.0}) == 0.0


def test_text_similarity_uses_a_fitted_vectorizer():
    vec = TfidfVectorizer().fit(["python developer job", "excel marketing job"])
    score = text_similarity(vec, "python developer", "excel marketing")
    assert 0.0 <= score < 1.0


# ---------- resume / JD text block extraction ----------

def test_resume_text_blocks_pulls_skills_experience_projects():
    sections = {"SKILLS": ["Python, SQL"], "EXPERIENCE": ["Did things"], "PROJECTS": ["Built a thing"]}
    blocks = resume_text_blocks(sections)
    assert blocks["skills"] == "Python, SQL"
    assert blocks["experience"] == "Did things"
    assert blocks["projects"] == "Built a thing"


def test_resume_text_blocks_handles_missing_sections():
    assert resume_text_blocks({}) == {"skills": "", "experience": "", "projects": ""}
    assert resume_text_blocks(None) == {"skills": "", "experience": "", "projects": ""}


def test_jd_text_blocks_pulls_skill_names_and_responsibilities():
    jd = {
        "required_skills": [{"name": "Python"}, {"name": "SQL"}],
        "responsibilities": ["Write code", "Fix bugs"],
        "normalized_text": "full jd text",
    }
    blocks = jd_text_blocks(jd)
    assert blocks["skills"] == "Python SQL"
    assert blocks["experience"] == "Write code Fix bugs"
    assert blocks["projects"] == "full jd text"


# ---------- score_match ----------

def test_score_match_skips_projects_when_resume_has_none():
    vec = TfidfVectorizer().fit(["python developer", "python jd"])
    sections = {"SKILLS": ["Python"], "EXPERIENCE": ["Built stuff"]}
    jd = {"required_skills": [{"name": "Python"}], "responsibilities": ["Build stuff"], "normalized_text": "jd"}
    result = score_match(vec, sections, jd)
    assert result["projects_similarity"] is None
    assert result["overall_similarity"] == round(
        (result["skills_similarity"] + result["experience_similarity"]) / 2, 4
    )


def test_score_match_includes_projects_when_present():
    vec = TfidfVectorizer().fit(["python developer project", "python jd project"])
    sections = {"SKILLS": ["Python"], "EXPERIENCE": ["Built stuff"], "PROJECTS": ["A project"]}
    jd = {"required_skills": [{"name": "Python"}], "responsibilities": ["Build stuff"], "normalized_text": "jd project"}
    result = score_match(vec, sections, jd)
    assert result["projects_similarity"] is not None


# ---------- matching report (real-data-shaped) ----------

def _fake_segmented_dir(tmp_path, records):
    d = tmp_path / "segmented"
    d.mkdir()
    for name, record in records.items():
        (d / f"{name}_sections.json").write_text(json.dumps(record), encoding="utf-8")
    return d


def _fake_jds_dir(tmp_path, jds):
    d = tmp_path / "jds"
    d.mkdir()
    for name, jd in jds.items():
        (d / f"{name}.json").write_text(json.dumps(jd), encoding="utf-8")
    return d


def test_compute_all_matches_produces_resume_times_jd_pairs(tmp_path):
    segmented_dir = _fake_segmented_dir(tmp_path, {
        "alice": {"source_file": "alice.docx", "sections": {"SKILLS": ["Python"], "EXPERIENCE": ["Coded"]}},
        "bob": {"source_file": "bob.docx", "sections": {"SKILLS": ["Sales"], "EXPERIENCE": ["Sold things"]}},
    })
    jds_dir = _fake_jds_dir(tmp_path, {
        "sde": {"title": "Software Engineer", "required_skills": [{"name": "Python"}], "responsibilities": ["Code"], "normalized_text": "code"},
        "sales": {"title": "Sales Rep", "required_skills": [{"name": "Sales"}], "responsibilities": ["Sell"], "normalized_text": "sell"},
    })
    matches = compute_all_matches(str(segmented_dir), str(jds_dir))
    assert len(matches) == 4  # 2 resumes x 2 JDs


def test_top_matches_for_jd_does_not_collide_on_duplicate_titles(tmp_path):
    # Regression: two JDs sharing the same title used to get merged together when
    # filtering by title. Filtering by jd_file (the filename) must keep them separate.
    segmented_dir = _fake_segmented_dir(tmp_path, {
        "alice": {"source_file": "alice.docx", "sections": {"SKILLS": ["Python"], "EXPERIENCE": ["Coded"]}},
    })
    jds_dir = _fake_jds_dir(tmp_path, {
        "sde_one": {"title": "Software Engineer", "required_skills": [{"name": "Python"}], "responsibilities": [], "normalized_text": "python"},
        "sde_two": {"title": "Software Engineer", "required_skills": [{"name": "Excel"}], "responsibilities": [], "normalized_text": "excel"},
    })
    matches = compute_all_matches(str(segmented_dir), str(jds_dir))
    sde_one_matches = top_matches_for_jd(matches, "sde_one")
    sde_two_matches = top_matches_for_jd(matches, "sde_two")
    assert len(sde_one_matches) == 1
    assert len(sde_two_matches) == 1
    assert sde_one_matches[0]["overall_similarity"] != sde_two_matches[0]["overall_similarity"]


def test_score_distribution_returns_min_max_mean_median():
    matches = [{"overall_similarity": v} for v in [0.0, 0.2, 0.4, 0.6]]
    dist = score_distribution(matches)
    assert dist["min"] == 0.0
    assert dist["max"] == 0.6


def test_tag_folder_keeps_docx_and_pdf_versions_as_separate_files(tmp_path):
    # Regression: Path(resume_name).stem collapsed "alice.docx" and "alice.pdf" into
    # the same output filename, silently overwriting one with the other.
    segmented_dir = _fake_segmented_dir(tmp_path, {
        "alice_docx": {"source_file": "alice.docx", "sections": {"SKILLS": ["Python"]}},
        "alice_pdf": {"source_file": "alice.pdf", "sections": {"SKILLS": ["Python"]}},
    })
    jds_dir = _fake_jds_dir(tmp_path, {
        "sde": {"title": "Software Engineer", "required_skills": [{"name": "Python"}], "responsibilities": [], "normalized_text": "python"},
    })
    output_dir = tmp_path / "out"
    count = tag_folder(str(segmented_dir), str(jds_dir), str(output_dir))
    assert count == 2
    assert (output_dir / "alice_docx_matches.json").exists()
    assert (output_dir / "alice_pdf_matches.json").exists()


def test_build_accuracy_report_has_one_entry_per_jd(tmp_path):
    segmented_dir = _fake_segmented_dir(tmp_path, {
        "alice": {"source_file": "alice.docx", "sections": {"SKILLS": ["Python"]}},
    })
    jds_dir = _fake_jds_dir(tmp_path, {
        "sde": {"title": "Software Engineer", "required_skills": [{"name": "Python"}], "responsibilities": [], "normalized_text": "python"},
        "sales": {"title": "Sales Rep", "required_skills": [{"name": "Sales"}], "responsibilities": [], "normalized_text": "sales"},
    })
    matches = compute_all_matches(str(segmented_dir), str(jds_dir))
    report = build_accuracy_report(matches)
    assert len(report["per_jd"]) == 2
    assert "threshold" in report
    assert "distribution" in report