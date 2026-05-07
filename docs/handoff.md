# Handoff — `indian-law-git` / Constitution v1

**Purpose of this document:** to give a fresh Claude Code session (or human collaborator) enough context in 5 minutes to start building, without having to re-derive decisions that were already made.

**Read this with:**

1. `docs/prd-constitution-v1.md` — the authoritative spec.
2. `can I build something like this for india.md` — original research notes (data sources, prior art, source landscape).

If anything in this handoff conflicts with the PRD, **the PRD wins**.

---

## 1. How we got here

The user (Akash) ran a structured discovery process before any code was written:

1. **`/grill-master`** — a relentless interview pass. Walked the design tree branch by branch (purpose, scope, granularity, amendment-history strategy, source of truth, file structure, repo organization, parsing approach, tech stack, cross-references). Each branch was decided explicitly with stated tradeoffs.
2. **`/spec-writer`** — converted the confirmed shared understanding into a comprehensive PRD (`docs/prd-constitution-v1.md`).
3. **This handoff** — a quick-reference launchpad for the next session, which will be in a fresh repo cloned from a new GitHub org.

The grill-master conversation already pushed back on temptations (e.g., backward-replay, full-AKN-XML strategy, mimicking `indiacode.nic.in` for the org name). Don't relitigate those decisions without a real reason; they're locked in.

## 2. What's locked in (do not relitigate without cause)

| Decision | Choice |
|----------|--------|
| Scope of v1 | Constitution of India, English only, full amendment history, intra-Constitution cross-refs |
| Direction of pipeline | **Forward replay from 1950 baseline.** Not backward. Not snapshot-based. |
| Source of truth (root commit) | Lok Sabha's "Constitution as adopted on 26 January 1950" PDF |
| HEAD verification | Final state must match India Code's current consolidated text |
| File granularity | One file per Article (`articles/article-NNN.md`), one per Schedule, parts as thin manifests |
| Repealed articles | Stay as files with `status: repealed` frontmatter + tombstone — not deleted |
| Amendment-as-commit semantics | One amendment = one commit (or one logical commit set if it touches many articles) |
| Parsing strategy | LLM-end-to-end with structured edit output + automated round-trip verification |
| Trust bar for commit | Round-trip auto-check passes **AND** lawyer review passes |
| Language | Python |
| PDF tooling | pdfplumber + pdfminer + `lit` (liteparse), cross-checked |
| LLM workflow | Phase 1: interactive Claude Code (first ~5 amendments). Phase 2: scripted Anthropic API. |
| Repo shape | Single repo containing pipeline code + law text + metadata |
| Org/repo name | Working name `indian-law-git`. **Avoid names that mimic `indiacode.nic.in`.** |
| Posture | Best-effort, clearly labeled. README must say "not legal advice." |

## 3. What's still open (TBDs that don't block starting)

- **License for the law text itself** — pending read of India Code Terms of Use + lawyer-friend consult. Pipeline code is MIT/Apache. Can ship Phase 1 baseline before resolving.
- **Final repo name** — `indian-law-git` is working; pick the final name after first 5 amendments are committed and the project has shape.
- **Lok Sabha 1950 PDF quality** — unknown until inspected. May need OCR.
- **Round-trip verification prompt design** — empirical; iterate during the first 5 amendments.
- **Source of the 106 individual amending acts** — India Code lists them; quality of each scan unknown until inventoried.
- **Human-review frequency** — calibrate after first 10 amendments based on round-trip-pass rate.

See PRD §9 for the complete open-questions table with owners and resolution paths.

## 4. Recommended first moves in the new repo

In this exact order:

1. **Scaffold the repo skeleton** matching PRD §5.1. Create empty directories (`articles/`, `schedules/`, `parts/`, `metadata/`, `pipeline/`) with `.gitkeep` files. Stub the README, CONTRIBUTING, LICENSE (pipeline), LICENSE-TEXT (placeholder).
2. **Set up `pipeline/` Python project.** Pick `uv` or `poetry` for env management; add `pdfplumber`, `pdfminer.six`, `anthropic` (SDK), `pyyaml`, `typer` (CLI), `pytest` as initial deps. Follow `claude-api` skill guidance for the Anthropic SDK setup.
3. **Inspect the Lok Sabha 1950 PDF.** Source it (start with `legislative.gov.in` or `loksabhadocs.nic.in`), check whether it's text-layer or scanned-only. This determines the OCR question.
4. **Write `pipeline/extract/`** — three independent extractors (pdfplumber, pdfminer, lit) + a cross-check function that flags disagreements. Test against the 1950 PDF.
5. **Phase 1 baseline ingest.** Parse the 1950 PDF into article + schedule + part files. Hand-verify a sample (~5 random articles) against the source. Commit as the root commit with provenance metadata.
6. **Stop and review with Akash + a lawyer friend** before starting Phase 2 (amendments). The Phase 1 output is independently publishable as "Constitution of India, as adopted, 26 January 1950 — Markdown edition." That's a real artifact and a useful checkpoint.
7. **Phase 2 — first 5 amendments interactively in Claude Code.** Goal is to learn the data, not to scale. Refine the parse and round-trip prompts. Keep the LLM responses cached.

Don't try to script the full pipeline before completing step 5. Premature automation is the most likely way this project dies in engineering rather than data work.

## 5. Things to be careful about

- **Don't commit `pipeline/intermediate/`.** That's where uncached LLM responses, working PDFs, and intermediate JSON live. Gitignore aggressively. The published repo shows only verified output.
- **Don't write commit messages by hand.** Use the structured format from PRD §5.7 generated by `pipeline/commit/`. Hand-written messages will drift in shape and break downstream tooling.
- **Don't confuse "round-trip check passed" with "this is correct."** The check can pass on a self-consistent but wrong interpretation. Lawyer review is load-bearing per the trust bar.
- **Don't optimize for breadth over depth on Phase 2.** Get the first amendment fully right (with its diff verifiable by a lawyer) before doing the second. The grill-master explicitly chose Constitution-first / depth-first for this reason.
- **Don't pick a final org/repo name that mimics `indiacode.nic.in`.** Real risk of user confusion and possible takedown pressure. Acceptable patterns: `indian-law-git`, `bharat-law`, `samhita`, `code-of-india`, etc. Avoid: `india-code`, `indiacode`, anything that reads as "official."
- **Don't skip provenance.** Every source PDF cited in `metadata/provenance.json` with URL + SHA-256 + retrieval date. This is the foundation of the project's credibility.

## 6. Project tone

The user is comfortable with terse, honest collaboration. The grill-master conversation pushed back on choices when the user's stated plan didn't match the engineering reality, and the user appreciated it — they explicitly went "all-in" on the hardest path (full backfill via amendment-instruction parsing) after hearing the warnings. Don't soft-pedal real engineering risks; they're on the table on purpose.

The user has lawyer friends willing to review. Treat lawyer review as a project asset to plan around, not an afterthought.

## 7. What to bring forward into the new repo

When the user creates the new repo and clones it, copy these files from `ind-code/`:

- `docs/prd-constitution-v1.md` → `docs/prd-constitution-v1.md` (authoritative spec)
- `docs/handoff.md` → `docs/handoff.md` (this file)
- `can I build something like this for india.md` → `docs/research-notes.md` (rename for sanity)

The `ind-code/` directory itself can be archived or deleted; nothing else from it carries forward.

---

*If you (the next Claude Code session) hit a question this handoff or the PRD doesn't answer, check the PRD's open-questions table (§9) before asking the user — it's likely already flagged.*
