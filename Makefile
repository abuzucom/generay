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
	tests/test_worker_timeout_defaults.py \
	scripts/check_gate_adoption.py \
	scripts/check_gate_pr_integrity.py \
	scripts/check_hook_launchers.py \
	scripts/complete_gate_adoption.py \
	tests/gate_corpus.py \
	tests/read_only_branch_support.py \
	tests/retrying_temp_directory.py \
	tests/test_advisory_workflow_wiring.py \
	tests/test_block_destructive_bash.py \
	tests/test_block_destructive_cmd.py \
	tests/test_block_destructive_powershell.py \
	tests/test_block_infrastructure_access.py \
	tests/test_branch_gate_edge_paths.py \
	tests/test_branch_review_regressions.py \
	tests/test_branch_validation_boundaries.py \
	tests/test_branch_validation_bypasses.py \
	tests/test_branch_validation_contexts.py \
	tests/test_branch_validation_execution.py \
	tests/test_branch_validation_failures.py \
	tests/test_branch_write_destinations.py \
	tests/test_check_agent_prose_gate.py \
	tests/test_check_compliance_tree.py \
	tests/test_check_conflict_markers.py \
	tests/test_check_gate_adoption.py \
	tests/test_check_gate_pr_integrity.py \
	tests/test_check_hook_coverage.py \
	tests/test_check_hook_launchers.py \
	tests/test_ci_branch_fixtures.py \
	tests/test_cloudflare_pages_path_security.py \
	tests/test_cloudflare_pages_policy.py \
	tests/test_command_execution_gate.py \
	tests/test_compaction_directive.py \
	tests/test_complete_gate_adoption.py \
	tests/test_dependabot_branch_policy.py \
	tests/test_enforce_branch_name.py \
	tests/test_enforce_gate_adoption.py \
	tests/test_enforce_git_identity.py \
	tests/test_enforce_git_identity_wording.py \
	tests/test_external_pr_refs.py \
	tests/test_external_repo_gate.py \
	tests/test_fresh_gate_entrypoints.py \
	tests/test_gate_adoption_transaction.py \
	tests/test_gate_bypass_regressions.py \
	tests/test_gate_hardening.py \
	tests/test_gate_parity.py \
	tests/test_gate_pr_integrity_timeline.py \
	tests/test_gh_label_and_method_denial.py \
	tests/test_gh_option_value_forms.py \
	tests/test_github_command_denylist.py \
	tests/test_hook_payload_and_identity.py \
	tests/test_identity_checker_hardening.py \
	tests/test_immutable_auth_wiring.py \
	tests/test_immutable_compliance.py \
	tests/test_integrity_attribution_scope.py \
	tests/test_logic_consistency.py \
	tests/test_master_branch_conversion.py \
	tests/test_new_runtime_structure.py \
	tests/test_npm_workflow_gate.py \
	tests/test_parallel_test_runner.py \
	tests/test_pipe_gate_list_operators.py \
	tests/test_plan_write_roots.py \
	tests/test_platform_policy.py \
	tests/test_platform_policy_coverage.py \
	tests/test_policy_size_wiring.py \
	tests/test_primary_branch_override.py \
	tests/test_primary_branch_read_only.py \
	tests/test_reinject_agents_policy.py \
	tests/test_reinject_policy_supporting.py \
	tests/test_require_consent.py \
	tests/test_sync_shared.py \
	tests/test_temp_root_isolation.py \
	tests/test_trusted_gh.py \
	tests/test_trusted_gh_failure_classification.py \
	tests/test_trusted_gh_temp_isolation.py \
	tests/test_trusted_git_hardening.py \
	tests/test_trusted_git_proxy.py \
	tests/test_windows_drive_paths.py

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
