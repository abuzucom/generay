# Changelog

All changes follow Semantic Versioning. Versions below 1.0.0 are unstable.

## 0.1.1

- Stop the review workflow from checking out `inputs.base_sha`. CodeQL flagged the step as
  checkout of untrusted code in a privileged context.

## 0.1.0

- Add `TIME.md` (C1 to C26) and `SYNC.md` (C27) review prompts.
- Add class drafts, problem notes, best practices, ledger, and library registry.
- Add deterministic scanners for Python, JavaScript and TypeScript, JVM, Go, .NET,
  NTP configuration, and infrastructure files.
- Add doc policy, ledger coverage, and registry validation checks.
- Add review envelope builder, model client, and report validator adapted from euler.
- Add golden eval corpus with Contract mode.
