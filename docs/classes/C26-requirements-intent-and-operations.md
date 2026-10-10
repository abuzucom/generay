# C26 Requirements, intent, and operations

(sources: PA-116, 134, 136; inbound from C3.6, C9.4, C15.1, C17.2, C23.2) Approved by the user.

Scope: whether time-sensitive requirements are complete, deliberate
date and timer misbehavior, and time-related monitoring. Each earlier
class escalates its own missing rules; C26 holds the general checklist.

- C26.1 Complete time-sensitive requirements.
  - Facts: a date and clock time leave most decisions open. "The offer
    expires 2026-11-01 01:30" in New York names a time that happens twice
    that night, at -04:00 and -05:00 (verified). A complete requirement
    states: governing zone and party, and calendar (C14.6, C6.1); anchor
    (C10.2); boundary, inclusive or exclusive, precision, what "midnight"
    or "end of day" means (for example close of business), and rounding
    (C3.5, C3.6, C24.6, C20.5); which event counts (C8.1); elapsed or
    calendar durations, business days and holiday calendar, month-end and
    Feb 29 policies (C7, C4); skipped and repeated local times and dates
    (C11.6, C6.4); recurrence rules (C7.2); clock authority, tolerated
    skew, and accuracy (C15, C17.3); display zone and labels (C14.1,
    C24); and change handling for rule changes, travel, and corrections
    (C10.2, C25.4).
  - In work products: tickets, specs, or contracts with "due 2026-10-10
    17:00" and nothing more. API fields documented only as "date-time".
    Tests written from the same incomplete spec, passing whatever the code
    assumes. Team decisions made by default and not recorded (C9.4).
  - Fix: use the checklist as a requirements template. Record each answer
    next to the implementing code and test it. When an answer is missing,
    escalate instead of inferring (the review follows the same rule).
  - Not a finding: requirements answering every applicable point or
    stating that a point does not apply.
  - Escalate: any time-sensitive requirement missing a governing zone,
    anchor, boundary rule, or duration semantics.
- C26.2 Deliberate date and timer misbehavior.
  - Facts: compatibility quirks are kept on purpose (Excel's 1900-02-29,
    C2.5; JS zero-based months and `getYear()`; Java legacy `Calendar`
    months), and "fixing" them breaks consumers. Time-triggered behavior
    is built in on purpose (trials, license time bombs, beta kill dates,
    certificate and token lifetimes). Malicious time triggers exist (logic
    bombs; Michelangelo on March 6 and CIH on April 26; insider
    time-triggered deletions). Timestamps are falsified on purpose
    (timestomping, MITRE ATT&CK T1070.006; backdated documents and stock
    options). Clocks and zones are misreported for privacy (Tor and
    Firefox report UTC, browsers coarsen timers) and fairness (smearing).
    Presentation can mislead (renewal deadlines in a vendor-favoring zone
    or format, one-sided rounding). (Deliberate timer interference is
    C18.6.)
  - In code: comparisons against hardcoded future dates (`if now >
    2027-01-01`), especially guarding destructive, disabling, or
    exfiltrating actions. Time-conditional branches in dependencies. Code
    setting file or record timestamps outside tooling meant to
    (`os.utime`, `touch -d` in application code). Editable audit or record
    timestamps. Compatibility quirks "fixed" without checking consumers.
  - Fix: require a documented owner and reason for every time-conditional
    behavior, and review hardcoded future dates as possible time bombs.
    Keep audit timestamps server-assigned and append-only (C8.1).
    Restrict timestamp-setting calls. Document intentional quirks and wrap
    them. Present deadlines in the user's zone with the zone named and a
    stated rounding rule.
  - Not a finding: documented, owned expirations that fail safely.
  - Escalate: undocumented date-triggered behavior that disables, deletes,
    or sends data, in first- or third-party code.
- C26.3 Time-related monitoring.
  - Facts: time failures usually leave services up: drifting or stepped
    clocks, stale tz data or leap-second lists, skipped or duplicated
    jobs, parse failures that look like quiet days, out-of-range client
    clocks, future-dated records, negative durations, out-of-order
    timestamps, and expiring certificates and tokens.
  - What to monitor: clock offset, sync status, and estimated error per
    host (Prometheus node_exporter `node_timex_offset_seconds`,
    `node_timex_sync_status`; C27); loss of sync and holdover time (C27.5); tz
    data version and age per layer, unapplied IANA releases, and
    leap-second list expiry (C10.3, C17.2); expected versus actual job
    runs, late runs, and duplicates via check-in monitoring and run IDs
    (C18.5); rates of parse failures, rejected or implausible or
    future-dated timestamps, negative durations, and monotonicity
    violations (C23.2, C15.2, C19); client skew distribution (C15.5);
    sync watermark lag (C19.4); certificate and token expiry dates; and
    synthetic checks around DST transitions, month-ends, and year-ends
    (C25.3).
  - In code and operations: health checks returning only HTTP 200. Cron
    jobs without run tracking. Parse errors swallowed or logged without
    metrics. No clock-offset or skew metrics.
  - Fix: add the metrics and alerts that apply, with owners and runbooks.
    Log in UTC with offsets so events correlate (C9.2).
  - Not a finding: documented time-health monitoring appropriate to risk.
  - Escalate: time-critical systems whose monitoring is outside the review
    unit.
- Proposed severity (for the user to decide), per check: CRITICAL for
  undocumented time-triggered destructive code (data destroyed, within
  the rule). HIGH for undocumented time-triggered exfiltrating code and
  editable audit timestamps (user decision: not CRITICAL exceptions).
  HIGH also when a legal, financial, safety, or
  contractual deadline is implemented from an incomplete requirement;
  timestamp-forging paths or misleading deadline presentation sit on core
  paths; or skipped or duplicated jobs, clock drift, or parse failures on
  a core path (billing, expiry, compliance) would go undetected. MEDIUM for
  other features, undocumented compatibility workarounds, and other
  monitoring gaps. LOW for internal tooling and test-only code.

Point ledger for C26:
- Inbound from C3.6: state what "end of day" means -> C26.1.
- Inbound from C9.4: record team time decisions -> C26.1.
- Inbound from C15.1: monitor clock offset -> C26.3.
- Inbound from C17.2: alert on leap-second list expiry -> C26.3.
- Inbound from C23.2: count parse failures -> C26.3.
- PA-116: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C26.2. Privacy misreporting -> C26.2 with C14.1.
  Deliberate timer facts -> C18.6 (already there via PA-117). Severity ->
  C26 severity.
- PA-134: all facts, checklist, work-product patterns, checks, fixes,
  not-a-finding, escalation -> C26.1. Severity -> C26 severity.
- PA-136: all facts, monitoring list, code and operations patterns,
  checks, fixes, not-a-finding, escalation -> C26.3. Severity -> C26
  severity.
