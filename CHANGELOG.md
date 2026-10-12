# Changelog

All changes follow Semantic Versioning. Versions below 1.0.0 are unstable.
Each version heading carries its UTC release date. Each date has one entry.
A same-day change renames that day's heading to the new version and merges
its items into the entry.

## [0.4.0] (2026-10-12)

### Added

- Add the agents hooks and the Claude Code, Codex, Gemini, and Antigravity
  client configurations through one gate adoption transaction.
- Add the gate scripts, `shared-files.json`, `hook-coverage-baseline.json`,
  the hook trace tool, and the remaining agents tests.
- Add the `sync-check`, `agents-compliance`, `agents-md-compliance`,
  `immutable-conflict-check`, and `gate-integrity` workflows.

## [0.3.0] (2026-10-10)

This entry merges the same-day releases 0.1.0, 0.1.1, and 0.2.0.

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
- Add the portable agents checkers, the prose bundle, the trusted Git and GitHub
  wrappers, the shard test runner, and the matching tests.
- Add `requirements-checkers.txt`, `.pre-commit-config.yaml`, and
  `plan/HANDOFF.md.example`.
- Add the `agents-test`, `agents-lint`, `identity`, and `changelog` targets.
  `make check` runs `changelog`. `make lint` runs `agents-lint`.
- Add `TIME.md` (C1 to C26) and `SYNC.md` (C27) review prompts.
- Add class drafts, problem notes, best practices, ledger, and library registry.
- Add deterministic scanners for Python, JavaScript and TypeScript, JVM, Go, .NET,
  NTP configuration, and infrastructure files.
- Add doc policy, ledger coverage, and registry validation checks.
- Add review envelope builder, model client, and report validator adapted from euler.
- Add golden eval corpus with Contract mode.

### Changed

- ruff and mypy skip the files imported from `abuzucom/agents`.
  `docs/template-drift.md` lists the imported files.

- The CI `checks` job installs `requirements-checkers.txt` before `make check`.

### Security

- Stop the review workflow from checking out `inputs.base_sha`. CodeQL flagged the step as
  checkout of untrusted code in a privileged context.
