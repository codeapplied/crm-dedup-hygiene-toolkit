# CRM Dedup/Hygiene Toolkit

Finds and safely merges duplicate organizations and contacts in a CRM, with a
full audit trail — rebuilt as a generalized, open-source system.

Originally built as an internal work tool; this repo is a from-scratch rebuild
using generic, sanitized logic only. No employer-specific data, workflows, or
branding.

## Status

🚧 Early development. DB models, config loading, and CLI skeleton are in
place. Duplicate discovery and merge execution are not built yet — see
[open issues](https://github.com/codeapplied/crm-dedup-hygiene-toolkit/issues).

## Architecture

Fetch every record of an entity type (organizations by normalized domain,
contacts by email) → group records sharing that key → for each group of 2+,
snapshot every related record (contacts, deals, notes, activities) on every
member → score each member by a weighted combination of linked-record counts
→ the highest-scoring member becomes "primary" → dry run prints the exact
merge plan; only an explicit `--execute` performs the merge → call the CRM's
native merge endpoint, then post one audit note on the primary summarizing
exactly what was absorbed. Every stage is logged to `MergeLog`, which the ops
CLI reads for history.

## Setup

```
uv venv
uv pip install -e .
cp config/.env.example .env
cp config/rules.example.yaml config/rules.yaml
crmdedup init
```

## CLI

- `crmdedup init` — create the database
- `crmdedup status` — recent merge runs
- `crmdedup rules` — show the loaded scoring weights and known-false-positive skip list
- `crmdedup discover` — find duplicate groups (not yet implemented)

## License

MIT — see [LICENSE](LICENSE).
