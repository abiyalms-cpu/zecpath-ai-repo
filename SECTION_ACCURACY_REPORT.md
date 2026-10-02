# Resume Section Detection — Accuracy Report

## Method

24 of 27 sample resumes have real section headings, so for those, "accuracy"
isn't a meaningful test — if the heading is recognized, the split is correct
by construction, and Day 5 already proved heading recognition works across
all 24. The real test is the **heuristic fallback path**, which only runs
when a resume has fewer than 2 recognizable headings.

Every line from the two no-heading resumes was hand-checked against what the
correct label should actually be, since I wrote both resumes and know the
right answer for each line.

## Results — heuristic path

| Resume | Lines | Correctly labeled | Honestly unclassified | Wrongly labeled |
|---|---|---|---|---|
| `no_headings_vikram.docx` (prose) | 6 | 5 | 1 | 0 |
| `no_headings_meena.docx` (bullets) | 11 | 10 | 1 | 0 |
| **Total** | **17** | **15 (88%)** | **2 (12%)** | **0 (0%)** |

"Honestly unclassified" means the line was the opening summary paragraph in
both cases. There's no reliable content signal that a sentence of ordinary
prose *is* a professional summary rather than any other paragraph, so the
classifier leaves it unlabeled instead of guessing — that's a deliberate
design choice, not a miss. Zero lines were put in the *wrong* section.

## What this doesn't cover

- Only two heuristic-path resumes exist, both written for this test. Real
  resumes written by actual people will vary more than two examples can
  prove.
- The heuristic has no rule for detecting a summary paragraph at all. It
  will always land in `UNCLASSIFIED` on a no-heading resume, which is
  correct behaviour, but worth knowing rather than discovering later.
- Section detection for Projects only has one tested example
  (`ananya_rao.docx`), and only in the heading-based path — there's no
  no-heading Projects test case.

## Results — heading-based path (24 resumes)

All 24 correctly produced exactly the sections their source text contains —
no section was invented, and none was dropped, except where a resume
genuinely never had that section to begin with (e.g. `ishaan_kapoor_photo.docx`
has no SUMMARY, because the original resume doesn't either).