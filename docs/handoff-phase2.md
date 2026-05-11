# Handoff — Phase 2 in progress (post-redo, on the corrected baseline)

**Companion to** [`docs/handoff.md`](handoff.md) (original Phase 0/1 handoff) and [`docs/prd-constitution-v1.md`](prd-constitution-v1.md) (the spec).

This file is the canonical re-onboarding doc for resuming Phase 2 work in a fresh session.

---

## 1. Where we are

**Tagged**: [`v1.0-baseline`](https://github.com/indian-law-git/constitution-of-india/releases/tag/v1.0-baseline) — the **corrected** 1950 baseline (re-rendered from CLPR's consolidated `/constitution/constitution-of-india-1950/` page; schedules audited against the Aggarwala facsimile and verified against the calligraphic 1950 manuscript). The earlier baseline carried CLPR per-article drift; the redo (commit `60f2d44`) replaced it.

**Phase 2 underway. 41 of 106 amendments landed:**

Latest 12 tagged commits (most recent first):

```
amendment-041  0153dc3  41A (1976) — Article 316(2) State/Joint PSC age 60→62
amendment-040  e597d0d  40A (1976) — Article 297 EEZ added; Ninth Schedule +64 entries (incl. SAFEMA, ULC, MV Act 66A)
amendment-039  b2ad679  39A (1975) — Article 71 restructured; new Article 329A (Indira Gandhi election ouster); Ninth Schedule +38 entries (incl. RPA 1951)
amendment-038  a0c7ae5  38A (1975) — Emergency-era ouster: judicial review of Presidential/Governor/Administrator satisfaction barred across articles 123, 213, 239B, 352, 356, 359, 360
amendment-037  72d78ae  37A (1975) — Arunachal Pradesh added to articles 239A and 240 UT-legislature framework
amendment-036  767dd3d  36A (1975) — Sikkim becomes full State; 35A's associated-state framework dismantled; new Article 371F
                                    [pre-36A correction commit 58ea4d2: applied PRA 1966, Madras Rename 1968, HP State Act 1970, NEAR 1971, Mysore Rename 1973]
amendment-035  d1917d2  35A (1974) — Sikkim as associated state; new Article 2A and Tenth Schedule
amendment-034  36af13a  34A (1974) — Ninth Schedule +20 entries
amendment-033  16da40d  33A (1974) — Articles 101/190 — MP/MLA resignation requires Speaker/Chairman acceptance
amendment-032  ...     32A (1973) — Article 371D / 371E inserted; Article 371 cl(1) omitted with placeholder; Schedule 7 entry 63 substituted
amendment-031  ...     31A (1973) — LS seat limits 500→525 / 25→20; ST exclusions extended to Meghalaya/Arunachal/Mizoram
amendment-030  ...     30A (1972) — Article 133(1) civil appeals restricted to "substantial question of law of general importance"
```

**Two correction commits in the timeline so far:** (consolidate non-368 Acts before an amendment that operates on a state we couldn't reach with 368-only)
- `3bf5179` Pre-14A correction — APM 1959 + BRA 1960 + SNA 1962 applied to Schedules 1 and 4
- `58ea4d2` Pre-36A correction — PRA 1966 + Madras Rename 1968 + HP State Act 1970 + NEAR 1971 + Mysore Rename 1973 applied to Schedules 1 and 4

**65 amendments remain.** Next: **42A** — the Mini-Constitution, biggest amendment ever (~50 articles touched, multiple new parts/schedules). Will need substantial preparation.

**Archive branch** `archive/pre-redo-2026-05-09` (on origin) preserves the pre-redo work (the 6 amendments + 4 baseline-fix commits done against the old baseline).

**Baseline branch** `baseline-1950` (on origin) is a long-lived parallel branch that mirrors what the 1950 Constitution *should* look like. It diverged from `v1.0-baseline` and accumulates only baseline-fix commits — never amendment commits. Use case:

```bash
git diff baseline-1950 main -- articles/article-X.md   # everything that's happened to article X since 1950
```

Workflow when a baseline gap surfaces (rare — should be rarer over time):

1. Edit on `main`, commit as `Baseline fix: …`, push.
2. `git checkout baseline-1950`, apply the same content diff (frontmatter stays in 1950-shape: no `amended_by`, `current_as_of: "1950-01-26"`), commit, push.
3. `git checkout main` and continue.

If the gap involves a clause/article that was later amended, the baseline-1950 version carries the **pre-amendment 1950 form**, while main carries the post-amendment form. (See Article 366 cl(30): "Uparajpramukh" on baseline-1950, "Union territory" on main.)

**One known baseline gap closed so far:** Article 366 cl(22)-(30) — both branches updated 2026-05-09 from CLPR per-article scrape + manuscript verification. The CLPR consolidated 1950 page truncates at cl(21); per-article had all 30 in 1950-form but wasn't consulted at v1.0-baseline time. Manuscript verification surfaced one CLPR per-article drift: cl(22) cross-ref is "article 291" in 1950, not "article 363".

## Working conventions developed in this phase

Saved as memory files under `~/.claude/projects/-Users-akash-github-constitution-of-india/memory/`:

1. **`current_as_of` = assent date, always.** All textual changes (including those gated on Presidential notification or "appointed day") are applied at the Act's Presidential assent date. Operational deferrals live in commit messages, not frontmatter.
2. **Correction commits between amendments.** At most ONE correction commit between any two amendments. Accumulates non-368 Act changes (state reorganisation Acts, etc.) plus discovered baseline fixes. Amendment commits stay pristine — show only what the Act did.
3. **Clause omission convention.** When an amendment omits a clause within a multi-clause article, KEEP original numbering of remaining clauses (don't renumber). Insert an italic placeholder marker for the omitted clause. Distinct from full-article repeal or amendment-mandated renumber/re-letter.
4. **Schedule 4 reconstruction pattern.** When a 368-amendment operates on a Schedule 4 entry-number/total that doesn't match our state, research the intervening non-368 Acts (state reorganisation, alteration-of-name, NE reorganisation, HP state act, etc.) and apply them all in one correction commit. See pre-14A and pre-36A commits as templates.

## Notable threading through the timeline

- **35A → 36A (12 weeks)**: the Sikkim associated-state framework lived only briefly. Tenth Schedule (Sikkim) was repealed by 36A; the "Tenth Schedule" slot was reused by 52A in 1985 for the anti-defection law (different content entirely).
- **38A → 39A → 40A (Emergency-era cluster, 1975-76)**: all three apply during Emergency. 38A immunises Presidential satisfaction; 39A retrospectively shields PM/Speaker elections (Article 329A); 40A adds EEZ and inflates Ninth Schedule by 64 entries. Several 38A/39A provisions are reversed by 44A in 1978.
- **39A cl(4) of Article 329A** struck down in Indira Nehru Gandhi v. Raj Narain (Nov 1975); entire Article 329A omitted by 44A.

## 2. Pipeline cheat-sheet

```bash
uv sync --extra dev
uv run indlaw --help

# Phase 1 inputs (already cached)
indlaw scrape-clpr               # 495 article URLs from CLPR (per-article)
indlaw scrape-clpr-schedules     # 21 schedule URLs from CLPR
indlaw extract-ik                # parse offline IK HTML
indlaw extract-manuscript        # parse pipeline/sources/manuscript/*.txt

# Baseline (re-runnable; produces the corrected v1.0-baseline)
uv run python -m pipeline.extract.clpr_consolidated  # extract from consolidated page
indlaw render-articles
indlaw render-parts
indlaw render-schedules

# Phase 2 inputs (cached)
indlaw extract-legislative       # parse docs/legislative-amendments.html (Akamai-saved manually)
indlaw download-amendments       # 106 PDFs → docs/amendments/{NNN}.pdf

# Metadata
indlaw build-provenance
indlaw build-crossrefs
indlaw build-amendments          # unified amendments index, 4 sources triangulated
```

## 3. Per-amendment workflow

For each remaining amendment N (`docs/amendments/NNN.pdf`):

1. **Read the PDF** end to end. Try `pdfplumber` first — when it returns chars=0 the PDF is a scan; render at `pdftoppm -r 300` and OCR with **both** tesseract and `lit parse --dpi 300` (the `/liteparse` skill / `lit` CLI). Cross-verify the operative section verbatim. On disagreement, render the line at 600 DPI and inspect the image directly. **Above all, escalate to the user** — they have the PDF open and will read it. The user's reading is the final source of truth.

2. **Cross-check the touched-articles list** against `metadata/amendments.json` for amendment N (pykih + IK seeds). Discrepancies are interesting but not blocking. Note that pykih sometimes mislabels schedules as low-numbered articles (e.g. "007" for Schedule 7).

3. **Validate-before-patch.** For every article/schedule/part the amendment claims to touch, verify our current corpus matches the BEFORE state the amendment expects. With the corrected v1.0-baseline, mismatches are now rare — but they happen (Article 366 has a documented baseline gap; some §27 / §29 phrases were already in post-amendment form due to residual CLPR drift). When mismatches are found, **bundle ALL baseline corrections for the amendment cycle into a single consolidated commit** between the previous amendment commit and this amendment commit. Do NOT split per-article. Do NOT fold baseline fixes into the amendment commit (a non-technical reader of the amendment diff would otherwise see edits that aren't actually in the Act).

4. **Apply edits.** Direct edits to `articles/article-NNN.md`, `schedules/schedule-NN.md`, `parts/part-X.md`. Frontmatter on every touched file:

   ```yaml
   amended_by:
     - "The Constitution (Nth Amendment) Act, YYYY"
     # earlier amendments accumulate above
   current_as_of: "YYYY-MM-DD"   # the act's date of assent
   ```

   For new articles: add `inserted_by: "The Constitution (Nth Amendment) Act, YYYY"`. For substituted-entirely articles: flip `source: legislative-gov-in` and update `source_url` to the Act's PDF.
   For repealed articles: `status: repealed`, `repealed_by: "..."`, body replaced with a `*[repeal marker]*` (see Article 238 / 232 / 379 for examples).
   For new schedules: `inserted_by: + source: legislative-gov-in + source_url:`.

5. **Tag the amendment commit** `amendment-NNN` (3-digit zero-padded; annotated; tag message = full Act title + assent date). `git tag --list "amendment-*"` filters Phase 2 history out of the noise.

6. **Push** the commit AND the tag.

7. **Don't commit often.** Resist per-article baseline-fix commits, doc-touchup commits, progress commits. The repo's audience is non-technical lawyers / journalists / students; a noisy `git log` is hostile to them.

### For *big* amendments (10+ touched articles)

The 7th Amendment was the first big one (132 files). Approach:
- Use `docs/amendment-NNN-progress.md` as a session-spanning todo (untracked; deleted before commit).
- Spread work across multiple sessions; working tree accumulates uncommitted changes.
- Use Python scripts in `/tmp/` for mechanical batch substitutions (e.g. drop "or Rajpramukh" across many articles). Keep changes verifiable and small per pattern.
- Spot-check before committing — script-applied substitutions can leave grammatical noise (stranded "or"s, doubled commas) that requires hand-fixing.
- Single commit at end with a detailed multi-section message walking section-by-section.

## 4. Decisions that aren't obvious from the code

- **Manuscript precedence on overlap.** Where a Markdown file has both a CLPR-derived and a manuscript-derived source, manuscript wins. Frontmatter `source: mixed` flags hybrid origin. See `pipeline/render/markdown.py` `collect_baseline()`.
- **Parts have tracking metadata** (`status`, `inserted_by`, `repealed_by`, `amended_by`, `current_as_of`) since amendment-001. Update them when an amendment touches a Part — article-membership changes (insertion, repeal) should be reflected in the `articles:` list.
- **CLPR consolidated vs per-article.** Per-article pages drift to post-amendment text under their "Constitution of India 1950" labels in a non-trivial fraction of cases. The consolidated `/constitution-of-india-1950/` page is more reliable. The current v1.0-baseline uses consolidated as primary, with per-article fallback for 5 articles missing from consolidated (142, 199, 300, 342, 375).
- **CLPR feedback draft** is at `docs/clpr-feedback-draft.md` (untracked) — listing all the discrepancies we found with their data; ready to send when the user is ready.
- **Article 366 baseline gap**: clauses (22)–(29) of the 1950 form are missing from both CLPR sources (both truncate at cl(21)). Flagged in the article's frontmatter `note:` for back-fill from Aggarwala. Doesn't block Phase 2 work but should eventually be fixed.
- **Akamai shenanigans.** legislative.gov.in's listing page is behind Akamai bot detection; the rendered HTML must be saved manually from a real browser (`docs/legislative-amendments.html`, gitignored). The static-CDN PDFs work programmatically only with browser-like headers (User-Agent, Referer, Sec-Fetch-*).
- **PDFs and IK HTML are gitignored.** SHA-256s in `metadata/provenance.json` for verifiability.
- **Amendment commits are one logical commit each** (PRD §5.7). Mirrors `nickvido/us-code` snapshot-as-commit model.
- **Deferred amendments**: §8(2) of the 7th Amendment defers Madhya Pradesh insertion in Article 168(1)(a) to a future Presidential notification. NOT applied. If/when the notification is tracked, a follow-up commit will add it.

## 5. Source landscape recap

| Source | Path | Coverage | Role |
|---|---|---|---|
| CLPR consolidated 1950 page | `pipeline/intermediate/clpr-scout/constitution-1950.html` (gitignored) → `pipeline/intermediate/scraped/articles-consolidated/` | 390 articles | **Primary baseline source** (post-redo) |
| CLPR per-article pages | scraped to `pipeline/intermediate/scraped/articles/` | 389 articles | Fallback for 5 articles missing from consolidated; not authoritative for 1950 baseline |
| CLPR per-schedule pages | `pipeline/intermediate/scraped/clpr-schedules/` | 16 segments / 8 schedules | Schedule baseline |
| Lok Sabha calligraphic 1950 manuscript | `pipeline/sources/manuscript/article-NNN.txt` (tracked) | 6 article fills + 5 spot-checks + 2 schedule fills + various baseline-correction back-fills | Authoritative 1950 source |
| Indian Kanoon | `docs/ConstitutionofIndia_IK.html` (gitignored) → `pipeline/intermediate/scraped/ik/` | 498 records, 95 distinct amendment-act citations | Cross-check + amendment seed |
| pykih | `pipeline/sources/pykih/{amendments,data}.json` (tracked) | 99 amendments + 440 (amendment, article, status) triples | Phase 2 cross-validation |
| Aggarwala 1950 facsimile | `docs/constitutionofin_1ed_fulltext.txt` (gitignored) | full 1950 text | Audit / back-fill source for missing baseline content |
| legislative.gov.in (Ministry of Law and Justice) | `docs/legislative-amendments.html` + `docs/amendments/{NNN}.pdf` (both gitignored) | 106 amendment Acts as PDFs | **Phase 2 authoritative source** |

## 6. Phase 2 backlog

Next ten amendments (chronological):

| # | Year | Date | Short summary (from pykih) |
|---|---|---|---|
| 8 | 1959 | … | Reservation of seats for SC/ST; languages. |
| 9 | 1960 | … | Adjustment of names of States. |
| 10 | 1961 | … | Dadra and Nagar Haveli. |
| 11 | 1961 | … | Amendments to articles 66 and 71 (Vice-President election). |
| 12 | 1962 | … | Goa, Daman and Diu becoming part of India. |
| 13 | 1962 | … | Special status for Nagaland. |
| 14 | 1962 | … | Pondicherry; HC for UTs. |
| 15 | 1963 | … | HC judges' age, etc. |
| 16 | 1963 | … | Oath of office; secularism etc. (Sixteenth A) |
| 17 | 1964 | … | Land acquisition; Ninth Schedule additions. |

Full list with PDF paths and known-touched-articles in [`metadata/amendments.json`](../metadata/amendments.json).

## 7. What to do on a fresh session

1. `git pull` (origin/main is the source of truth).
2. `uv sync --extra dev` (Python deps).
3. Read this file + the relevant section of `docs/prd-constitution-v1.md` if needed.
4. Inspect amendments.json for the next amendment: `cat metadata/amendments.json | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['amendments'][7], indent=2))"`
5. Read `docs/amendments/NNN.pdf` (pdfplumber for text-layer; tesseract+liteparse for scans).
6. Validate, edit, commit, tag. Same workflow as amendments 1–7.

## 8. Where to look for canonical examples

- `amendment-007` (commit `db7b020`) — canonical example of a *large* amendment.
- `amendment-001` (commit `6c3f148`) — canonical example of a multi-article amendment with new article inserts.
- `amendment-002` (commit `2fdd5f0`) — canonical example of a tiny single-clause amendment.
- `amendment-003` (commit `c08b5d2`) — canonical example of a scanned-PDF amendment with OCR.
- `amendment-005` (commit `69e74dc`) — canonical example of a single-article-substitution.
- `articles/article-031A.md`, `articles/article-031B.md` — canonical inserted-article frontmatter shape.
- `articles/article-238.md`, `article-242.md`, `article-379.md`–`article-391.md` — canonical repealed-article shape.
- `parts/part-vii.md`, `parts/part-ix.md` — canonical repealed-part shape.
- `articles/article-366.md` — canonical "baseline gap" `note:` field shape.

Good luck.
