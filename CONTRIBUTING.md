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

## Code of conduct

Be respectful and constructive. Disagreements about constitutional content are welcome when grounded in cited sources.
