# Zecpath AI System

The AI side of Zecpath — five services that read resumes, run screening 
calls, run interviews, and score candidates.

## Folder layout

| Folder | What it does |
|---|---|
| `parsers/` | Turns a raw resume into structured data |
| `ats_engine/` | Scores a parsed resume against job requirements |
| `screening_ai/` | Triggers and tracks the AI screening call |
| `interview_ai/` | Runs the AI video interview session |
| `scoring/` | Combines all scores into one final recommendation |
| `utils/` | Shared logging and config code |
| `tests/` | Tests for each service above |
| `data/` | Local sample resumes/videos for development |

## Setup

\`\`\`bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env
pytest
\`\`\`

## Logging

Every module logs through `utils/logger.py` instead of using `print()`. 
Logs go to the console and to `logs/zecpath_ai.log`.

## Tests

Run `pytest` to check everything still works.
## Resume text extraction 

Turns a PDF or DOCX resume into clean plain text, ready for the AI to read.

| File in `parsers/` | What it does |
|---|---|
| `docx_reader.py` | Reads Word files, including tables and bullet lists |
| `pdf_reader.py` | Reads PDFs, handles two-column layouts and re-joins wrapped lines |
| `text_cleaner.py` | Removes noise, standardises bullets, section headings and capitalisation |
| `extractor.py` | Main entry point: picks the right reader, cleans the text, saves JSON |

Run it on a whole folder:

```bash
python -c "from parsers.extractor import extract_folder; extract_folder('data/resumes', 'data/extracted')"
```

Each resume becomes one JSON file in `data/extracted/` with `source_file`,
`file_type`, `status`, `extracted_at`, `char_count`, `line_count` and `text`.
`status` is `ok`, or `no_text_found` if the file had nothing to read.

Run the tests and save the results to `logs/test_results.txt`:

```bash
python run_tests.py
```

Known limits:
- Scanned (image-only) PDFs are flagged as `no_text_found`. Reading them would need OCR, which is not built yet.
- Wrapped-line and two-column detection are rules of thumb, tuned on the 24 sample resumes in `data/resumes/`. An unusual layout may need the rules adjusted.
## JD parsing 

Turns a plain-text job description into a structured job requirement
object, matching the schema from Day 4. Full documentation: `JD_PARSING.md`.

Run it on a whole folder:

```bash
python -c "from parsers.jd_parser import parse_folder; parse_folder('data/job_descriptions', 'data/parsed_jds')"
```
## Resume section classification 

Splits cleaned resume text (from Day 5) into labeled sections: SUMMARY,
SKILLS, EXPERIENCE, EDUCATION, CERTIFICATIONS, PROJECTS. Full accuracy
report: `SECTION_ACCURACY_REPORT.md`.

```bash
python -c "from parsers.section_tagger import tag_folder; tag_folder('data/extracted', 'data/segmented')"
```
## Skill extraction engine

Pulls the actual skills out of a resume's section-tagged text (from Day 8) using a master dictionary of technical, business, and creative skills, with synonym matching, skill-stack expansion (MERN, MEAN, LAMP), and fuzzy matching for spelling mistakes the dictionary doesn't already list.

Files: `skills_engine/skill_dictionary.py` (the master dictionary and stacks), `skills_engine/skill_extractor.py` (finds skills in a block of text), `skills_engine/skill_profile.py` (weights matches by which resume section they came from and deduplicates across sections), `skills_engine/skill_tagger.py` (runs the whole thing across a folder).

Confidence per skill depends on how it was found — exact name match scores highest, a known synonym or stack-inferred mention next, a fuzzy spelling match lowest — multiplied by how much we trust the section it came from (the SKILLS section itself outweighs a passing mention buried in EXPERIENCE text).

Three real bugs were caught while testing against actual resumes, not invented ones: a trailing sentence period was silently breaking fuzzy matching ("Pyhton." never matched "Python"), "Six Sigma" was fuzzy-matching "Figma" (fixed by requiring a fuzzy match to start with the same letter — real typos almost never change the first letter), and "Tailwind CSS" was being double-counted as a separate standalone "CSS" skill (fixed by tracking which part of the text a longer match already claims). All three are regression-tested.

Run it:
```
python -c "from skills_engine.skill_tagger import tag_folder; tag_folder('data/segmented', 'data/skills')"
python run_tests.py
```
## Experience parsing & relevance engine

Parses a resume's EXPERIENCE section (from Day 8) into structured job entries — company, title, start/end dates — computes total experience (merging overlapping date ranges so dual roles aren't double-counted), flags gaps and overlaps between jobs, and scores how relevant a candidate's past roles are to a specific job description.

Files: `experience_engine/experience_parser.py` (extracts company/title/dates from messy real-world header formats like "Title, Company — Date – Date" and "Title at Company, Location, from Date to Date"), `experience_engine/experience_calculator.py` (total experience, gap/overlap detection), `experience_engine/relevance_scorer.py` (role-to-role similarity via Day 6's role synonyms, plus skill overlap via Day 9's skill profiles), `experience_engine/experience_tagger.py` (runs it all across a folder).

Relevance combines two signals: role similarity (1.0 for an exact synonym match via Day 6, otherwise a word-overlap fallback) and skill overlap against a JD's mandatory required skills (from Day 9). Ran against all 27 resumes scored for a real Software Engineer JD, Rohan Mehta's actual software engineering background scored highest (0.62); unrelated profiles (sales, HR, mechanical engineering) correctly scored 0.

Known limit: the word-overlap fallback for role similarity can give a small nonzero score to titles that share only a generic word like "Engineer" (e.g. "Design Engineer" vs "Software Engineer") without the roles being functionally related. This is honest word overlap, not a synonym match, and is visible in the `role_relevance` field rather than hidden in a single blended score.

Run it:
```
python -c "from experience_engine.experience_tagger import tag_folder; tag_folder('data/segmented', 'data/experience')"
python run_tests.py
```
## Education & certification parsing engine

 Extracts structured academic data from a resume's EDUCATION and CERTIFICATIONS sections (from Day 8's segmentation).

- `education_engine/education_parser.py` — parses degree type, field of study, institution, and graduation year from lines like `"B.Tech, Computer Science — Visvesvaraya Technological University (2021)"`. Handles both em-dash and pipe separators, and lines with or without a comma between degree and field. Also parses certification lines (bullet prefix optional, year optional).
- `education_engine/certification_tagger.py` — categorizes each certification into Technology, Finance, Healthcare, Engineering, Design, or Business using keyword matching, falling back to "Uncategorized" honestly rather than guessing.
- `education_engine/education_tagger.py` — runs both parsers across a whole folder of Day 8's segmented resumes and saves one structured academic profile per resume.
- `education_engine/education_relevance.py` — scores how relevant a candidate's field of study is to a target role by reusing Day 10's `role_similarity`, and flags which certifications match a target role's relevant categories.

**A real bug found while testing:** a pipe-separated line with two pipes (`"B.Sc Statistics | Loyola College | 2020"`) left a dangling `|` on the end of the institution name, because the year-removal step stripped the digits but not the leftover separator next to them. Fixed by trimming dangling separator characters after the year is removed.

**Known limits:**
- Lines split across two entries by a two-column PDF layout (e.g. degree on one line, institution+year on the next) are honestly skipped rather than stitched back together.
- Prose-style "no headings" resumes that describe education/certifications in full sentences (e.g. "B.Com from Madras University, completed in 2018.") are also skipped rather than guessed at.
- Field-relevance scoring is pure word overlap — a field like "Computer Science" scores 0 against a role like "Software Engineer" even though they're obviously related, because there's no overlapping word. This is a real limitation, not a close call.
- The certification category list is hand-picked from what's actually in the 27 sample resumes (Technology, Finance, Healthcare, Engineering, Design, Business) — an uncommon certification domain not covered by these keywords falls into "Uncategorized".

Run it:
```
python -c "from education_engine.education_tagger import tag_folder; tag_folder('data/segmented', 'data/education')"
python run_tests.py
```
## Semantic matching engine

Day 12 moves beyond Day 9's exact/fuzzy keyword matching to compare the actual meaning-bearing text of a resume against a job description.

**A deliberate design choice, stated plainly:** "embeddings" usually implies a neural model (e.g. sentence-transformers), which would mean a new dependency and a model download. To keep this stdlib-only like every other engine, Day 12 uses a from-scratch **TF-IDF vector space model with cosine similarity** instead — a classic, well-understood information-retrieval technique. It's simpler than real embeddings and that's acknowledged here rather than oversold.

- `semantic_engine/text_vectorizer.py` — a from-scratch TF-IDF implementation (`re`, `math`, `collections.Counter` only). `fit()` learns term weights from a corpus of real resume + JD text; `transform()` turns any text into a sparse weighted vector.
- `semantic_engine/similarity_scorer.py` — cosine similarity between two vectors.
- `semantic_engine/semantic_matcher.py` — builds a shared vectorizer across all real resume and JD text, then compares a resume's SKILLS/EXPERIENCE/PROJECTS text against a JD's required skills, responsibilities, and full text (JDs have no dedicated "project description" field, so the full JD text is the closest honest proxy for that comparison).
- `semantic_engine/matching_report.py` — scores every resume against every JD, saves one ranked file per resume, and builds the matching accuracy report.

**Two real bugs found while validating against real data:**
1. **Duplicate JD titles collapsed two different jobs into one.** `sde_ii.json` and `software_developer.json` are both titled "Software Engineer." Filtering matches by title merged their results together, so a "top match" couldn't be traced to a specific JD. Fixed by keying every match on the JD's filename instead of its title.
2. **`.docx` and `.pdf` versions of the same resume overwrote each other's output.** `Path("alice.docx").stem` and `Path("alice.pdf").stem` both evaluate to `"alice"`, so the tagger silently wrote both to the same output file — 27 resumes went in, only 17 files came out before this was caught. Fixed by keeping the extension in the output filename (`alice_docx_matches.json` vs `alice_pdf_matches.json`).

**Threshold, chosen from real data, not guessed:** across all 216 resume×JD pairs, the score distribution is mean 0.049, median 0.017 — most pairs are genuinely unrelated. Real matches (verified by hand) cluster from ~0.10 up to 0.6. **0.10** is used as the "good match" cutoff.

**Validation across job types** (real results): Divya Menon (MBA in Marketing, Google Ads/HubSpot certified) scores highest of all 216 pairs — 0.6 — against the Digital Marketing JD. Anjali Suresh (MBA in Human Resources) ranks first against the HR Manager JD. Ananya Rao (React/JS/TypeScript skills) outranks Rohan Mehta (Java/Spring Boot) against a JavaScript-stack Software Engineer JD, correctly reflecting the closer stack match.

**Known limits:**
- TF-IDF is a bag-of-words model — it has no notion of synonyms or paraphrasing beyond shared vocabulary. "Built web applications" and "Developed online software" would score lower than their actual meaning overlap deserves.
- Only 2 of 27 resumes have a PROJECTS section, so the projects-similarity comparison is validated on a small sample.
- The vectorizer is fit once on the current 27 resumes + 8 JDs. Adding new resumes or JDs later would need a re-fit to stay consistent, not an incremental update.

Run it:
```
python -c "from semantic_engine.matching_report import compute_all_matches, tag_folder, build_accuracy_report; import json; tag_folder('data/segmented', 'data/parsed_jds', 'data/semantic_matches'); matches = compute_all_matches('data/segmented', 'data/parsed_jds'); json.dump(build_accuracy_report(matches), open('data/semantic_matches/_accuracy_report.json', 'w', encoding='utf-8'), indent=2)"
python run_tests.py
```
## ATS scoring engine

Combines everything built so far into one explainable, weighted candidate score — the capstone of Days 9–12, not a parallel engine.

- `scoring_engine/score_components.py` — four 0–1 component scores, each reusing an earlier engine's real output directly rather than reimplementing logic: skill match (Day 9's skill profile vs. a JD's required skills, mandatory skills weighted fully, nice-to-haves at half), experience relevance (Day 10's `role_similarity` + skill-overlap scorer, reused as-is), education alignment (Day 11's field-of-study relevance), semantic similarity (Day 12's precomputed TF-IDF score, looked up rather than recomputed).
- `scoring_engine/weight_profiles.py` — three weight profiles (technical / education-heavy / default) mapped to the 8 real JDs by role category, each summing to 1.0.
- `scoring_engine/scoring_engine.py` — combines the four components using the right profile, and handles missing data honestly: a component that can't be computed (e.g. no parsed work history) is excluded entirely, and its weight is redistributed proportionally across whatever components are available — never silently treated as a zero. Also produces a plain-English explanation of exactly how a score was reached.
- `scoring_engine/candidate_score_generator.py` — scores every resume against every JD and saves one ranked file per resume.

**A deliberate scope decision:** Day 3's `ats_engine/ats_scorer.py` is a simple early scaffold (flat skill lists, plain containment match) whose input shape doesn't match what Days 9–12 actually produce now. Rather than force today's real data into that old shape, Day 13 is a new, separate `scoring_engine/` module. The old file is left in place as historical scaffold.

**A scope boundary, stated honestly:** education alignment uses only field-of-study relevance. Matching a certification's domain to a role's domain was considered but left out — it would need a hand-built role-to-category mapping with too little real data (27 resumes) to validate it confidently. A certification like "AWS Certified" already contributes indirectly anyway, since Day 9's skill dictionary picks up "AWS" as a skill in its own right.

**Validated against real data, not just hand-checked math:** Rohan Mehta's final score vs. the SDE II JD comes to exactly 0.2606 — hand-calculated from the four real component scores (0.2, 0.625, 0.0, 0.0976) and confirmed by the test suite. Divya Menon's score against the Digital Marketing JD (0.3366) is nearly 100x every other JD she was scored against — the whole pipeline agreeing clearly on one obviously-correct answer.

**Known limits:**
- Certification-to-role-domain relevance isn't factored into education alignment (see above).
- Weight profiles are assigned per JD by hand, based on role category judgment — not learned or tuned against labeled outcome data, since none exists.
- A component scoring a real 0.0 (e.g. "Computer Science" vs. "Software Engineer" under Day 11's word-overlap limit) is treated as an available, meaningful score — not missing data — which is correct behavior, but means a genuine word-overlap gap still drags the final score down rather than being excluded.

Run it:
```
python -c "from scoring_engine.candidate_score_generator import score_all_resumes; score_all_resumes('data/segmented', 'data/skills', 'data/experience', 'data/education', 'data/semantic_matches', 'data/parsed_jds', 'data/candidate_scores')"
python run_tests.py
```