# Changelog

All changes follow Semantic Versioning. Versions below 1.0.0 are unstable.
Each version heading carries its UTC release date. Each date has one entry.
A same-day change renames that day's heading to the new version and merges
its items into the entry.

## [0.2.0] (2026-10-10)

This entry merges the same-day releases 0.1.0 and 0.1.1.

### Added

- Adopt the canonical `AGENTS.md` from `abuzucom/agents` at commit
  `f255dca66dded4c62e736bd189cfaaac978b7b2b`.
- Add `docs/agent-policy/`, `docs/project-orientation.md`, and
  `docs/repository-orientation.md`. The generay local rules, enforcement list,
  and orientation move to the orientation files.
- Add `scripts/sync.py` and the eight synchronized policy copies.
- Add `.gitattributes`, `.editorconfig`, and `.claudeignore`.
- Add the `make sync` and `make agents-check` targets. `make check` runs
  `agents-check`.
- Add `docs/template-drift.md`.
- Add `TIME.md` (C1 to C26) and `SYNC.md` (C27) review prompts.
- Add class drafts, problem notes, best practices, ledger, and library registry.
- Add deterministic scanners for Python, JavaScript and TypeScript, JVM, Go, .NET,
  NTP configuration, and infrastructure files.
- Add doc policy, ledger coverage, and registry validation checks.
- Add review envelope builder, model client, and report validator adapted from euler.
- Add golden eval corpus with Contract mode.

### Changed

- ruff and mypy skip the files imported from `abuzucom/agents`.
  `docs/template-drift.md` lists them.

### Security

- Stop the review workflow from checking out `inputs.base_sha`. CodeQL flagged the step as
  checkout of untrusted code in a privileged context.
