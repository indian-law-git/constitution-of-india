# Pipeline

The reproducible pipeline that ingests Government of India source PDFs and produces the article/schedule/part Markdown files at the repo root, plus the cross-reference and provenance metadata.

**Status:** scaffolded; modules are stubs.

See [`../docs/prd-constitution-v1.md`](../docs/prd-constitution-v1.md) §5.5 and §7 for the design.

## Modules

| Module | Responsibility |
|--------|----------------|
| `extract/` | PDF → text. Three independent extractors (pdfplumber, pdfminer, lit) cross-checked. |
| `parse/` | Text → structured edit operations (LLM-driven). |
| `apply/` | Apply structured edits to article files. |
| `verify/` | Round-trip verification + HEAD-state verification against India Code. |
| `commit/` | Git commit orchestration + structured commit messages (PRD §5.7). |
| `crossref/` | Intra-Constitution cross-reference indexer. |
| `llm/` | Anthropic SDK wrapper, prompt templates, response cache. |
| `cli/` | CLI entry points. |

## Setup

TBD — Python env tool (uv vs poetry) being decided. Once chosen, this section will document `pipeline/` install + run.

## Phasing

- **Phase 1** — interactive Claude Code over the first ~5 amendments. Goal: learn the data, refine prompts.
- **Phase 2** — scripted Anthropic API for the bulk amendments. Cached responses, batched.

See PRD §7.2 and Appendix A.
