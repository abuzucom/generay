.PHONY: check test policy coverage registry scan eval lint sync agents-check agents-test agents-lint identity changelog

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

changelog:
	$(PYTHON) scripts/check_changelog.py

identity:
	$(PYTHON) scripts/check_git_identity.py --advise

# Runs every test through the agents shard runner. make test runs the same
# suites through unittest discovery.
agents-test:
	$(PYTHON) scripts/run_tests.py

# The agents prose checks. Spelling, English, and hedging findings stay advisory.
AGENTS_PROSE = AGENTS.md README.md CHANGELOG.md docs/project-orientation.md docs/repository-orientation.md \
	docs/template-drift.md plan/HANDOFF.md.example

agents-lint:
	$(PYTHON) scripts/lint_style.py
	$(PYTHON) scripts/check_ascii.py $(AGENTS_PROSE)
	$(PYTHON) scripts/check_us_spelling.py $(AGENTS_PROSE)
	$(PYTHON) scripts/check_english_only.py $(AGENTS_PROSE)
	$(PYTHON) scripts/check_hedging.py $(AGENTS_PROSE)
	$(PYTHON) scripts/check_conflict_markers.py

# Needs the tools from requirements-dev.txt. make check stays standard-library only.
# The ruff steps follow the abuzucom/rough baseline. --ignore-noqa makes
# suppression comments ineffective. The warn tier reports and never fails.
RUFF_PATHS = scripts ci eval/run_eval.py tests

# Files imported byte-identical from abuzucom/agents. They follow that
# repository's style, so ruff and mypy skip exactly these paths. The agents
# checks cover them instead. docs/template-drift.md records the list.
AGENTS_IMPORTED = \
	scripts/check_action_pins.py \
	scripts/check_agent_prose_gate.py \
	scripts/check_ascii.py \
	scripts/check_banned_agents.py \
	scripts/check_branch_name.py \
	scripts/check_changelog.py \
	scripts/check_commit_attribution.py \
	scripts/check_commit_message.py \
	scripts/check_compliance_tree.py \
	scripts/check_conflict_markers.py \
	scripts/check_dockerfile_root.py \
	scripts/check_english_only.py \
	scripts/check_external_pr_refs.py \
	scripts/check_git_identity.py \
	scripts/check_hedging.py \
	scripts/check_hook_coverage.py \
	scripts/check_persist_credentials.py \
	scripts/check_policy_size.py \
	scripts/check_pr_review_response.py \
	scripts/check_pull_request_message.py \
	scripts/check_secrets_heuristic.py \
	scripts/check_test_first.py \
	scripts/check_us_spelling.py \
	scripts/check_weak_hashing.py \
	scripts/handoff_policy.py \
	scripts/lint_style.py \
	scripts/prose_policy.py \
	scripts/read_git_state.py \
	scripts/run_tests.py \
	scripts/sync.py \
	scripts/trusted_bot_identities.py \
	scripts/trusted_gh.py \
	scripts/trusted_git.py \
	tests/json_line_worker.py \
	tests/json_line_worker_child.py \
	tests/persistent_main_worker.py \
	tests/test_check_action_pins.py \
	tests/test_check_ascii.py \
	tests/test_check_changelog.py \
	tests/test_check_changelog_daily_entries.py \
	tests/test_check_commit_attribution.py \
	tests/test_check_commit_message.py \
	tests/test_check_git_identity_advisory.py \
	tests/test_check_pr_review_response.py \
	tests/test_check_test_first.py \
	tests/test_hook_coverage_runner.py \
	tests/test_model_disclosure_attribution.py \
	tests/test_persistent_main_worker.py \
	tests/test_policy_distribution.py \
	tests/test_policy_size.py \
	tests/test_prose_metadata.py \
	tests/test_prose_policy.py \
	tests/test_security_checkers.py \
	tests/test_shard_priority.py \
	tests/test_sync_security.py \
	tests/test_trusted_bot_identities.py \
	tests/test_trusted_git_state.py \
	tests/test_worker_timeout_defaults.py

comma := ,
empty :=
space := $(empty) $(empty)
AGENTS_IMPORTED_CSV = $(subst $(space),$(comma),$(strip $(AGENTS_IMPORTED)))
AGENTS_IMPORTED_RE = ^($(subst $(space),|,$(subst .,\.,$(strip $(AGENTS_IMPORTED)))))$$

lint: agents-lint
	$(PYTHON) -m ruff check --ignore-noqa --extend-exclude '$(AGENTS_IMPORTED_CSV)' $(RUFF_PATHS)
	$(PYTHON) -m ruff format --check --extend-exclude '$(AGENTS_IMPORTED_CSV)' $(RUFF_PATHS)
	$(PYTHON) -m ruff check --config ruff.warn.toml --ignore-noqa --exit-zero --extend-exclude '$(AGENTS_IMPORTED_CSV)' $(RUFF_PATHS)
	$(PYTHON) -m mypy --exclude '$(AGENTS_IMPORTED_RE)'
	$(PYTHON) -m yamllint --strict .github .yamllint.yml

test:
	$(PYTHON) -m unittest discover -s tests

check: policy coverage registry scan eval agents-check changelog test
