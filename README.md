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