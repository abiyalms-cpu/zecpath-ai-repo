import glob
import json

from semantic_engine.text_vectorizer import TfidfVectorizer
from semantic_engine.similarity_scorer import text_similarity


def build_corpus_and_fit(segmented_dir, jds_dir):
    """Fits one shared TfidfVectorizer across all real resume and JD text, so every
    comparison happens in the same vector space rather than refitting per pair."""
    corpus = []
    for path in glob.glob(f"{jds_dir}/*.json"):
        jd = json.load(open(path, encoding="utf-8"))
        corpus.append(jd.get("normalized_text", ""))

    for path in glob.glob(f"{segmented_dir}/*.json"):
        record = json.load(open(path, encoding="utf-8"))
        sections = record.get("sections") or {}
        text = " ".join(
            sections.get("SKILLS", []) + sections.get("EXPERIENCE", []) + sections.get("PROJECTS", [])
        )
        corpus.append(text)

    return TfidfVectorizer().fit(corpus)


def resume_text_blocks(sections):
    sections = sections or {}
    return {
        "skills": " ".join(sections.get("SKILLS", [])),
        "experience": " ".join(sections.get("EXPERIENCE", [])),
        "projects": " ".join(sections.get("PROJECTS", [])),
    }


def jd_text_blocks(jd_record):
    skill_names = [s["name"] for s in jd_record.get("required_skills", [])]
    return {
        "skills": " ".join(skill_names),
        "experience": " ".join(jd_record.get("responsibilities", [])),
        # JDs have no dedicated "project description" field — the full normalized
        # text is the closest honest proxy to compare a resume's PROJECTS text against.
        "projects": jd_record.get("normalized_text", ""),
    }


def score_match(vectorizer, resume_sections, jd_record):
    r_blocks = resume_text_blocks(resume_sections)
    j_blocks = jd_text_blocks(jd_record)

    scores = {}
    scores["skills_similarity"] = text_similarity(vectorizer, r_blocks["skills"], j_blocks["skills"])
    scores["experience_similarity"] = text_similarity(vectorizer, r_blocks["experience"], j_blocks["experience"])

    if r_blocks["projects"].strip():
        scores["projects_similarity"] = text_similarity(vectorizer, r_blocks["projects"], j_blocks["projects"])
    else:
        scores["projects_similarity"] = None  # no PROJECTS section — not scored, not guessed at

    present_scores = [v for v in scores.values() if v is not None]
    scores["overall_similarity"] = round(sum(present_scores) / len(present_scores), 4) if present_scores else 0.0

    return scores