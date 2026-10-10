# Template drift

This file records generay differences from `abuzucom/agents`. The template
`DRIFT.md` defines the categories.

## Adopted at

Template commit `f255dca66dded4c62e736bd189cfaaac978b7b2b`.

## Imported files

These files match the template byte for byte. ruff and mypy skip them through
`AGENTS_IMPORTED` in the `Makefile`.

- `scripts/sync.py`

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
  template targets use the `agents-` prefix or keep their template names when
  no generay target shares the name.
- `CHANGELOG.md` keeps the generay preamble. The headings follow the template
  format.

## Local rules

- L1 keeps the generay CI-check rule. Canonical Rule 18 covers gates instead.
- L2 keeps the generay workflow rule. Canonical Rule 22 covers hooks and the
  banned-model list instead.
- L3 keeps the `ci/` branch prefix. The template branch checker omits it.

## Not adopted

- `docs/agent-policy/source-orientation.md` belongs to the template only.

## Template findings

- `docs/agent-policy/adoption.md` carries a "Source repository orientation"
  section without `source-only` markers. Adoptable output therefore keeps it.
