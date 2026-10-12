# Template drift

This file records generay differences from `abuzucom/agents`. The template
`DRIFT.md` defines the categories.

## Adopted at

Template commit `f255dca66dded4c62e736bd189cfaaac978b7b2b`.

## Imported files

`AGENTS_IMPORTED` in the `Makefile` lists every imported Python file under
`scripts/` and `tests/`. Each file matches the template byte for byte. ruff
and mypy skip exactly that list. `make agents-test` and `make test` run the
imported tests.

These data and configuration files match the template byte for byte:

- `scripts/banned_models.txt`
- `scripts/branch_name_bans.txt`
- `scripts/prose_bans.txt`
- `.pre-commit-config.yaml`
- `plan/HANDOFF.md.example`

These policy files match the template byte for byte:

- `AGENTS.md`
- `docs/agent-policy/adoption.md`
- `docs/agent-policy/clients.md`
- `docs/agent-policy/enforcement.md`
- `docs/agent-policy/github.md`
- `docs/agent-policy/security.md`
- `.gitattributes`
- `.editorconfig`
- `.claudeignore`

`make sync` generates the eight policy copies.

## Expected to differ

- `docs/project-orientation.md` holds generay content. The template caps the
  assembled policy at 64 KiB. The canonical policy leaves 269 bytes for this
  file. The file therefore names the local rules and links to
  `docs/repository-orientation.md`.
- `docs/repository-orientation.md` holds the full local rules, the enforcement
  list, and the generay orientation. The policy copies omit it.
- `Makefile` keeps the generay `check`, `test`, and `lint` targets. The
  template targets use the `agents-` prefix or keep the template name when
  no generay target shares the name.
- `CHANGELOG.md` keeps the generay preamble. The headings follow the template
  format.

- `requirements-checkers.txt` pins the template version of PyYAML with the
  hashes from `requirements-dev.txt`. The template file carries no hashes.
- The agents workflows keep the template text. The imported wiring tests read
  that text literally. `.yamllint.yml` ignores these five workflows, because
  the template formatting fails the generay `yamllint --strict` check. The
  active human approved this narrowing of the yamllint scope.
- `sync-check.yml` names the generay prose files instead of the template
  prose files. It omits the AgentLint step.
- `scripts/check_agent_prose_gate.py` lists the same generay prose files in
  `TARGET_FILES`. The template list names files that generay lacks.
- `README.md` carries a Handoffs section. The imported wiring tests require
  the handoff wording in the README.

## Gate set

`complete_gate_adoption.py` installed the hooks and the four client
configurations in one transaction from `.gate-staging/agents-f255dca`. The
hooks, `.claude/settings.json`, `.codex/`, `.gemini/settings.json`,
`.agents/hooks.json`, `hook-coverage-baseline.json`, and
`tools/hook-trace/sitecustomize.py` match the template byte for byte.
`sync.py --check-shared` verifies the 28 shared files.

## True drift

The active human approved each test edit below under Rules 3 and 22.

- `tests/test_block_destructive_bash.py`,
  `tests/test_block_destructive_powershell.py`, and `tests/test_gate_parity.py`
  run broad reads of `.` in an empty temporary directory. The gate denies a
  broad read over a tree with protected infrastructure files. The generay eval
  corpus holds Terraform fixtures under `eval/cases/c27-*`. The template tests
  read the repository root and therefore fail here. `shared-files.json`
  records the new hashes of the two shared test files.
- `tests/test_immutable_compliance.py` names its token-shaped probe
  `DETECTOR_PROBE_VALUE`. CodeQL reads a `SECRET` identifier as sensitive
  data and flagged each fixture write. The probe keeps its template value.

## Local rules

- L1 keeps the generay CI-check rule. Canonical Rule 18 covers gates instead.
- L2 keeps the generay workflow rule. Canonical Rule 22 covers hooks and the
  banned-model list instead.
- L3 keeps the `ci/` branch prefix. The template branch checker omits it.
  `.pre-commit-config.yaml` and the hooks run the checker with the template
  prefixes.

## Not adopted

- `docs/agent-policy/source-orientation.md` belongs to the template only.
- `security-review-pr.yml` and the template `ci/` files. generay keeps its own
  `ci/` review machinery under the same file names.
- `tests/test_security_review_wiring.py` covers only `security-review-pr.yml`.
- The AgentLint action, a third-party dependency.

## Template findings

- `trusted_git` and `trusted_gh` tests fail with "no safe external directory"
  in a root container. The same failure occurs in the template repository.

- `docs/agent-policy/adoption.md` carries a "Source repository orientation"
  section without `source-only` markers. Adoptable output therefore keeps it.
