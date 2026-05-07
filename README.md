# Constitution of India

A Git-native, diffable representation of the Constitution of India. Every amendment is a discrete commit; `git log` reconstructs constitutional history from 26 January 1950 to the present.

**Status:** Phase 0 — repository scaffolded; baseline ingest not yet committed. See [`docs/prd-constitution-v1.md`](docs/prd-constitution-v1.md) for the v1 spec and [`docs/handoff.md`](docs/handoff.md) for the handoff notes.

## What this is

- One file per Article (`articles/article-NNN.md`), one per Schedule (`schedules/schedule-NN.md`).
- Each amendment landed as one logical commit, in chronological order.
- HEAD verified against the current consolidated text published by the Lok Sabha / India Code.
- An intra-Constitution cross-reference index (`metadata/cross-references.json`).
- Reproducible pipeline (`pipeline/`) — Python, PDF extraction, LLM-assisted parsing, lawyer-reviewed.

## What this is not

This is a **best-effort** open artifact for researchers, journalists, lawyers, and informed citizens. It is **not legal advice**, **not authoritative**, and **not a substitute** for the official text published by the Government of India. For legal use, refer to [indiacode.nic.in](https://www.indiacode.nic.in) and the Gazette of India.

## Inspiration and prior art

Inspired by [`nickvido/us-code`](https://github.com/nickvido/us-code), adapted for India's source landscape (PDFs rather than versioned XML). See [`docs/research-notes.md`](docs/research-notes.md).

## Contributing

Corrections, typo fixes, and source-cited improvements are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licensing

- Pipeline code: MIT (see [`LICENSE`](LICENSE)).
- Constitutional text: see [`LICENSE-TEXT`](LICENSE-TEXT) (pending; the text is reproduced from public Government of India sources).
