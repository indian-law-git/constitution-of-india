# Handoff — Phase 2 in progress

**Companion to** [`docs/handoff.md`](handoff.md) (Phase 0/1 handoff) and [`docs/prd-constitution-v1.md`](prd-constitution-v1.md) (the spec). When in doubt, the PRD wins.

This file exists so a fresh Claude Code session (or human collaborator) can pick up Phase 2 cleanly.

---

## 1. Where we are

**Tagged**: [`v1.0-baseline`](https://github.com/indian-law-git/constitution-of-india/releases/tag/v1.0-baseline) (the 1950 Constitution; published before Phase 2 began). 24 commits on `main`. The repo is public.

**Phase 1 complete:**
- 395 articles in `articles/` (one Markdown file each, with YAML frontmatter)
- 22 part manifests in `parts/`
- 8 schedules in `schedules/` (no documented gaps)
- `metadata/provenance.json` (7 sources, SHA-256s)
- `metadata/cross-references.json` (403 nodes, inbound/outbound)
- `metadata/amendments.json` (106 amendments, 4-source triangulation)

**Phase 2 underway. 3 of 106 amendments landed:**
- Commit [`d1ddc77`](https://github.com/indian-law-git/constitution-of-india/commit/d1ddc77) — baseline-integrity fix for Article 19 clause (6) (true 1950 form restored from manuscript; CLPR's per-article page had carried the post-1st-Amendment (i)/(ii) split).
- Commit [`4251da3`](https://github.com/indian-law-git/constitution-of-india/commit/4251da3) — **The Constitution (First Amendment) Act, 1951.** 14 files changed: edits to Articles 15, 19, 85, 87, 174, 176, 341, 342, 372, 376; new Articles 31A, 31B; new Ninth Schedule; Part III manifest updated.
- Commit `384e42c` — baseline-integrity fix for Article 81 (CLPR's per-article page mislabels its 1950 section as "(1) to (2)" and was missing clause (3); body taken from CLPR's consolidated 1950 page, cross-checked against Aggarwala 1950 facsimile).
- Commit `b779d66` — **The Constitution (Second Amendment) Act, 1952.** 1 file: Article 81(1)(b) loses the lower-bound population floor (omits "not less than one member for every 750,000 of the population and").
- Commit `e116bc1` — **The Constitution (Third Amendment) Act, 1954.** 1 file: Schedule 7 List III entry 33 substituted wholesale with five-sub-clause form bringing essential commodities (foodstuffs, cattle fodder, raw cotton, raw jute) under concurrent jurisdiction. **First scanned-PDF amendment** — required OCR with cross-verification (tesseract + `/liteparse` + 600 DPI image inspection at punctuation-ambiguous lines).

**103 amendments remain.**

## 2. Pipeline cheat-sheet

```bash
uv sync --extra dev
uv run indlaw --help

# Phase 1 inputs (already cached)
indlaw scrape-clpr               # 495 article URLs from CLPR
indlaw scrape-clpr-schedules     # 21 schedule URLs from CLPR
indlaw extract-ik                # parse offline IK HTML
indlaw extract-manuscript        # parse pipeline/sources/manuscript/*.txt

# Phase 1 renders (re-runnable)
indlaw render-articles
indlaw render-parts
indlaw render-schedules

# Phase 2 inputs
indlaw extract-legislative       # parse docs/legislative-amendments.html
indlaw download-amendments       # 106 PDFs → docs/amendments/{NNN}.pdf
                                 # (browser-like headers required; Akamai)

# Metadata
indlaw build-provenance
indlaw build-crossrefs
indlaw build-amendments
```

## 3. Per-amendment workflow (locked in)

For each remaining amendment N (`docs/amendments/NNN.pdf`):

1. **Read the PDF** end to end. Identify each section's edit op (substitute / insert clause / insert article / add at end / repeal). Try `pdfplumber` first — when it returns chars but no text, the PDF is a scanned image with no text layer (the 3rd Amendment was the first such case). For scans, render pages with `pdftoppm -r 300` and OCR with both **tesseract** and **`/liteparse` with OCR**, cross-verify the operative section verbatim, and on any disagreement crop the relevant region at 600 DPI and inspect the image directly to settle punctuation / wording. Old Gazette typography (semicolon-with-trailing-dash, comma-with-em-dash) is a frequent OCR-misread source.
2. **Cross-check the touched-articles list** against `metadata/amendments.json` for amendment N. Three independent seed sources (legislative.gov.in PDF, pykih, IK) — discrepancies are interesting but not blocking.
3. **Validate-before-patch.** For each article the amendment claims to touch, verify our current corpus's clause / wording matches the BEFORE state the amendment expects. Mismatches mean the v1.0-baseline carries a hybrid form (e.g. CLPR mixed in some early-amendment text). Fix the baseline from manuscript as a **discrete prior commit** — see commit `d1ddc77` for the pattern.
4. **Apply edits.** Direct file edits to `articles/article-NNN.md`, `schedules/schedule-NN.md`, `parts/part-X.md`. Frontmatter on every touched file:
   ```yaml
   amended_by:
     - "The Constitution (Nth Amendment) Act, YYYY"
     # ... earlier amendments accumulate above
   current_as_of: "YYYY-MM-DD"   # the act's date of assent
   ```
   For new articles, also: `inserted_by: "The Constitution (Nth Amendment) Act, YYYY"`.
   For new schedules: `inserted_by:` + `source: legislative-gov-in` + `source_url:` (the legislative.gov.in PDF URL from `metadata/amendments.json`).
5. **Single commit per amendment** (PRD §5.7). Commit message format: see commit `4251da3` for the template — section-by-section breakdown, source PDF cite, validation pass summary, before-state mismatch notes (with reference to the prior baseline-fix commit).
6. **Push** when satisfied.

## 4. Decisions that aren't obvious from the code

- **Manuscript precedence on overlap.** Where a Markdown file has both a CLPR-derived and a manuscript-derived source, the manuscript wins. Frontmatter `source: mixed` flags hybrid origin. See `pipeline/render/markdown.py` `collect_baseline()` for articles, `_load_schedule_segments()` for schedules.
- **Bare-numeric slugs only for the 1950 baseline.** Letter-suffixed slugs (21A, 31B, 134A) are by definition post-1950 insertions — even when CLPR mislabels them as 1950 (Article 257A was one such case). The CLPR scraper rejects them in `scrape_article()`.
- **CLPR has internal data inconsistencies.** Their per-article pages occasionally carry post-amendment text under the "Constitution of India 1950" label (Article 19 clause 6 was the canonical example — found during 1st Amendment validation). Their consolidated `/constitution-of-india-1950/` page is more reliable for these but has its own gaps. Trust the manuscript when in doubt.
- **Article 19's hybrid frontmatter** (`source: mixed` + `manuscript_pdf_sha256:` + `note:`) is the template for back-fixed articles.
- **Akamai shenanigans.** legislative.gov.in's listing page is behind Akamai bot detection; the rendered HTML must be saved manually from a real browser (`docs/legislative-amendments.html`, gitignored). The static-CDN PDFs work programmatically only with browser-like headers (User-Agent, Referer, Sec-Fetch-*) — see `pipeline/extract/legislative.py:download_pdfs()`.
- **PDFs and the IK HTML are gitignored.** Their SHA-256s live in `metadata/provenance.json` for verifiability.
- **Amendment commits are one logical commit each** (PRD §5.7), not one commit per touched article. Mirrors `nickvido/us-code` snapshot-as-commit model.

## 5. Source landscape recap

| Source | Path | Coverage | Role |
|---|---|---|---|
| CLPR (Centre for Law and Policy Research) | per-article URLs scraped to `pipeline/intermediate/scraped/articles/` | 389 articles | Phase 1 baseline primary |
| CLPR schedules | per-schedule URLs to `pipeline/intermediate/scraped/clpr-schedules/` | 16 segments / 8 schedules | Phase 1 baseline primary |
| Lok Sabha calligraphic 1950 manuscript | `pipeline/sources/manuscript/article-NNN.txt` (tracked) | 6 baseline-fill articles + 5 spot-checks + 2 schedule fills + 1 baseline integrity fix (Art 19 clause 6) | Authoritative 1950 source for gaps + spot-check ground truth + back-fixes |
| Indian Kanoon | offline HTML at `docs/ConstitutionofIndia_IK.html` (gitignored) → `pipeline/intermediate/scraped/ik/` | 498 records, 95 distinct amendment-act citations across 163 articles | Cross-check + Phase 2 amendment-touching-articles seed |
| pykih | `pipeline/sources/pykih/{amendments,data}.json` (tracked) | 99 amendments + 440 (amendment, article, status) triples | Phase 2 cross-validation |
| Wikipedia table of amendments | not extracted programmatically | 106 amendments | Phase 2 fallback metadata |
| legislative.gov.in (Ministry of Law and Justice) | `docs/legislative-amendments.html` + `docs/amendments/{NNN}.pdf` (both gitignored) | 106 amendment Acts as PDFs | **Phase 2 authoritative source** |

## 6. Phase 2 backlog (chronological order)

The next ten amendments after the 1st (which is in):

| # | Year | Date | Short summary (from pykih) |
|---|---|---|---|
| 2 | 1952 | 1953-05-01 | Allocation of seats / representation tweak. |
| 3 | 1954 | 1955-02-22 | Concurrent List entry on essential commodities. |
| 4 | 1955 | … | Property compensation; Ninth Schedule additions. |
| 5 | 1955 | … | Reorganisation Act–related Schedule changes. |
| 6 | 1956 | … | Tax on inter-State sales. |
| 7 | 1956 | … | **Big one** — States Reorganisation Act; eliminates Part A/B/C/D states; many articles touched; Schedule 1 restructured. |
| 8 | 1959 | … | Reservation of seats for SC/ST; languages. |
| 9 | 1960 | … | Adjustment of names of States. |
| 10 | 1961 | … | Dadra and Nagar Haveli. |
| 11 | 1961 | … | Amendments to articles 66 and 71 (Vice-President election). |

The full chronological list with PDF paths and known-touched-articles is in [`metadata/amendments.json`](../metadata/amendments.json).

The 7th Amendment (1956) is going to be the first big test — it eliminated the Part A/B/C/D state classification that the 1950 Constitution leans on heavily. Many articles' baselines reference "Part A or Part B of the First Schedule"; the 7th Amendment substituted those wholesale.

## 7. Things to watch

- **Article-19-style hybrids are likely elsewhere.** CLPR's 1950 text occasionally carries post-amendment forms. The validate-before-patch step will surface them as we go.
- **Renumbering.** Some amendments renumber articles (e.g. CLPR's article-39 page already shows that current Art 39 was numbered Art 38 in 1950). Our v1.0-baseline uses the slug-derived numbering, which is the *current* numbering; for amendments that did renumber, we'll need to handle this carefully when an amendment cites an article by its post-renumbering number.
- **Schedule 1 is a moving target.** The 1950 First Schedule had Part A / B / C / D states + territories. The 7th Amendment (1956) restructured this entirely. Earlier amendments (4th, 5th, 6th) also touched the First Schedule. Each amendment that touches Schedule 1 will need careful diffing.
- **Commencement vs assent.** Some amendments have a commencement date later than assent (the 42nd Amendment 1976 famously had multiple staggered commencement dates per its own preamble — we observed this in `metadata/amendments.json` where the title even leaked the commencement narrative). For Phase 2 commits, use the date of assent for `current_as_of` and note any commencement specifics in the commit message.
- **Constitutional Orders.** Some amendments delegate to the President to issue Constitutional Orders (e.g. listing Scheduled Castes / Tribes). Those orders aren't constitutional articles themselves; we don't track them.

## 8. Where to look

- The 1st Amendment commit ([`4251da3`](https://github.com/indian-law-git/constitution-of-india/commit/4251da3)) is the canonical example of a Phase 2 amendment commit. Read its commit message and diff before doing the 2nd Amendment.
- The baseline-fix ([`d1ddc77`](https://github.com/indian-law-git/constitution-of-india/commit/d1ddc77)) is the canonical example of a baseline-integrity fix. Read its commit message before fixing any future hybrid you find.
- `articles/article-019.md` shows the post-1st-Amendment state and the hybrid-source frontmatter. Reference shape for any future "mixed source" article.
- `articles/article-031A.md` shows the inserted-article frontmatter shape.
- `schedules/schedule-09.md` shows the inserted-schedule frontmatter shape.
- `pipeline/extract/legislative.py` — the parser for the listing HTML and the PDF downloader. Reusable as-is.
- The PRD ([`docs/prd-constitution-v1.md`](prd-constitution-v1.md)) §5.7 has the exact commit-message schema.

## 9. What to do on a fresh session

1. `git pull` (the public history is the source of truth).
2. `uv sync --extra dev` (Python deps).
3. Read this file + `docs/prd-constitution-v1.md` §5.6, §5.7.
4. `cat metadata/amendments.json | jq '.amendments[1]'` (or equivalent) to see what the 2nd Amendment is expected to touch.
5. `pdfplumber` your way through `docs/amendments/002.pdf`.
6. Validate, edit, commit. Same workflow as the 1st.

Good luck.
