# pykih — Constitution data files

Two JSON files mirrored from [`constitution-of-india.pykih.com`](http://constitution-of-india.pykih.com/) (a Pykih project that visualises constitutional amendments, originally built around a 2015 article in *The Hindu*: "How the Indian Constitution has evolved over the years").

## Files

- **`amendments.json`** — 99 entries (Amendments 1–99). Each is `{amendment, url, summary}`. The `url` field points to the (now-stale) `indiacode.nic.in/coiweb/amend/amendN.htm` location; the `summary` is a one-paragraph description of what the amendment did. Useful as a metadata seed.

- **`data.json`** — 440 entries. Each is a `(tenure, year, date, amendment, article, status, type, party, year_range)` row, one per `(amendment, article)` pair, where `status ∈ {modified, inserted, insertion, deleted}`. This is a structured per-article amendment-touch index.

## Provenance

- Origin URL: <http://constitution-of-india.pykih.com/data/amendments.json> and `/data/data.json`
- Retrieved: 2026-05-08
- Coverage: Amendments 1–99 (the 100th was passed in 2021; the dataset hasn't been updated since the 2015 article)

## Role in this project

- Cross-validation source for `metadata/amendments.json`. Three-way agreement (pykih + IK + legislative.gov.in) on `(amendment N → articles touched)` lifts our confidence; disagreements get flagged for review.
- One-paragraph summaries are used as preliminary commit-message hints for Phase 2 amendment ingestion.

The dataset stops at 99, so the last 7 amendments (100–106) come from IK + legislative.gov.in alone.
