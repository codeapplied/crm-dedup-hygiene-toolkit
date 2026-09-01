# CRM Dedup/Hygiene Toolkit

[![Tests](https://github.com/codeapplied/crm-dedup-hygiene-toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/codeapplied/crm-dedup-hygiene-toolkit/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Finds and safely merges duplicate organizations and contacts in a CRM, with a
full audit trail — rebuilt as a generalized, open-source system.

Originally built as an internal work tool; this repo is a from-scratch rebuild
using generic, sanitized logic only. No employer-specific data, workflows, or
branding.

## Status

Core pipeline is built and tested: duplicate discovery, score-based primary
selection, and merge execution (dry-run by default, `--execute` to actually
merge) all work end-to-end against both the bundled sandbox demo and a real
Pipedrive backend. See [open issues](https://github.com/codeapplied/crm-dedup-hygiene-toolkit/issues)
for what's next.

## Architecture

Fetch every record of an entity type (organizations by normalized domain,
contacts by email) → group records sharing that key → for each group of 2+,
snapshot every related record (contacts, deals, notes, activities) on every
member → score each member by a weighted combination of linked-record counts
→ the highest-scoring member becomes "primary" → dry run prints the exact
merge plan; only an explicit `--execute` performs the merge → call the CRM's
native merge endpoint, then post one audit note on the primary summarizing
exactly what was absorbed. Every run is logged to `MergeLog`, which the ops
CLI reads for history.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full data-flow
diagram and design rationale.

## Setup

```
uv venv
uv pip install -e .
cp config/.env.example .env
cp config/rules.example.yaml config/rules.yaml
crmdedup init
```

Leave `.env`'s Pipedrive fields blank to run against the bundled zero-network
sandbox demo — no credentials needed to try it.

## CLI

- `crmdedup init` — create the database
- `crmdedup status` — recent merge runs
- `crmdedup rules` — show the loaded scoring weights and known-false-positive skip list
- `crmdedup discover` — find duplicate groups (dry run — plans only, writes nothing to the CRM)
- `crmdedup discover --execute` — actually perform each planned merge

## Development

```
uv pip install -e ".[dev]"
pytest -v
```

## License

MIT — see [LICENSE](LICENSE).
