# JD Parsing System

Turns a plain-text job description into a structured job requirement object:
role, required experience, education preference, and skills — normalized
against synonym tables so different wordings collapse into one form.

## How it works

| File | Job |
|---|---|
| `parsers/jd_synonyms.py` | Lookup tables: variant wording → one canonical role or skill |
| `parsers/jd_cleaner.py` | Standardises bullets, spacing, and section headings (`Must Have`, `What You'll Need` → `REQUIREMENTS`) |
| `parsers/jd_extractor.py` | Pulls out role, experience range, education, and skills from cleaned text |
| `parsers/jd_parser.py` | Ties it together: clean → extract → save as JSON |

## Running it

```bash
python -c "from parsers.jd_parser import parse_folder; parse_folder('data/job_descriptions', 'data/parsed_jds')"
```

Each JD becomes one JSON file with `title`, `experience_required`,
`education_requirement`, `required_skills`, and `normalized_text`.

## Role and skill synonym detection

Two JDs worded completely differently both resolve to the same role:

- `software_developer.txt`: `Job Title: Software Developer` → **Software Engineer**
- `sde_ii.txt`: "We're hiring an **SDE II**..." (no title label at all) → **Software Engineer**

Same for skills — `React`, `ReactJS`, and `React.js` all collapse to **React**.

## Real bugs found while building this

Matching text by "does this phrase appear anywhere" caused three false
positives, all from the same root cause: no word-boundary check.

- **"Java" matched inside "JavaScript"** — a JD requiring only JavaScript
  wrongly also showed Java as a required skill.
- **"HRIS" matched inside "Thrissur"** — a Kerala location line falsely
  triggered an HR software skill match.
- **"MBA" matched inside "Mumbai"** — a location line was picked as the
  education requirement instead of the actual degree line further down.

Fixed by requiring a real word boundary (`\bMBA\b`, not just `"MBA" in text`)
before counting anything as a match.

## Known limits

- The skill vocabulary is a fixed list (`jd_synonyms.py`). A skill not in
  that list (e.g. a JD mentioning "NoSQL databases" generically) won't be
  picked up, even though it's a real requirement.
- Experience extraction takes the *first* years-of-experience mention in
  the text as the primary requirement. This works for every sample JD
  tested, but a JD structured very differently could pick the wrong number.
- Education detection returns the first matching line, not every degree
  mentioned, so a JD offering several acceptable degrees only surfaces one.