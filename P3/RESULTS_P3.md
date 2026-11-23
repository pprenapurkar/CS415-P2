# P3 Proof of Concept: results (P2 vs P3)

All data is mock. Every number below is reproducible with the commands shown (Python 3 + Tesseract, same setup as P2).
Raw outputs are in `demo_kit/results/`.

## What changed since P2

| | P2 | P3 |
|---|---|---|
| Screenshot reading and comparing (Missing / Changed / New / Can't confirm) | yes | **unchanged** (output byte-identical to P2 on all 4 conditions) |
| Dump parser | regex + keywords | + spoken clock phrases ("half past", "quarter to"), "a week from Thursday", holidays, "end of the month", "before nine", "pushed to X, it's the Y", filler words; every item now carries a **category reason** |
| Duplicate / changed-commitment detection | none | **`dedupe.py`**: DUPLICATE / UPDATE / NEW with a plain-English reason; number-aware, course-aware, date-aware |
| Coverage status | printed as text | **`coverage.py`**: per-source Captured / Partial / Unavailable + Needs Review list as JSON, for the prototype's coverage view |

## Why (each change traced to a P2 finding)

- P2 test: participants worried about **duplicates** and **missed or changed meetings** -> `dedupe.py` (UPDATE verdict = "this moved").
- P2 test: **inconsistent categorization** -> category reason shown for every item; ambiguous items stay flagged for the user.
- P2 test: **uncertainty about whether everything was captured**, and flagged uncertainty was well received -> `coverage.py`.
- P2 conclusion named exactly these four: duplicate detection, categorization, coverage status, changing commitments.

## Evidence

### 1. Duplicate / changed-commitment detection
40 incoming items vs the 24-item known list (14 true duplicates, 10 updates, 16 new, including look-alikes such as Quiz 5 vs Quiz 7 and Homework 6 vs Homework 7). `python3 demo.py dupes`

| Approach | Dev set (40) | Blind set (16) |
|---|---|---|
| P2: no duplicate check | 16/40 (40%): 0/14 duplicates, 0/10 updates found | 5/16 (31%) |
| Naive title similarity (P2's matcher, ratio >= 0.7) | 26/40 (65%): treats Quiz 7 as a duplicate of Quiz 5 | 10/16 (62%) |
| **P3 `dedupe.py`** | **40/40 (100%)** | **15/16 (94%)** |

Honesty notes: the dev cases were written before the code, but I designed the rules knowing what they had to handle, and one case ("CS 450 lab 7") failed on first run (39/40) and was fixed, so treat 40/40 as "developed against". The blind set was written after the code was frozen and run once. Its one miss is an abbreviation: "GA office **hrs**" vs "GA office hours" (no synonym handling).

### 2. Dump parser (`python3 demo.py dumps`, `--stress`, `--heldout`)
| Test set | Items found | Date+time correct | Category correct | Expected "check this" flags raised |
|---|---|---|---|---|
| Original 25 dumps | 44/45 -> 44/45 | 97% -> 97% | 96% -> 96% | 10/13 -> 10/13 (no regression) |
| 8 harder phrasings (**tuned on**) | 7/9 -> 9/9 | 44% -> 94% | 44% -> 89% | 2/6 -> 3/6 |
| 20 held-out dumps (written before parser changes) | 17/21 -> 21/21 | 67% -> **100%** | 71% -> **90%** | 1/4 -> 2/4 |

Caveats: the held-out phrases are my own and cover the same families of phrasing that failed in the stress set (clock phrases, holidays, "end of the month", "EOD"). They show the rules generalize across words and items, not that arbitrary speech works. Uncertainty flags are still the weakest part: the parser raises only about half of the flags a person would want.
Remaining held-out misses: "lab report" (lab = School, report = Work: it flags the category but picks Work), and "boss" is not in the Work vocabulary (flagged, not guessed).

### 3. Coverage status (`python3 demo.py coverage <set>`)
| Condition | Canvas | Outlook | Correct? |
|---|---|---|---|
| clean | Captured | Captured | yes |
| phone-quality | Captured | Captured | yes |
| cropped Canvas | **Partial** (5 items "can't confirm", not "missing") | Captured | yes |
| unreadable Outlook | Captured | **Unavailable** (nothing reported missing) | yes |

Screenshot reading itself is unchanged: 10/10 planted differences caught on clean and phone, 9 caught + 1 "can't confirm" on cropped, 5 caught + Outlook declared unreadable on unreadable. Identical to P2.

### 4. Overlapping screenshots (the issue friends raised)
Friends who heard the idea said uploading several screenshots of the same calendar would add the same task twice. Test: screenshot A's items are the existing list, screenshot B is checked against it. `python3 test_overlap.py`

| Scenario | Result |
|---|---|
| partial screenshot, then full screenshot (6 items overlap) | 6 duplicates, 5 new, 0 false updates |
| full screenshot, then partial screenshot | 6 duplicates, 0 new |
| clean screenshot, then phone-quality screenshot of the same screen | 11 duplicates, 0 new |
| same screenshot uploaded twice | 11 duplicates, 0 new |

Limit: one mock Canvas screen in four versions (Canvas only), not real accounts or overlapping Outlook weeks.

## Limits (say these on the slide or in Q&A)
- Only one version of the mock screens x 4 conditions is in the repo, so that is what was rerun. The P2 deck's "5 random versions" matrix is not in the repo and was not rerun.
- Mock data, rule-based, no language model; test sets are small and written by the team.
- OCR output can differ slightly across Tesseract versions. Rerun `demo.py screenshots clean --reveal` on your machine before quoting those numbers.
