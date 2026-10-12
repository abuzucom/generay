# Repository orientation

This file holds generay facts and local rules. `docs/project-orientation.md`
names the local rules in every policy copy and links here. `AGENTS.md`
controls when this file conflicts with it.

## Local rules

### L1. Keep checks whole

Never remove, narrow, move, disable, bypass, weaken, or misreport a check that
this repository's CI runs. Denials, failures, and blocks are policy outcomes.
Report each failure. Fix the cause.

### L2. Protect workflow files

Never modify `.github/workflows/*` without fresh active-human consent. On any
edit need, stop, enter plan mode, and obtain affirmative approval. Never work
around absent consent.

### L3. Branch prefixes

| Prefix | Use |
|---|---|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `chore/` | Maintenance, dependencies, and build changes |
| `docs/` | Documentation only |
| `test/` | Adding or refactoring tests |
| `ci/` | CI configuration |

## Enforcement in this repository

The following checks exist:
- `.github/workflows/ci.yml` runs `make check` on every pull request.
- `.github/workflows/ci.yml` runs `make lint` on every pull request. ruff and
  mypy cover `scripts/`, `ci/`, and `eval/run_eval.py`. ruff also covers
  `tests/`. yamllint covers `.github/`. Files imported from `abuzucom/agents`
  sit outside ruff and mypy. `docs/template-drift.md` lists the files.
- The ruff block tier runs with `--ignore-noqa`. Suppression comments have no
  effect on it.
- `make check` runs `scripts/check_doc_policy.py` on `TIME.md` and `SYNC.md`
  for structure, ASCII, LF line endings, prose dashes, width, and the 32 KiB
  limit. The same script checks `AGENTS.md`, this file, and the prose
  documents in prose-only mode.
- `make check` runs `scripts/check_ledger_coverage.py`. It checks that every
  problem and best practice is in the ledger, every ledger check is drafted,
  and `TIME.md` plus `SYNC.md` list every check once with the ledger method.
- `make check` runs `scripts/validate_registry.py` on `data/libraries.json`.
- `make check` runs the eval structure check. It compares scanner output with
  `expected_prescan` for every case.
- `make check` runs `scripts/sync.py --check`. It fails when a policy copy
  differs from `AGENTS.md` plus the supporting policy files.
- `make check` runs `scripts/check_changelog.py` on `CHANGELOG.md`.
- `make test` runs the imported agents tests with the generay tests. The CI
  `checks` job installs `requirements-checkers.txt` first.
- `make lint` runs `make agents-lint`. `lint_style.py`, `check_ascii.py`, and
  `check_conflict_markers.py` block. The spelling, English, and hedging
  checkers only warn.
- `.pre-commit-config.yaml` registers the agents checkers for contributors
  who install pre-commit. CI does not run pre-commit.
- `sync-check.yml` runs the agents test suite on Windows and macOS, the
  pull request authorship checks, the shared-file manifest check, the gate
  adoption check, the hook coverage check, and the agents prose checks.
- `agents-md-compliance.yml` runs `agents-compliance.yml` on pushes to `main`.
- `immutable-conflict-check.yml` scans pull requests to `main` with the
  trusted base checker.
- `gate-integrity.yml` requires the `gate-change-approved` label from a person
  for protected gate changes.
- The hooks in `hooks/` gate agent tool calls for Claude Code, Codex, Gemini,
  and Antigravity. `docs/agent-policy/enforcement.md` lists the coverage limits.

## Commands

- `make check` runs every policy check, the coverage check, the registry
  check, the scanner smoke run, the eval structure check, the policy copy
  check, and the unit tests.
- `make test` runs the unit tests only.
- `make lint` runs ruff, mypy, and yamllint. The tools come from
  `requirements-dev.txt`.
- `make sync` regenerates the policy copies from `AGENTS.md`.
- `make agents-test` runs every test through `scripts/run_tests.py`.
- `make agents-lint` runs the agents prose and style checks.
- `make identity` reports the Git identity without changes.
- `make changelog` checks `CHANGELOG.md`.

## Architecture

- `TIME.md` and `SYNC.md` define the review contract. Model reviewers load both
  as the system prompt.
- `docs/` holds the class drafts, problem notes, and best practices.
- `docs/agent-policy/` holds supporting agent policy from `abuzucom/agents`.
- `data/` holds the ledger and the favored-library registry.
- `scripts/` holds the policy checkers and the deterministic time scanners in
  `scripts/time_checks/`.
- `eval/` holds the golden corpus and its runner.
- `ci/` holds the review envelope builder, the model adapter, and the report
  validator.
- `.github/workflows/` holds repository CI and the PR time review.

## Do not touch

- `eval/cases/*/expected.json` without a matching `TIME.md`, `SYNC.md`, or
  scanner change.
- `CLAUDE.md`, `GEMINI.md`, `CONVENTIONS.md`, `.cursorrules`, `.clinerules`,
  `.windsurfrules`, `.copilot-instructions`, and
  `.github/copilot-instructions.md`. `make sync` generates the copies.
- Files imported from `abuzucom/agents` without a drift record in
  `docs/template-drift.md`.

## Read before touching

- `eval/README.md` before any change to `ci/` or the review workflows.
- `docs/classes/` before any change to a check in `TIME.md` or `SYNC.md`.
- `docs/template-drift.md` before any change to an imported file.

## Policy changes

Any `TIME.md` or `SYNC.md` change to a verdict, a severity, or a check ships
with a new or updated `eval/cases/` case in the same change. A new problem
starts at the next free PA number. It needs a note in `docs/problems.md`, a
class draft entry, a prompt entry, and a ledger entry.
