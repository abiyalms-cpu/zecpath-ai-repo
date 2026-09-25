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