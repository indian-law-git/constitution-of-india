# Constitution of India

A Git-native, diffable representation of the Constitution of India. Every amendment is a discrete commit; `git log` reconstructs constitutional history from 26 January 1950 to the present.

**Status: v1 baseline complete** — the Constitution as adopted on 26 January 1950 is fully in. Phase 2 (the 106 constitutional amendments, replayed forward as commits) has not yet started. See [`docs/prd-constitution-v1.md`](docs/prd-constitution-v1.md) for the spec and [`docs/handoff.md`](docs/handoff.md) for the design notes.

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
```

Every scraped artifact lands in `pipeline/intermediate/` (gitignored). The published artefacts are everything outside `pipeline/intermediate/`.

## What's next (Phase 2)

The PRD plans the 106 constitutional amendments as discrete commits — one amendment, one commit (or one logical commit set), in chronological order. The IK extraction has already harvested 95/106 amendment-act citations as a seed. Phase 2 begins with the **1st Amendment Act, 1951**, parsed interactively in Claude Code so the prompt and round-trip-verification design get pinned down on a small batch before scripting.

## Inspiration and prior art

Inspired by [`nickvido/us-code`](https://github.com/nickvido/us-code), adapted for India's source landscape (no versioned XML — PDFs and human-curated digital). See [`docs/research-notes.md`](docs/research-notes.md).

## Contributing

Corrections, typo fixes, and source-cited improvements are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md). Spot-check disagreements between the baseline articles and an authoritative source (Lok Sabha facsimile, India Code, Gazette of India) are particularly valuable.

## Licensing

- Pipeline code: MIT (see [`LICENSE`](LICENSE)).
- Constitutional text: see [`LICENSE-TEXT`](LICENSE-TEXT) (pending; the text is reproduced from public Government of India sources).
