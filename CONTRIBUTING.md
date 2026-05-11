# Contributing

Thanks for your interest. This project aims to be a faithful, transparent, source-cited mirror of the Constitution of India. Contributions that improve faithfulness, cite sources clearly, or strengthen the pipeline are very welcome.

## Kinds of contributions we want

- **Textual corrections** — typos, formatting, missing punctuation, or substantive divergences from a cited official source.
- **Cross-reference fixes** — missing or incorrect links between articles or to schedules.
- **Pipeline improvements** — better PDF extraction, prompt refinements, more robust verification.
- **Documentation** — clearer explanations, better examples, fixes to spec or handoff docs.

## Kinds of contributions we cannot accept

- Commentary, interpretation, or case-law annotations — these belong in a separate project.
- Translations (Hindi or regional) — out of scope for v1; see PRD §8.
- Edits to law text without a cited official source.

## Submitting a correction to the law text

Open an issue or PR that includes:

1. The article (or schedule) affected, with file path.
2. The exact change, presented as a diff or before/after.
3. **A citation** — the official source (Lok Sabha PDF, India Code, Gazette of India), with URL and ideally a SHA-256 of the PDF or page reference.
4. Whether this is a typo/formatting fix or a substantive textual correction.

Substantive corrections are reviewed by the maintainer and a lawyer-reviewer before merging. Typo and formatting fixes have a lighter review path.

## Submitting a pipeline change

Standard PR. Include tests where reasonable. The pipeline is in `pipeline/`; see `pipeline/README.md` (forthcoming).

## Conventions

### Repealed / omitted articles and schedule entries

When an article or schedule entry is omitted by an amendment, we **keep** it listed in the parent file's frontmatter (`articles:` array in part files, or in-order numbering in schedule files) and **keep** the article file on disk. The article file gets `status: repealed`, a `repealed_by` reference to the omitting Act, and its body is replaced with an italic omission marker. Schedule entries get an in-place italic omission marker (e.g. `*87. [Omitted by ...]*`).

Rationale:

- Article slots are not reused — once article 31 is omitted, no future amendment creates a different "Article 31". Listing the slot preserves traceability.
- The source of truth for "is this article currently in force?" is the `status:` field inside the article file, not the parent's array.
- Removing entries from the array would create unexplained numerical gaps (e.g. `30, 31A, 31B, 31C, 32`) that readers couldn't interpret without consulting the body prose.

Each affected part file's body prose should also document the omission explicitly — e.g. "Articles 31, 31D, 32A have been omitted."

### Amendment commit cadence

One commit per amendment. Tag every amendment `amendment-NNN` (annotated, with the Act's full short title and assent date in the tag message). Between any two amendments, at most one correction commit may accumulate baseline fixes and changes from non-368 Acts (e.g. State Reorganisation Acts).

### `current_as_of` = assent date

The `current_as_of` field is the **assent date** of the most recent amendment that touched the file, never a commencement or notification date. All textual changes from an amendment are applied at its assent date even when individual sections of that Act were notified into force later (or never notified — see e.g. 42A §§18, 19, 22, 31, 32, 35, which our repo reverted via 44A §45).

## Code of conduct

Be respectful and constructive. Disagreements about constitutional content are welcome when grounded in cited sources.
