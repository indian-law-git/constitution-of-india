# Constitution of India

A Git-native, diffable representation of the Constitution of India. Every amendment is a discrete commit; `git log` reconstructs constitutional history from 26 January 1950 to the present.

**Status: Phase 2 in progress** — v1 baseline (the Constitution as adopted on 26 January 1950) is in, tagged [`v1.0-baseline`](https://github.com/indian-law-git/constitution-of-india/releases/tag/v1.0-baseline). Phase 2 replays the 106 constitutional amendments forward as discrete commits; the **1st Amendment, 1951** has landed. See [`docs/prd-constitution-v1.md`](docs/prd-constitution-v1.md) for the spec and [`docs/handoff.md`](docs/handoff.md) for the design notes.

### Browse the history

- [`articles/article-019.md`](articles/article-019.md) — current state of Article 19 (post-1st-Amendment).
- `git log articles/article-019.md` — three entries: the baseline render, a manuscript baseline-fix that restored true 1950 clause (6), and the 1st Amendment.
- [`articles/article-031A.md`](articles/article-031A.md), [`articles/article-031B.md`](articles/article-031B.md) — articles inserted by the 1st Amendment.
- [`schedules/schedule-09.md`](schedules/schedule-09.md) — Ninth Schedule (also inserted by the 1st Amendment).
- [`metadata/amendments.json`](metadata/amendments.json) — full index of all 106 amendments (sources triangulated across legislative.gov.in, pykih, Indian Kanoon).

## What's in this repo

| Path | Contents |
|------|----------|
| [`articles/`](articles/) | 395 article files — one per Article, named `article-NNN.md` with YAML frontmatter (PRD §5.2). |
| [`parts/`](parts/) | 22 Part manifests — thin nav files mapping each Part of the 1950 Constitution to its article range. |
| [`schedules/`](schedules/) | 8 schedule files — Schedule 1–8 of the 1950 Constitution. Multi-Part schedules (1, 2, 5, 7) carry their internal structure as `## ` sub-headings. |
| [`metadata/provenance.json`](metadata/provenance.json) | Every source the baseline draws on, with SHA-256s and roles. |
| [`metadata/cross-references.json`](metadata/cross-references.json) | Inbound/outbound citation graph across articles and schedules. |
| [`pipeline/`](pipeline/) | The reproducible Python pipeline: scrapers, extractors, renderers, CLI. |
| [`pipeline/sources/manuscript/`](pipeline/sources/manuscript/) | Human-typed transcriptions from the calligraphic 1950 manuscript. Tracked in git as audit trail. |

## Where the 1950 baseline came from

| Source | Coverage | Role |
|--------|----------|------|
| **Centre for Law and Policy Research** ([constitutionofindia.net](https://www.constitutionofindia.net/)) | 389 articles + 16 schedule segments | Primary baseline. Curated digital text of the 1950-enacted Constitution; per-article/per-schedule pages with explicit Version-1 (Draft) / Version-2 (1950) sections. |
| **Lok Sabha calligraphic manuscript** | 6 article fills, 2 schedule fills, 5 spot-checks | Most authoritative source for the gaps CLPR didn't cover (Articles 40, 135, 232, 239, 240, 341; Schedule 2 Part B; Schedule 7 List III). Spot-check sample (Articles 14, 53, 84, 280, 309) showed CLPR's transcription matches the manuscript byte-for-byte after whitespace + U+2060 normalisation. |
| **Indian Kanoon** ([offline save](docs/ConstitutionofIndia_IK.html), gitignored) | 498 articles | Cross-check + Phase 2 seed — the saved page uses Akoma Ntoso markup and embeds inline `akn-remark` editorial annotations citing 95 distinct amendment acts across 163 articles. Carries *current* consolidated text, not 1950 baseline. |

The `manuscript` source carries each transcription's PDF SHA-256 and page reference. Anyone with the same `Original-Manuscript-of-the-Constitution-of-India_New1.pdf` (gitignored due to size) can verify the chain of custody.

## Browsing the repo

- **An article**: open `articles/article-019.md` (or any `article-NNN.md`) on GitHub. Frontmatter renders as a metadata box; the body renders as legal-text Markdown with clauses on their own paragraphs.
- **A part**: open `parts/part-iii.md` to see "Part III — Fundamental Rights" with its article list; click through to individual articles.
- **A schedule**: open `schedules/schedule-07.md` to see the Seventh Schedule (Union/State/Concurrent Lists) with each list as a numbered Markdown section.
- **The citation graph**: `metadata/cross-references.json` — each id has `outbound` (articles/schedules cited) and `inbound` (where it's cited from). The First Schedule is the most-cited node (59 articles) — the 1950 Constitution's Part A/B/C/D state classification was referenced everywhere.

## What this is **not**

This is a **best-effort** open artifact for researchers, journalists, lawyers, and informed citizens. It is **not legal advice**, **not authoritative**, and **not a substitute** for the official text published by the Government of India. For legal use, refer to [indiacode.nic.in](https://www.indiacode.nic.in) and the Gazette of India.

## Reproducing the build

The pipeline is `pipeline/` — Python, managed by [`uv`](https://github.com/astral-sh/uv).

```bash
uv sync --extra dev
uv run indlaw --help        # list commands

# scrape sources (cached locally; sitemap-driven; throttled 1.5s/request)
uv run indlaw scrape-clpr
uv run indlaw scrape-clpr-schedules
uv run indlaw extract-ik           # if docs/ConstitutionofIndia_IK.html is present
uv run indlaw extract-manuscript   # parse pipeline/sources/manuscript/*.txt

# render
uv run indlaw render-articles
uv run indlaw render-parts
uv run indlaw render-schedules

# metadata
uv run indlaw build-provenance
uv run indlaw build-crossrefs
uv run indlaw build-amendments     # unified amendments index across 4 sources

# amendment Acts (Phase 2 source)
uv run indlaw extract-legislative  # parse docs/legislative-amendments.html
uv run indlaw download-amendments  # 106 PDFs → docs/amendments/{NNN}.pdf
```

Every scraped artifact lands in `pipeline/intermediate/` (gitignored). The published artefacts are everything outside `pipeline/intermediate/`.

## Phase 2 — amendments

Each constitutional amendment lands as one logical commit per PRD §5.7, in chronological order. The 1st Amendment is in (commit [`4251da3`](https://github.com/indian-law-git/constitution-of-india/commit/4251da3)); 105 to go.

**Per-amendment workflow** (interactive, per PRD Appendix A for the early ones):

1. Read `docs/amendments/{NNN}.pdf` (the act text from legislative.gov.in).
2. Validate the before-state of every touched article against our current corpus. Where it doesn't match (e.g. a baseline integrity issue), fix from the manuscript first as a separate commit.
3. Apply the substitutions / insertions / additions directly to `articles/`, `schedules/`, and `parts/` Markdown files.
4. Update each touched file's frontmatter (`amended_by`, `current_as_of`).
5. Cross-validate the touched-articles list against `metadata/amendments.json`'s pykih + IK seeds.
6. Single commit. Structured commit message per PRD §5.7.

Discoveries during Phase 2 ingestion that affect baseline integrity get fixed as discrete prior commits, so each amendment's diff stays clean and `git log articles/article-NNN.md` tells the article's true history.

## Inspiration and prior art

Inspired by [`nickvido/us-code`](https://github.com/nickvido/us-code), adapted for India's source landscape (no versioned XML — PDFs and human-curated digital). See [`docs/research-notes.md`](docs/research-notes.md).

## Contributing

Corrections, typo fixes, and source-cited improvements are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md). Spot-check disagreements between the baseline articles and an authoritative source (Lok Sabha facsimile, India Code, Gazette of India) are particularly valuable.

## Licensing

- Pipeline code: MIT (see [`LICENSE`](LICENSE)).
- Constitutional text: see [`LICENSE-TEXT`](LICENSE-TEXT) (pending; the text is reproduced from public Government of India sources).
