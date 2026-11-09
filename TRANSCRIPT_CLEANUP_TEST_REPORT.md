# Transcript Cleanup Test Report

**What this tests:** the normalization and cleanup rules in `screening_ai/transcript_normalizer.py` and `transcript_processor.py`, against realistic speech-to-text-style text (filler words, spoken numbers, hedging, negation, silence, partial/interrupted answers).

**What this does NOT test:** real speech-to-text accuracy. No STT provider is integrated anywhere in this repo yet, and no real phone call has ever happened (`screening_ai/call_handler.py` is still the Day 1 stub), so there is no audio-to-text accuracy to measure. Every input below is already text, standing in for what a provider would eventually return.

**Result: 17/17 cases passed.**

| # | Case | Input (as STT would return it) | Result |
|---|------|-------------------------------|--------|
| 1 | filler words, informal self-introduction | `um so uh basically I'm a software engineer with like five years of experience` | PASS |
| 2 | spoken number, with unit spoken back | `um like twenty five years` | PASS |
| 3 | plain digit already spoken as a number | `5 years` | PASS |
| 4 | number phrase outside recognizable range -- must not be coerced to 0 | `around a hundred projects or so` | PASS |
| 5 | clear yes with filler and hedge words around it | `uh yeah sure, definitely` | PASS |
| 6 | soft no phrased conversationally | `not really, no` | PASS |
| 7 | genuinely ambiguous answer -- must stay null, not guessed | `maybe, it depends on the team` | PASS |
| 8 | currency in lakhs with filler and unit words | `um around 12 lakhs per annum` | PASS |
| 9 | currency, vague non-numeric answer kept as text | `it's negotiable, market rate basically` | PASS |
| 10 | notice period in weeks | `uh two weeks notice` | PASS |
| 11 | notice period, immediate joiner phrasing | `I can join right away` | PASS |
| 12 | skills list spoken as a sentence, one skill explicitly denied | `uh yeah so I've worked with react and node js mostly, not so much mongo` | PASS |
| 13 | skills list with spacing/casing differences from the canonical names | `javascript and NODEJS, that's about it` | PASS |
| 14 | silence -- candidate said nothing | `(empty / silence)` | PASS |
| 15 | silence -- STT returned only dead air / noise markers | `(empty / silence)` | PASS |
| 16 | partial answer -- call cut off mid-sentence | `I have around three years of experience in` | PASS |
| 17 | interrupted -- candidate started answering, then talked over | `I worked at` | PASS |

## Detail per case

### 1. filler words, informal self-introduction — PASS
- Input: `um so uh basically I'm a software engineer with like five years of experience`
- Answer type: `free_text`
- normalized_text: `I'm a software engineer with five years of experience`
- parsed_value: `I'm a software engineer with five years of experience`
- check `normalized_text`: expected `I'm a software engineer with five years of experience`, got `I'm a software engineer with five years of experience` -- ok

### 2. spoken number, with unit spoken back — PASS
- Input: `um like twenty five years`
- Answer type: `number`
- normalized_text: `25`
- parsed_value: `25`
- check `parsed_value`: expected `25`, got `25` -- ok

### 3. plain digit already spoken as a number — PASS
- Input: `5 years`
- Answer type: `number`
- normalized_text: `5`
- parsed_value: `5`
- check `parsed_value`: expected `5`, got `5` -- ok

### 4. number phrase outside recognizable range -- must not be coerced to 0 — PASS
- Input: `around a hundred projects or so`
- Answer type: `number`
- normalized_text: `around a hundred projects or`
- parsed_value: `None`
- check `parsed_value is None (unparsed)`: expected `None`, got `None` -- ok

### 5. clear yes with filler and hedge words around it — PASS
- Input: `uh yeah sure, definitely`
- Answer type: `yes_no`
- normalized_text: `Yes`
- parsed_value: `True`
- check `parsed_value`: expected `True`, got `True` -- ok

### 6. soft no phrased conversationally — PASS
- Input: `not really, no`
- Answer type: `yes_no`
- normalized_text: `No`
- parsed_value: `False`
- check `parsed_value`: expected `False`, got `False` -- ok

### 7. genuinely ambiguous answer -- must stay null, not guessed — PASS
- Input: `maybe, it depends on the team`
- Answer type: `yes_no`
- normalized_text: ``
- parsed_value: `None`
- check `parsed_value`: expected `None`, got `None` -- ok

### 8. currency in lakhs with filler and unit words — PASS
- Input: `um around 12 lakhs per annum`
- Answer type: `currency`
- normalized_text: `INR 1,200,000`
- parsed_value: `{'amount': 1200000, 'currency': 'INR'}`
- check `parsed_value`: expected `{'amount': 1200000, 'currency': 'INR'}`, got `{'amount': 1200000, 'currency': 'INR'}` -- ok

### 9. currency, vague non-numeric answer kept as text — PASS
- Input: `it's negotiable, market rate basically`
- Answer type: `currency`
- normalized_text: `it's negotiable, market rate`
- parsed_value: `None`
- check `parsed_value is None (unparsed)`: expected `None`, got `None` -- ok

### 10. notice period in weeks — PASS
- Input: `uh two weeks notice`
- Answer type: `duration`
- normalized_text: `14 days`
- parsed_value: `14`
- check `parsed_value`: expected `14`, got `14` -- ok

### 11. notice period, immediate joiner phrasing — PASS
- Input: `I can join right away`
- Answer type: `duration`
- normalized_text: `0 days`
- parsed_value: `0`
- check `parsed_value`: expected `0`, got `0` -- ok

### 12. skills list spoken as a sentence, one skill explicitly denied — PASS
- Input: `uh yeah so I've worked with react and node js mostly, not so much mongo`
- Answer type: `list`
- normalized_text: `React, Node.js`
- parsed_value: `['React', 'Node.js']`
- check `parsed_value`: expected `['React', 'Node.js']`, got `['React', 'Node.js']` -- ok

### 13. skills list with spacing/casing differences from the canonical names — PASS
- Input: `javascript and NODEJS, that's about it`
- Answer type: `list`
- normalized_text: `JavaScript, Node.js`
- parsed_value: `['JavaScript', 'Node.js']`
- check `parsed_value`: expected `['JavaScript', 'Node.js']`, got `['JavaScript', 'Node.js']` -- ok

### 14. silence -- candidate said nothing — PASS
- Input: `(empty)`
- Answer type: `free_text`
- normalized_text: `None`
- parsed_value: `None`
- silence_detected: true
- check `silence_detected`: expected `True`, got `True` -- ok

### 15. silence -- STT returned only dead air / noise markers — PASS
- Input: `(empty)`
- Answer type: `free_text`
- normalized_text: `None`
- parsed_value: `None`
- silence_detected: true
- check `silence_detected`: expected `True`, got `True` -- ok

### 16. partial answer -- call cut off mid-sentence — PASS
- Input: `I have around three years of experience in`
- Answer type: `free_text`
- normalized_text: `I have around three years of experience in`
- parsed_value: `I have around three years of experience in`
- partial_answer: true
- check `normalized_text`: expected `I have around three years of experience in`, got `I have around three years of experience in` -- ok

### 17. interrupted -- candidate started answering, then talked over — PASS
- Input: `I worked at`
- Answer type: `free_text`
- normalized_text: `I worked at`
- parsed_value: `I worked at`
- interrupted: true
- check `normalized_text`: expected `I worked at`, got `I worked at` -- ok

## Honest gaps

- Confidence-level handling is untested here beyond the silence case (forcing it to 0.0) -- there's still no real STT provider to confirm what a given confidence number means in practice (same gap TRANSCRIPT_DATA_ARCHITECTURE.md already flagged).
- `partial` and `interrupted` are tested only as explicit flags passed in -- there is no real call-event stream yet to detect either condition on its own, so this report cannot claim the module detects them automatically, only that it carries the flag through correctly once something else reports it.
- Negation handling in the `list` rule is a literal word-window check (a few words before a skill), not real sentence understanding -- a negation phrased further from the skill name than that window would be missed.
