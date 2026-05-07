# PRD — `indian-law-git`: Constitution v1

**Status:** Draft
**Author:** Akash Kamble
**Created:** 2026-05-07
**Working name:** `indian-law-git` (final repo name TBD)

---

## 1. Summary

`indian-law-git` is a Git repository that mirrors the Constitution of India as a structured Markdown corpus, where every constitutional amendment is a discrete commit and the repo's `git log` reconstructs Indian constitutional history from 26 January 1950 to the present. v1 covers the Constitution only (English text), with forward-replayed amendment history and an intra-Constitution cross-reference graph. The target users are researchers, journalists, lawyers, and informed citizens who need to inspect, diff, or programmatically query the Constitution's text and evolution. Inspired by `nickvido/us-code`, but adapted to India's source landscape, where no equivalent of OLRC's clean versioned XML exists.

## 2. Problem Statement

- The authoritative source for Indian law (`indiacode.nic.in`) publishes Acts as PDFs and serves only the *current consolidated* text. There is no machine-readable bulk export, no version history, and no commit-style timeline.
- Amendment history is scattered across separate amending acts. To reconstruct "what did Article 21 say in 1985?", a reader must locate the 1950 baseline, then manually walk every amending act that touched Article 21 in chronological order — a non-trivial research task.
- Existing structured datasets are partial and stale:
  - `nyaayaIN/laws-of-india` (Akoma Ntoso XML) — last meaningful update around 2018.
  - Zenodo dataset (858 Central Acts as JSON, 1838–2020) — single snapshot, no version history.
- Prior art `nickvido/us-code` demonstrates the value of "law as code" for the United States, but only because OLRC publishes the US Code as cleanly-versioned USLM XML. India lacks an equivalent free machine-readable source.
- A `git`-native, diffable, blame-able representation of Indian constitutional law does not currently exist as an open public artifact.

Evidence:
- Manual inspection of `indiacode.nic.in` (PDFs only, no XML).
- Public discussion threads (HN, LinkedIn, Reddit r/legaltech, r/LegalAdviceIndia) consistently citing the access gap.
- Research material in `can I build something like this for india.md` (this repo).

## 3. Goals and Non-Goals

### Goals

1. Publish the full text of the Constitution of India as Markdown, with one file per Article and one file per Schedule.
2. Reconstruct all ~106 amendments as discrete chronological commits, each amendment landing as one commit (or one logical commit set if it touches many articles).
3. The repo's HEAD must match the current consolidated Constitution as published by the Lok Sabha / India Code, within a documented tolerance — this is the integration test.
4. Generate a complete intra-Constitution cross-reference index (article → article, article → schedule, schedule → article).
5. Provide reproducible provenance for every commit: source PDF citation, parser version, LLM responses cached.
6. Establish a dual-review workflow (maintainer + lawyer friend) and document it for ongoing maintenance.
7. Ship a public, browsable repo with a README that frames the project honestly: best-effort, not legal advice, contributions welcome.

### Non-Goals

- Central Acts (deferred to v2).
- State Acts (deferred indefinitely).
- Hindi or regional-language texts (deferred; English-only for v1).
- Subordinate legislation (rules, regulations, notifications, orders).
- Inter-Act citation graph (the Constitution doesn't cite Acts, so this only matters once Acts ship).
- Web UI, search interface, or API service. The repo *is* the artifact.
- Real-time freshness automation — v1 is human-in-the-loop.
- Legal interpretation, case law, or commentary.
- Authoritative attestation or e-signature.

## 4. User Stories

1. **As a constitutional researcher**, I want to see Article 21's full amendment history so I can study how the right to life clause has evolved.
2. **As a journalist**, I want to `git diff` the Constitution between two specific amendments so I can show readers concrete textual changes.
3. **As a lawyer**, I want to `grep` the corpus for cross-references to Article 14 so I can quickly locate every related provision.
4. **As an interested citizen**, I want to read the current Constitution as plain Markdown so I can understand my rights without commercial sources.
5. **As a constitutional law student**, I want to `git log articles/article-031.md` to see the full history of when and how Article 31 was repealed.
6. **As an external contributor**, I want to submit a PR fixing a typo or formatting issue so the repo improves with community help.
7. **As the maintainer (Akash)**, I want every amendment commit to pass an automated round-trip check before review so I don't waste reviewer attention on obviously-broken commits.
8. **As a lawyer-reviewer**, I want batched review requests (e.g., one batch per amendment) so I can sign off without being interrupted commit-by-commit.
9. **As a downstream-tool builder**, I want a JSON cross-reference index (`metadata/cross-references.json`) so I can build a citation graph or other analyses without re-parsing Markdown.
10. **As a developer**, I want each article file to have YAML frontmatter (article number, part, status, amendment list) so I can iterate the corpus programmatically.
11. **As an academic**, I want every commit message to cite the source amending act with its name, number, and date of assent so I can reproduce my analysis.
12. **As a researcher**, I want repealed articles to remain as tombstone files (with `status: repealed` frontmatter) so I can still find Article 31 even though it no longer has substantive content.
13. **As a contributor**, I want a documented reproducible pipeline (`pipeline/` directory + README) so I can run it locally and validate or recreate a commit.
14. **As a downstream consumer**, I want a stable file naming scheme (`articles/article-019.md`, `articles/article-031A.md`) so external tools can deep-link to specific articles.
15. **As the maintainer**, I want intermediate parser artifacts kept out of the published repo (gitignored) so reviewers see only verified output.
16. **As a reviewer**, I want clear flags on commits where the LLM's interpretation was uncertain (e.g., low confidence, multiple valid parses) so I can prioritize my attention.
17. **As a researcher**, I want the 1950 baseline source PDF cited (with URL and SHA-256) in the root commit so I can verify provenance.
18. **As a downstream tool**, I want to detect that an article is repealed via the `status: repealed` frontmatter field without parsing the article's prose.
19. **As a maintainer**, I want amendments that touch many articles (e.g., 42nd Amendment) to land as a single commit so the diff communicates the amendment's scope honestly.
20. **As an analyst**, I want a `metadata/amendments.json` index listing every amendment with its number, short title, assent date, commencement date, and articles touched, so I can build timelines without parsing commit messages.

## 5. Functional Requirements

### 5.1 Repository file structure

```
indian-law-git/                           (repo root, working name)
├── README.md
├── CONTRIBUTING.md
├── LICENSE                                # for pipeline code
├── LICENSE-TEXT                           # for law text (TBD; see §9)
├── articles/
│   ├── article-001.md
│   ├── article-019.md
│   ├── article-031.md                    # status: repealed (tombstone)
│   ├── article-031A.md                   # inserted by 1st Amendment
│   ├── ...
│   └── article-395.md
├── schedules/
│   ├── schedule-01.md
│   ├── ...
│   └── schedule-12.md
├── parts/
│   ├── part-i.md                          # manifest only — ordering + metadata
│   ├── part-ii.md
│   └── ...
├── metadata/
│   ├── cross-references.json
│   ├── amendments.json
│   └── provenance.json                    # source PDFs, SHA-256, retrieval dates
├── pipeline/                              # parser source code
│   ├── extract/
│   ├── parse/
│   ├── apply/
│   ├── verify/
│   ├── commit/
│   ├── crossref/
│   ├── llm/
│   │   └── prompts/
│   ├── cli/
│   └── README.md
└── .gitignore                             # excludes pipeline/intermediate/, .cache/
```

### 5.2 Article file format

```markdown
---
article: 19
part: III
title: "Protection of certain rights regarding freedom of speech etc."
status: active                  # one of: active, repealed
inserted_by: original           # or: "1st Amendment, 1951"
repealed_by: null               # or: "44th Amendment, 1978"
amended_by:
  - "1st Amendment, 1951"
  - "16th Amendment, 1963"
  - "44th Amendment, 1978"
current_as_of: "2026-05-07"
source: "lok-sabha-2024-edition"
---

# Article 19. Protection of certain rights regarding freedom of speech etc.

(1) All citizens shall have the right—
  (a) to freedom of speech and expression;
  (b) to assemble peaceably and without arms;
  ...
```

### 5.3 Schedule file format

Same shape as articles but with `schedule:` instead of `article:` in frontmatter, and no `part:` field.

### 5.4 Part manifest format

```markdown
---
part: III
title: "Fundamental Rights"
articles: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 21A, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 31A, 31B, 31C, 31D, 32, 32A, 33, 34, 35]
---

# Part III — Fundamental Rights

This Part contains Articles 12 through 35. See individual article files in `articles/`.
```

(Manifests are thin — they exist for navigation and tooling, not as duplicate content.)

### 5.5 Pipeline phases

- **Phase A — Baseline ingestion.** Parse the 1950 Lok Sabha PDF into article + schedule + part files. One commit: "Constitution of India as adopted, 26 January 1950." Source PDF URL + SHA-256 in commit message and `metadata/provenance.json`.
- **Phase B — Amendment ingestion (per amendment, in chronological order).**
  1. Locate amending act PDF (India Code or Gazette of India).
  2. Extract text with pdfplumber + pdfminer + `lit` (cross-checked).
  3. LLM produces structured edit operations.
  4. Apply edits to relevant article files.
  5. Round-trip verification (LLM re-derives instruction from diff; compare to original).
  6. Maintainer + lawyer review the staged diff.
  7. On approval, commit with structured message (§5.7).
  8. Update affected articles' frontmatter (`amended_by`, `current_as_of`).
- **Phase C — Cross-reference indexing.** After each amendment commit, regenerate `metadata/cross-references.json` and amend the same commit (or land as the immediately following commit, depending on workflow choice).
- **Phase D — HEAD verification.** After all amendments applied, render full text from articles in part-order + schedules; compare to text extracted from India Code's current consolidated Constitution PDF. Discrepancies block release.

### 5.6 Amendment parsing — structured edit format

Each LLM-produced edit operation is a JSON object:

```json
{
  "op": "substitute",
  "target": "article-019/clause-1/sub-clause-a",
  "find": "subject to the provisions of clause (2)",
  "replace": "subject to the reasonable restrictions imposed by sub-clause (a) of clause (2)",
  "confidence": 0.95,
  "rationale": "Direct substitution per amending act §2(a)."
}
```

Supported ops (initial set; expand as edge cases surface):

- `substitute` — replace text within a target.
- `insert_after` / `insert_before` — insert new content adjacent to a target.
- `delete` — remove a target.
- `renumber` — reassign clause/sub-clause numbers.
- `repeal` — full article repeal (special-cased; produces tombstone).
- `insert_article` — new article (creates new file).

### 5.7 Commit message format

```
{Amendment Number} ({Year}): {Short title from amending act}

Amending act: The Constitution ({Number}) Amendment Act, {Year}
Date of assent: YYYY-MM-DD
Date of commencement: YYYY-MM-DD          # if different from assent
Articles touched: 19, 21, 22
Source PDF: {URL}
Source SHA-256: {hex}
Pipeline version: {git-rev-of-pipeline-at-time-of-commit}
Round-trip check: passed
Reviewed by: {Akash}, {Lawyer-Initials}
```

### 5.8 Repealed article handling

When an article is repealed:
- File remains; body content is replaced with a tombstone notice citing the repealing amendment.
- Frontmatter: `status: repealed`, `repealed_by: "{Amendment citation}"`.
- Title in body gains a `[REPEALED]` suffix.
- File is NOT deleted from the repo, ensuring `git log articles/article-NNN.md` continues to tell the full story.

### 5.9 Insertion numbering

- New articles inserted by amendment use suffix letters in the order they appear in the source: 31A, 31B, 31C, ..., 31I.
- File naming: `article-031A.md` (zero-padded numeric prefix preserves filesystem sort order).
- Same convention applies to inserted clauses within an article.

### 5.10 Cross-reference index format

`metadata/cross-references.json`:

```json
{
  "article-019": {
    "outbound": ["article-014", "article-021", "schedule-09"],
    "inbound": ["article-021", "article-358"]
  },
  "schedule-09": {
    "outbound": [],
    "inbound": ["article-031B"]
  }
}
```

Detection rules:
- Match `Article \d+[A-Z]?`, `article \d+[A-Z]?`, `Articles? \d+ to \d+`, `Schedule \w+`, `the {Ordinal} Schedule`.
- Normalize to canonical IDs (`article-019`, `schedule-09`).
- Excludes references in YAML frontmatter to avoid double-counting.

### 5.11 HEAD verification protocol

After replaying all amendments:
1. Concatenate all active articles (in part-order) + all schedules → render to plain text.
2. Extract text from the official current Lok Sabha / India Code consolidated Constitution PDF.
3. Normalize both (whitespace, hyphenation, footnote handling).
4. Diff. Tolerance: cosmetic differences (e.g., footnote markers) acceptable; substantive differences (different wording, missing/extra articles) block release.
5. Document any acceptable residual differences in `metadata/known-discrepancies.md`.

## 6. Non-Functional Requirements

- **Reproducibility.** Every commit is reproducible from the pipeline given (a) the same source PDFs (cited by URL + SHA-256), (b) the same pipeline version, (c) the same LLM responses (cached locally; cache is part of `pipeline/intermediate/` and is shareable but not committed to the public repo).
- **Provenance.** `metadata/provenance.json` lists every source PDF used, with retrieval URL, retrieval date, and SHA-256.
- **Transparency.** README clearly states "best effort, not legal advice, snapshot as of {date}." `LICENSE-TEXT` separates the law text's licensing from the pipeline code's.
- **Performance.** Not a primary concern (offline batch). Full corpus rebuild from scratch in < 1 day acceptable.
- **Storage.** Repo size at v1 should fit comfortably under GitHub's 1 GB recommendation. Markdown text + JSON metadata ≪ 100 MB.
- **LLM cost ceiling.** Constitution alone: ~106 amendments × ~5–20 articles/amendment × 2 LLM calls (parse + round-trip) ≈ 2,000–4,000 calls. Phase 1 (interactive Claude Code) covers ~5 amendments to learn shape; phase 2 (scripted, batched API) handles the bulk. Budget: a few thousand input/output tokens per call → tractable on Anthropic's standard pricing or free-tier alternatives.
- **Privacy.** No PII processed. All inputs are public legal documents.

## 7. Implementation Notes and Architecture

### 7.1 Module sketch

```
pipeline/
├── extract/        # PDF → text (pdfplumber, pdfminer, lit wrappers + cross-check)
├── parse/          # text → structured edit operations (LLM-driven)
├── apply/          # apply structured edits to article files
├── verify/         # round-trip verification, HEAD-state verification
├── commit/         # git commit orchestration + structured message generation
├── crossref/       # cross-reference indexer
├── llm/            # Anthropic SDK wrapper, prompt templates, response cache
│   └── prompts/
└── cli/            # CLI entry points (Typer or Click)
```

Each module is a deep module: well-defined inputs, well-defined outputs, side effects pushed to the edges (`commit/`, `apply/`). Pure functions where possible. This shape enables unit-testing each phase against fixtures (e.g., test that a known amendment text → expected structured edits, independently of git or LLM availability via cached fixtures).

### 7.2 Key technical decisions (locked in by grill-master)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python | Mature PDF + LLM + legal-NLP ecosystem. |
| PDF extraction | pdfplumber + pdfminer + `lit` (liteparse) | Cross-checked extraction; flag disagreements. |
| LLM | Claude (Anthropic) | Strong on legalese; user has Claude Code + API access. |
| LLM workflow phase 1 | Interactive Claude Code | First ~5 amendments; learn data shape before automating. |
| LLM workflow phase 2 | Scripted Anthropic API (or free-tier alt) | Bulk processing once prompts stable. |
| LLM response caching | Local SQLite or flat JSON | Avoid re-billing on retries; gitignored. |
| Storage backend | Git only; no DB | Repo *is* the database for v1. |
| Direction | Forward replay from 1950 baseline | Inverting amendment instructions is intractable. |
| File granularity | Per-article + per-schedule | Maximizes `git blame` clarity at the natural unit. |
| Repo shape | Single marquee repo for the Constitution | Future Central-Acts repo can be separate; Constitution gets its own visible identity. |
| Git host | GitHub, personal account initially | Transferable to org later; reversible. |

### 7.3 Prompt design — round-trip verification

Two distinct LLM prompts, version-controlled in `pipeline/llm/prompts/`:

- **`parse_amendment.md`**: Given (a) the amending act's text and (b) the current state of relevant articles, produce structured edit operations as JSON.
- **`derive_instruction.md`**: Given (a) a unified diff between pre- and post-amendment article text, produce a natural-language description of what the amendment did.

Round-trip verification: derived instruction (from `derive_instruction.md` on the diff) is semantically compared to the original amending act text. Comparison is itself a third LLM call OR a deterministic semantic-similarity check; design TBD.

Prompts evolve as edge cases are discovered; each commit records the prompt SHA used.

### 7.4 Repository for code vs repository for output

The published repo (`indian-law-git/constitution`) contains *both* the law text (committed as articles, schedules, parts) *and* the pipeline source (in `pipeline/`). One-repo simplicity for v1. If the pipeline grows or is reused for Central Acts, factor out into a separate `indian-law-git/pipeline` repo at that time.

## 8. Out of Scope (v1)

- Central Acts (planned for v2; will reuse the pipeline).
- State Acts (deferred indefinitely; states have inconsistent digitization).
- Subordinate legislation (rules, regulations, notifications, orders).
- Hindi and regional-language texts. Note: Article 348(3) makes the Hindi version of the Constitution constitutionally significant; English-only is a v1 simplification, not a final position.
- Web UI / search / browsable site. The repo, viewed on GitHub, is the artifact.
- API service.
- Inter-Act citation graph (no Acts in v1).
- Real-time scheduled freshness automation (manual trigger for v1).
- Mobile app.
- Authoritative legal attestation, e-signature, or government partnership.
- Case law, commentary, interpretation.
- Migration of the IPC → BNS / CrPC → BNSS (these are Acts, not constitutional).

## 9. Risks and Open Questions

### Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R1 | LLM produces confidently-wrong structured edits on legalese variants the prompt didn't anticipate. | High | Round-trip verification + lawyer review + conservative trust bar. Long tail expected; budget for ongoing prompt refinement. |
| R2 | Round-trip check passes on a self-consistent but incorrect interpretation. | High | Lawyer review is load-bearing, not optional. Sample-audit even passing commits. |
| R3 | Maintainer abandonment after partial completion. | Medium-High | Ship 1950 baseline + first 5 amendments early as public artifact to raise abandonment cost. Set explicit milestones. |
| R4 | Public-good positioning attracts scrutiny once the repo gets visibility; errors become reputational. | Medium | Clear "best-effort, not legal advice" framing in README; obvious contribution path for corrections. |
| R5 | Lok Sabha 1950 PDF may be image-only and need OCR. | Medium | Tesseract + manual verification. Worst case, a published facsimile + manual transcription of the baseline (one-time cost). |
| R6 | India Code's current consolidated text may differ from Lok Sabha's, creating verification ambiguity at HEAD. | Medium | Pick one as authoritative for the HEAD comparison; document the choice and any residual deltas. |
| R7 | Legal status of publishing law text under an open license is unsettled in Indian copyright. | Medium | Pipeline code under MIT/Apache; law text labeled separately as "as-published-by-Lok-Sabha" pending legal review. |
| R8 | Some amendments have conditional commencement (notified separately from assent). | Low-Medium | Commit when "deemed in force"; record both assent and commencement dates in commit message. |
| R9 | Some amendments amend prior amendments or are themselves later struck down (e.g., 39th Amendment partial strike-down). | Medium | Document the legal history in commit messages; structured `amendments.json` records both effective and struck-down status. |
| R10 | Schedule amendments (especially Eighth Schedule — languages) may have different patterns from article amendments. | Low | Same workflow, different prompt template if needed. |

### Open Questions

| ID | Question | Owner | Resolution path |
|----|----------|-------|-----------------|
| Q1 | Where to source the 106 amending acts as separate documents? India Code lists them; Gazette of India archive is more authoritative. Are scans clean? | Akash | Inventory phase before Phase B kicks off. |
| Q2 | Final repo name and GitHub placement (personal vs org). | Akash | Pick after first 5 amendments are committed and the project has shape. |
| Q3 | License determination for the law text. | Akash + lawyer friend | Read India Code Terms of Use; consult lawyer friends. |
| Q4 | Human-review frequency post-bootstrap (every commit? every amendment? sampled?). | Akash | Calibrate after the first 10 amendments based on how often the round-trip check catches issues. |
| Q5 | How to represent "deemed in force" dates that differ from assent dates in commit metadata. | Akash | Document in `commit message` schema (§5.7); decide on date used for chronological ordering. |
| Q6 | How to handle amendments later partially or fully struck down (e.g., 39th Amendment, parts of which were struck down by *Indira Nehru Gandhi v. Raj Narain* in 1975). | Akash + lawyer friend | Document in `amendments.json`; commit the amendment as enacted, with subsequent commit reflecting any strike-down if it changed the text. |
| Q7 | Verification prompt design — concrete prompt that catches realistic failures, not just easy cases. | Akash | Iterate during Phase B's first ~5 amendments; treat as an empirical exercise. |
| Q8 | Ordering tiebreaker: when multiple amendments were assented to on the same day or have overlapping commencement, what's the canonical order? | Akash | Pick alphanumeric amendment number as primary key; document. |

### Fragile Assumptions

- **A1**: The Constitution's amending acts are textually self-contained — i.e., they don't depend on knowledge of other documents to interpret. *Likely true; verify on first 5 amendments.*
- **A2**: India Code's current consolidated text is canonical and matches Lok Sabha's. *Likely true; verify by spot-checking 5 randomly-picked articles.*
- **A3**: Lawyer friends will have time and willingness to review at the cadence the project requires. *Worth confirming with them before launch.*
- **A4**: LLM cost will stay under ~$50 for the full Constitution corpus on Anthropic's standard pricing. *To verify after first ~5 amendments by extrapolation.*

## 10. Success Metrics

### v1 launch criteria (binary)

- [ ] 1950 baseline committed; root commit cites source PDF URL + SHA-256.
- [ ] All 106 amendments committed in chronological order, each with structured commit message.
- [ ] HEAD verifies against India Code's current consolidated Constitution within documented tolerance.
- [ ] `metadata/cross-references.json` generated and committed.
- [ ] `metadata/amendments.json` generated and committed.
- [ ] `metadata/provenance.json` generated and committed.
- [ ] README, CONTRIBUTING, LICENSE, LICENSE-TEXT in place.
- [ ] Pipeline runs reproducibly from a clean clone (documented in `pipeline/README.md`).

### Validation indicators (post-launch, 3–6 months)

- ≥ 1 external corrective PR submitted (signal that contributors trust the foundation enough to engage).
- ≥ 1 cited use of the repo by a journalist, academic, or lawyer.
- Lawyer-friend review workflow operates without becoming a bottleneck (no amendment stalls > 2 weeks awaiting review).
- ≥ 50 GitHub stars within 2 months of launch (rough public-interest proxy; not a hard target).

### Process metrics (during build)

- Round-trip check pass rate: target ≥ 90% on first attempt by amendment #20 (signals prompt has stabilized).
- Lawyer-review override rate: track how often lawyer review changes the diff post-round-trip-pass; informs trust calibration.
- Per-amendment human time: target ≤ 30 minutes of maintainer + reviewer time per amendment by amendment #20 (efficiency proxy).

---

## Appendix A — Phasing suggestion

This PRD describes v1 as a single deliverable, but the realistic execution order is:

1. **Phase 0 — Setup** (1–2 days). Create repo, scaffold `pipeline/`, set up prompts, write `extract/` for PDF → text.
2. **Phase 1 — Baseline** (3–5 days). Ingest 1950 PDF, produce article + schedule + part files, commit root. *This is publishable on its own.*
3. **Phase 2 — First 5 amendments** (1–2 weeks, mostly interactive in Claude Code). Learn data shape. Lock in prompts. *Publishable as "early preview."*
4. **Phase 3 — Bulk amendments** (4–8 weeks part-time). Script the pipeline, batch process. Lawyer review in batches of 5–10 amendments.
5. **Phase 4 — HEAD verification + cross-refs + launch polish** (1 week). Run integration test, generate cross-refs, write README, announce.

Total realistic time-to-launch: **~3 months** part-time, assuming no major surprises in PDF quality or amendment-instruction edge cases. Likelier: **4–6 months** with normal slippage.

If `/spec-to-plan` is invoked next, recommend it use this phasing as the basis for a phased implementation plan with tracer-bullet vertical slices.

---

*End of PRD.*
