# Transcript Data Architecture

Defines how one AI screening call becomes structured, storable, AI-processable data —
from the moment a candidate's spoken answer comes back from speech-to-text, to how it's
stored, to the shape any future scoring step would read it in. Nothing here runs any
code; the actual AI call, speech-to-text, and answer-scoring are later work (PRD Phase
4/5/16/17) that this schema is built to be ready for.

## Where this fits

## 1. Voice transcript schema

One record per question actually asked and answered. Keyed directly to the question it
answers, so a transcript is never orphaned from the question bank Day 22 already built.

```json
{
  "transcript_id": "sde_ii_karthik_subramaniam.docx_skills_01_a1",
  "candidate_id": "karthik_subramaniam.docx",
  "job_id": "sde_ii",
  "question_id": "sde_ii_skills_01",
  "timestamp": "2026-11-05T10:42:17+00:00",
  "raw_text": "uh yeah so I've worked with react and node js mostly, not so much mongo",
  "normalized_text": "React and Node.js. Not MongoDB.",
  "confidence_level": 0.87,
  "expected_answer_type": "list",
  "language": "en"
}
```

Worked example above uses a real question from the repo
(`data/screening_questions/sde_ii_questions.json` → `sde_ii_skills_01`) and a real
candidate filename from the resume corpus, not invented placeholders.

| Field | Type | Notes |
|---|---|---|
| `transcript_id` | string | `{job_id}_{candidate_id}_{question_id}_{attempt}` — unique per answer, including a retry attempt suffix (a candidate may be asked to repeat an unclear answer) |
| `candidate_id` | string | see Metadata Standards below |
| `job_id` | string | see Metadata Standards below |
| `question_id` | string | see Metadata Standards below |
| `timestamp` | string | see Metadata Standards below |
| `raw_text` | string | exactly what speech-to-text returned, untouched — never overwritten, kept for audit even after normalization |
| `normalized_text` | string | `raw_text` after the rules in section 3, specific to `expected_answer_type` |
| `confidence_level` | float | see Metadata Standards below |
| `expected_answer_type` | string | copied from the matching question object in Day 22's question bank (`free_text`, `number`, `list`, `yes_no`, `currency`, `duration`) — carried onto the transcript itself so nothing reading it later has to re-join back to the question bank just to know how to parse `normalized_text` |
| `language` | string | matches the question's own `language` tag (Day 22) |

## 2. AI screening data structure

One record per full call — the container that groups every transcript from one
candidate's one screening session for one job. This is what a future day would hand to
a decision/scoring step, not individual transcripts one at a time.

```json
{
  "session_id": "sde_ii_karthik_subramaniam.docx_20261105",
  "candidate_id": "karthik_subramaniam.docx",
  "job_id": "sde_ii",
  "started_at": "2026-11-05T10:40:02+00:00",
  "ended_at": "2026-11-05T10:46:55+00:00",
  "call_status": "completed",
  "transcript_ids": [
    "sde_ii_karthik_subramaniam.docx_introduction_01_a1",
    "sde_ii_karthik_subramaniam.docx_education_01_a1",
    "sde_ii_karthik_subramaniam.docx_skills_01_a1"
  ],
  "questions_asked": 10,
  "questions_answered": 9,
  "average_confidence": 0.84
}
```

`call_status` reuses the exact vocabulary `screening_ai/call_handler.py` (Day 1) already
returns (`"queued"`) plus the two states a real call naturally adds once it actually
runs: `"completed"`, `"no_answer"` — kept small and fixed for the same reason Day 22's
`expected_answer_type` list is fixed: whatever reads this next needs to switch on a known,
closed set of values, not freeform text.

## 3. Metadata standards

The five fields the brief asked for by name, each pinned to something that already
exists in this repo rather than invented fresh:

| Field | Standard | Why |
|---|---|---|
| **Candidate ID** | the resume's filename, exactly as it appears in `candidate_scores`, `eligibility`, and every other existing record (e.g. `"karthik_subramaniam.docx"`) | This is the real, already-used identifier everywhere in the live pipeline today. (The separate `CAND-001`-style anonymized ID in `fairness_engine/anonymizer.py` is a different, deliberately anonymized identity used only for bias review — not a general candidate ID. If a transcript ever needs to be anonymized the same way, that mapping can be applied on top of this field; it isn't replaced by it.) |
| **Job ID** | the JD's filename stem, exactly as used in `parsed_jds`, `candidate_scores`, `eligibility`, and `screening_questions` (e.g. `"sde_ii"`) | Same reasoning — this is the real key every other engine already joins on. (The JD's own `job_id` field is `null` in every parsed JD today — Day 6 left it null on purpose, since a real job_id would be assigned by whatever system creates the posting, which doesn't exist yet. The filename stem is what actually functions as the join key across the whole pipeline right now, so the transcript schema follows that reality rather than a field that's never populated.) |
| **Question ID** | Day 22's own question `id` field, unchanged (e.g. `"sde_ii_skills_01"`) | Already globally unique (job + category + number) and already the thing every question in the pipeline is addressed by — no reason to mint a second ID for the same question. |
| **Timestamp** | ISO 8601, UTC, with explicit offset — `datetime.now(timezone.utc).isoformat()` | The exact format `education_tagger.py` and `experience_tagger.py` already use for every record's `extracted_at` field. Matching it means a transcript's timestamp sorts and compares correctly against every other timestamped record without a format conversion step. |
| **Confidence level** | float, 0.0–1.0, one per transcript (not per word) | This has no existing precedent in the repo — there's no speech-to-text integration anywhere yet to pin it to. 0–1 is the common convention most STT providers (Google STT, Whisper, AWS Transcribe) already return, so the schema is compatible with any of them, but the exact calibration (what 0.87 really means in practice) can't be verified until a real provider is chosen. Flagged honestly rather than guessed at. |

## 4. Transcript normalization rules

Defined per `expected_answer_type`, reusing Day 22's existing fixed vocabulary rather
than one generic rule for every answer — a number and a yes/no answer need different
cleanup, so one rule can't honestly serve both.

| `expected_answer_type` | Normalization rule |
|---|---|
| `free_text` | Trim leading/trailing whitespace. Strip filler words (`um`, `uh`, `like`, `you know`) only when they're standalone words, not substrings. Collapse repeated whitespace. Preserve everything else as spoken — this type is read by a person or a future NLP step, not parsed into a strict value. |
| `number` | Strip filler words, then convert spoken number words to digits (`"five"` → `5`) for values zero through ninety-nine, the realistic range for "years of experience." A number outside that pattern (spelled oddly, or genuinely not a number) is left in `normalized_text` as text and flagged, not silently coerced to `0` — same honest-null discipline as `scoring_engine`'s redistribution logic (nothing invented when data doesn't fit). |
| `yes_no` | Map a closed set of real spoken variants (`"yes"`, `"yeah"`, `"yep"`, `"sure"` → `true`; `"no"`, `"nope"`, `"not really"` → `false`) to a boolean. Anything outside that closed set is left as `null` with the raw text kept — a borderline or hedging answer ("maybe, depends") shouldn't be forced into yes or no. |
| `currency` | Strip filler words and currency words/symbols into one normalized numeric value plus a currency code (defaults to `INR`, since every sample JD in this repo is an India-based role) — e.g. `"around 12 lakhs"` → `{"amount": 1200000, "currency": "INR"}`. Vague answers (`"market rate"`, `"negotiable"`) are kept as text, not forced into a number. |
| `duration` | Normalize to a number of days wherever the phrasing gives one (`"one month"` → `30`, `"two weeks"` → `14`, `"immediately"` / `"I can join right away"` → `0`). Same honesty rule as the others — an unparseable duration stays as text rather than being guessed at. |
| `list` | Split on commas and the word "and", trim each item, then match each item against the role's own mandatory-skill list from the question itself (the same list `question_builder.py` already filled into the question text) so the normalized list uses the project's canonical skill names, not whatever casing or wording the candidate happened to say. |

`raw_text` is never modified by any of this — every rule only ever produces
`normalized_text`, so the original spoken answer is always recoverable for audit,
exactly like `parse_education_section`'s approach of keeping `raw_line` alongside every
parsed education entry.

## 5. Database schema for screening interactions

Two tables (or two collections, if MongoDB — the PRD lists both as options and nothing
here depends on which is picked):

**`screening_sessions`** — one row per call

| Column | Type | Notes |
|---|---|---|
| `session_id` | string, primary key | |
| `candidate_id` | string, indexed | |
| `job_id` | string, indexed | |
| `started_at` | timestamp | |
| `ended_at` | timestamp, nullable | null while a call is still in progress |
| `call_status` | enum (`queued`, `completed`, `no_answer`) | |
| `questions_asked` | integer | |
| `questions_answered` | integer | |
| `average_confidence` | float, nullable | null until the call completes |

**`screening_transcripts`** — one row per answer, foreign-keyed to its session

| Column | Type | Notes |
|---|---|---|
| `transcript_id` | string, primary key | |
| `session_id` | string, foreign key → `screening_sessions.session_id` | |
| `candidate_id` | string, indexed | denormalized from the session on purpose — lets a query pull "every answer this candidate ever gave to a Skills question across every job" without a join, the same kind of lookup `ranking_engine` already does straight off `candidate_scores` files |
| `job_id` | string, indexed | |
| `question_id` | string, indexed | |
| `category` | string | copied from the question bank, so a query can filter by category (e.g. every Salary answer) without joining back to `screening_questions` |
| `timestamp` | timestamp | |
| `raw_text` | text | |
| `normalized_text` | text | |
| `confidence_level` | float | |
| `expected_answer_type` | string | |

Composite index on `(candidate_id, job_id)` on both tables — every real lookup so far in
this pipeline (scoring, eligibility, ranking) joins on exactly that pair, so the
transcript tables are indexed the same way rather than inventing a different access
pattern.

## Honest gaps, flagged rather than guessed at

- **Confidence-level calibration is unverified.** 0–1 is the right *shape*, matching
  every major STT provider, but what a given number actually means in practice can't be
  confirmed without picking a real provider and running it — that's a later day's work,
  not something to fake with invented numbers today.
- **`call_status` only has three values because nothing has called anyone yet.** A real
  integration will likely need more granularity (busy signal, wrong number, hung up
  mid-call) — this schema isn't closed against adding them, but adding states that don't
  correspond to anything the system can currently produce would be guessing.
- **The `list` normalization rule depends on Day 22's skill list already being in the
  question text** — if a future day changes how Skills questions are generated, this
  rule's assumption should be re-checked against the new question shape.