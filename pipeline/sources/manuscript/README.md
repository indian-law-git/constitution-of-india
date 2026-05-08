# Manuscript transcriptions

Human-typed transcriptions of articles, schedules, or parts directly from the **original calligraphic manuscript** of the Constitution of India — the signed-as-adopted copy from 26 January 1950, calligraphed by Prem Behari Narain Raizada.

This is the **most authoritative** 1950-baseline source we use. CLPR's curated digital text is the primary baseline for the 389 articles where it has clean coverage; manuscript transcriptions fill the small number of gaps where CLPR is incomplete (Articles 40, 135, 232, 239, 240, 341 in v1) and serve as spot-check ground truth (PRD §11).

## Source provenance

- **File:** `docs/Original-Manuscript-of-the-Constitution-of-India_New1.pdf` (gitignored — too large for git; SHA-256 below for verification)
- **SHA-256:** `e5cb50a2df24f4fbf65fbb1e125cbaa81124e0f518ba52d005344de10c742ec4`
- **Origin:** [constitutionofindia.net](https://www.constitutionofindia.net/) "Read → Original Manuscript"

## Format convention

One file per article: `article-NNN.txt` (e.g., `article-232.txt`, `article-031A.txt` for letter-suffixed). Number is the **1950 article number**.

```
# Title: Interpretation
# Page: 87

Where a High Court exercises jurisdiction in relation to more than one State specified in Part A or Part B of the First Schedule or in relation to a State and an area not forming part of the State—
(a) references in this Chapter to the Governor in relation to the Judges of High Court shall be construed as references to the Governor of the State in which the Court has its principal seat;
(b) the reference to the approval by the Governor of rules, forms and tables for subordinate courts shall be construed as a reference to the approval thereof by the Governor or the Rajpramukh of the State in which the subordinate court is situate, or if it is situate in an area not forming part of any State specified in Part A or Part B of the First Schedule, by the President; and
(c) references to the Consolidated Fund of the State shall be construed as references to the Consolidated Fund of the State in which the Court has its principal seat.
```

**Header lines (optional, all begin with `#`):**
- `# Title: ...` — the article's heading title
- `# Page: ...` — page number from the manuscript PDF (handy for re-finding)
- `# Notes: ...` — anything worth recording about the transcription decision

**Body conventions:**
- Preserve clause numbering: `(1)`, `(2)`, `(3)`
- Preserve sub-clause letters: `(a)`, `(b)`, `(c)`
- Provisos: just write `Provided that ...` on a new line
- Em-dashes: use `—` (U+2014) where the manuscript has them; ASCII `-` is fine as a fallback
- Italics in the manuscript (typically clause letters): don't worry about marking — the renderer will italicize `(a)`, `(b)`, etc. by convention.
- Don't try to mimic line breaks of the manuscript; just paragraph breaks.
- If the manuscript text is genuinely ambiguous to read, transcribe your best guess and add a `# Notes:` line noting the uncertainty.

## What gets tracked

Files in this directory ARE committed to git. They represent valuable manual work and are part of the project's audit trail. Each file is small (a few hundred lines at most).

The pipeline reads these files via `pipeline/extract/manuscript.py` and emits standard JSON records to `pipeline/intermediate/scraped/manuscript/` (gitignored), which then feed the same render step as CLPR/IK records.
