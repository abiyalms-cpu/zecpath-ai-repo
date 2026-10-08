import glob
import json
from pathlib import Path

from semantic_engine.semantic_matcher import build_corpus_and_fit, score_match


def compute_all_matches(segmented_dir, jds_dir):
    """Scores every resume against every JD. Returns a flat list of match records —
    the raw material for both the threshold decision and the accuracy report."""
    vectorizer = build_corpus_and_fit(segmented_dir, jds_dir)

    resumes = []
    for path in glob.glob(f"{segmented_dir}/*.json"):
        record = json.load(open(path, encoding="utf-8"))
        resumes.append((record.get("source_file", Path(path).stem), record.get("sections") or {}))

    jds = []
    for path in glob.glob(f"{jds_dir}/*.json"):
        jd = json.load(open(path, encoding="utf-8"))
        jd_key = Path(path).stem  # filename is unique; title is not (two JDs are both "Software Engineer")
        jds.append((jd_key, jd.get("title", jd_key), jd))

    matches = []
    for resume_name, sections in resumes:
        for jd_key, jd_title, jd_record in jds:
            scores = score_match(vectorizer, sections, jd_record)
            matches.append({"resume": resume_name, "jd_file": jd_key, "jd_title": jd_title, **scores})

    return matches


def top_matches_for_jd(matches, jd_file, top_n=5):
    """Filter by jd_file (the unique filename key), not jd_title — titles can collide."""
    filtered = [m for m in matches if m["jd_file"] == jd_file]
    return sorted(filtered, key=lambda m: -m["overall_similarity"])[:top_n]


def score_distribution(matches):
    scores = sorted(m["overall_similarity"] for m in matches)
    n = len(scores)
    return {
        "min": scores[0],
        "max": scores[-1],
        "mean": round(sum(scores) / n, 4),
        "median": scores[n // 2],
    }
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

GOOD_MATCH_THRESHOLD = 0.10  # chosen from the real score spread: mean 0.049, median 0.017,
                              # genuine matches observed from ~0.10 up to 0.6


def tag_folder(segmented_dir, jds_dir, output_dir):
    """Scores every resume against every JD and saves one ranked file per resume —
    a per-candidate view of which jobs they're the best semantic fit for."""
    matches = compute_all_matches(segmented_dir, jds_dir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    by_resume = {}
    for m in matches:
        by_resume.setdefault(m["resume"], []).append(m)

    count = 0
    for resume_name, resume_matches in by_resume.items():
        ranked = sorted(resume_matches, key=lambda m: -m["overall_similarity"])
        safe_name = resume_name.replace(".", "_")  # keep .docx vs .pdf distinct in the filename
        out_name = f"{safe_name}_matches.json"
        out_path = Path(output_dir) / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"resume": resume_name, "matches": ranked}, f, indent=2)
        logger.info(f"Saved {out_path}")
        count += 1

    logger.info(f"Tagged {count} resumes")
    return count


def build_accuracy_report(matches, top_n=3, threshold=GOOD_MATCH_THRESHOLD):
    """One deliverable the brief asks for directly: for every JD, which resumes rank
    highest, and how many pairs clear the 'good match' threshold."""
    jd_keys = sorted({(m["jd_file"], m["jd_title"]) for m in matches})
    report = {
        "threshold": threshold,
        "distribution": score_distribution(matches),
        "per_jd": [],
    }
    for jd_file, jd_title in jd_keys:
        top = top_matches_for_jd(matches, jd_file, top_n=top_n)
        above_threshold = sum(1 for m in matches if m["jd_file"] == jd_file and m["overall_similarity"] >= threshold)
        report["per_jd"].append({
            "jd_file": jd_file,
            "jd_title": jd_title,
            "top_matches": [{"resume": m["resume"], "overall_similarity": m["overall_similarity"]} for m in top],
            "resumes_above_threshold": above_threshold,
        })
    return report