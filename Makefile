.PHONY: check test policy coverage registry scan eval lint sync agents-check

# Overridable for platforms without this interpreter name:
#   make check PYTHON=py
PYTHON ?= python3

PROSE_DOCS = AGENTS.md README.md CHANGELOG.md eval/README.md docs/problems.md docs/best-practices.md $(wildcard docs/classes/*.md) \
	docs/project-orientation.md docs/repository-orientation.md docs/template-drift.md $(wildcard docs/agent-policy/*.md)
# The self-scan skips scripts/time_checks (the rules hold the patterns they match) and tests/ (fixtures).
SCAN_PATHS = scripts/check_doc_policy.py scripts/check_ledger_coverage.py scripts/check_time_handling.py \
	scripts/validate_registry.py scripts/review_envelope.py scripts/review_report.py ci eval/run_eval.py

policy:
	$(PYTHON) scripts/check_doc_policy.py TIME.md
	$(PYTHON) scripts/check_doc_policy.py SYNC.md
	for doc in $(PROSE_DOCS); do $(PYTHON) scripts/check_doc_policy.py $$doc --prose-only || exit 1; done

coverage:
	$(PYTHON) scripts/check_ledger_coverage.py

registry:
	$(PYTHON) scripts/validate_registry.py

# The scanner is advisory and exits 0. This run proves it executes over the repository code.
scan:
	$(PYTHON) scripts/check_time_handling.py all $(SCAN_PATHS) > /dev/null

eval:
	$(PYTHON) eval/run_eval.py

# Policy copies come from AGENTS.md plus the supporting policy files.
sync:
	$(PYTHON) scripts/sync.py

agents-check:
	$(PYTHON) scripts/sync.py --check

# Needs the tools from requirements-dev.txt. make check stays standard-library only.
# The ruff steps follow the abuzucom/rough baseline. --ignore-noqa makes
# suppression comments ineffective. The warn tier reports and never fails.
RUFF_PATHS = scripts ci eval/run_eval.py tests

# Files imported byte-identical from abuzucom/agents. They follow that
# repository's style, so ruff and mypy skip exactly these paths. The agents
# checks cover them instead. docs/template-drift.md records the list.
AGENTS_IMPORTED = scripts/sync.py

comma := ,
empty :=
space := $(empty) $(empty)
AGENTS_IMPORTED_CSV = $(subst $(space),$(comma),$(strip $(AGENTS_IMPORTED)))
AGENTS_IMPORTED_RE = ^($(subst $(space),|,$(subst .,\.,$(strip $(AGENTS_IMPORTED)))))$$

lint:
	$(PYTHON) -m ruff check --ignore-noqa --extend-exclude '$(AGENTS_IMPORTED_CSV)' $(RUFF_PATHS)
	$(PYTHON) -m ruff format --check --extend-exclude '$(AGENTS_IMPORTED_CSV)' $(RUFF_PATHS)
	$(PYTHON) -m ruff check --config ruff.warn.toml --ignore-noqa --exit-zero --extend-exclude '$(AGENTS_IMPORTED_CSV)' $(RUFF_PATHS)
	$(PYTHON) -m mypy --exclude '$(AGENTS_IMPORTED_RE)'
	$(PYTHON) -m yamllint --strict .github .yamllint.yml

test:
	$(PYTHON) -m unittest discover -s tests

check: policy coverage registry scan eval agents-check test
