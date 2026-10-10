.PHONY: check test policy coverage registry scan eval lint

# Overridable for platforms without this interpreter name:
#   make check PYTHON=py
PYTHON ?= python3

PROSE_DOCS = AGENTS.md README.md CHANGELOG.md eval/README.md docs/problems.md docs/best-practices.md $(wildcard docs/classes/*.md)
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

# Needs the tools from requirements-dev.txt. make check stays standard-library only.
# The ruff steps follow the abuzucom/rough baseline. --ignore-noqa makes
# suppression comments ineffective. The warn tier reports and never fails.
RUFF_PATHS = scripts ci eval/run_eval.py tests

lint:
	$(PYTHON) -m ruff check --ignore-noqa $(RUFF_PATHS)
	$(PYTHON) -m ruff format --check $(RUFF_PATHS)
	$(PYTHON) -m ruff check --config ruff.warn.toml --ignore-noqa --exit-zero $(RUFF_PATHS)
	$(PYTHON) -m mypy
	$(PYTHON) -m yamllint --strict .github .yamllint.yml

test:
	$(PYTHON) -m unittest discover -s tests

check: policy coverage registry scan eval test
