# C9 Host, environment, and stack zone handling

(sources: PA-8, 10, 90, 91, 92) Approved by the user.

Scope: zones and conversions that come from the machine, the deployment,
and the layers of the stack rather than from the code's own explicit
choices, and the belief that a stack or a single-site deployment needs no
deliberate time decisions. Zone rules and tz data are C10. DST behavior
and library gap defaults are C11. GMT versus UTC is C13. Which zone
governs a decision is C14. Scheduler behavior is C18. Database type
semantics are C22.

- C9.1 Code that reads the host zone.
  - Facts: developer laptops, on-premises and Windows servers, regional
    VM images, and end-user devices run in local zones. Containers are
    UTC only until `TZ` or `/etc/localtime` is set. CI runners often
    default to UTC, so tests pass there and fail, or pass wrongly,
    elsewhere. Calls that read the host zone (verified where marked):
    - Python: naive `datetime.now()`, `date.today()`,
      `datetime.fromtimestamp(ts)`, `time.mktime`; naive
      `datetime.utcnow().timestamp()` read as local (4 hours off on a New
      York host, verified); `astimezone()` with no argument (UTC 12:00
      becomes 21:00+09:00 on a Tokyo host, verified).
    - JS: `new Date(y, m, d)`, local getters, `toString()`;
      `"2026-07-01T09:00"` parses as local and `"2026-07-01"` as UTC
      (verified).
    - Java: `LocalDateTime.now()`, `LocalDate.now()`,
      `ZoneId.systemDefault()`, `TimeZone.getDefault()`,
      `SimpleDateFormat` without a zone.
    - Go: `time.Now()` carries `time.Local`; `time.Parse` without offset
      gives UTC, `ParseInLocation` the given zone (verified).
    - .NET: `DateTime.Now`, `DateTime.Today`, `ToLocalTime()`,
      `DateTime.Parse` giving `Local` or `Unspecified`.
    - SQL: `NOW()`, `CURRENT_DATE`, and `timestamptz` to `date` casts
      follow the session zone, which inherits the server's when unset.
    - Ops: cron entries, log timestamps without offset, shell `date`.
  - In code: any of these whose result is stored, compared, sent, or used
    for "today" or a business deadline. Zone set only by deployment
    config (`TZ` in Dockerfiles, manifests, systemd units). Database
    connections that never set the session zone. Tests that never pin or
    vary `TZ`.
  - Fix: read "now" in explicit UTC (Python `datetime.now(timezone.utc)`,
    Java `Instant.now()`, Go `time.Now().UTC()`, .NET
    `DateTimeOffset.UtcNow`, Luxon `DateTime.utc()`). Use the user's or
    business's named zone for local meaning, never the host's. Set the
    database session zone on every connection. Run tests under several
    `TZ` values: UTC, a negative offset, an offset beyond +12, and a
    non-whole-hour offset such as `Asia/Kathmandu`. `TZ=UTC` in
    deployment is defense in depth, not a replacement.
  - Not a finding: desktop or CLI tools required to show the user's own
    local time. Processes that set their zone explicitly and fail fast at
    startup if it differs, documented.
  - Escalate: host-local values stored or acted on when the deployment
    config that sets the zone is outside the review unit.
- C9.2 Production zone changes and zone-less stored data.
  - Facts: region migrations, new base images, provider or
    managed-service default changes, and ops edits change production
    zones. Active-active regions, DR sites, replicas, and blue/green
    fleets can differ at once. A host on a DST zone changes offset twice
    a year and repeats an hour in autumn.
  - In code: naive values, SQL `DATETIME`, or Postgres `timestamp`
    written in the host or session zone, so old and new rows mean
    different instants after a change. MySQL `TIMESTAMP` read through a
    changed session zone. Logs and audit trails in local time without
    offset. Cron in the host zone moving after the change. Mixed fleets
    writing one field in different zones. Idempotency keys, file names,
    or partitions from local dates colliding or splitting. No record of
    the zone in effect when old data was written.
  - Fix: store instants in UTC or with offsets (`timestamptz`, or UTC by
    documented convention). Log in UTC with an explicit offset in RFC
    3339 form. Configure schedulers with an explicit zone. Before a zone
    change, inventory zone-less data and plan a migration that records
    the original zone. Check zone settings in every region, replica, and
    fleet at deployment.
  - Not a finding: zone-less columns documented as UTC and written only
    by code that converts to UTC. Local-time storage that is intentional
    and carries the zone ID (C10).
  - Escalate: zone-less datasets whose original zone cannot be
    established.
- C9.3 Implicit conversions between stack layers.
  - Facts: databases (MySQL `TIMESTAMP` converts, `DATETIME` does not;
    Postgres `timestamptz` uses the session zone for offset-less input
    and output, `timestamp` does not convert, casts use the session
    zone). Drivers (JDBC `getTimestamp` applies the JVM zone; MySQL
    Connector/J `connectionTimeZone` and `preserveInstants` defaults
    changed across 8.0 releases). ORMs (Django `USE_TZ`, default on since
    5.0; Rails `config.time_zone` and `ActiveRecord.default_timezone`;
    Hibernate `hibernate.jdbc.time_zone`). Serializers (JS
    `JSON.stringify` writes UTC `Z` and drops the original offset,
    verified; Jackson `ADJUST_DATES_TO_CONTEXT_TIME_ZONE` on by default).
    Clients (HTML `valueAsDate` UTC midnight; mobile pickers in device
    zone). Tools (BI dashboards in the viewer's browser zone, logging
    frameworks in the host zone, cloud schedulers UTC-only or zoned).
  - In code: double conversion (offset applied twice). No conversion
    (each layer assumes another converted). Original offsets lost in
    serialization and needed later. Behavior changing after a driver,
    ORM, or framework upgrade. Tests only in UTC, where all of this is
    invisible.
  - Fix: map every hop's conversion and configure each explicitly
    (session zone, driver, ORM, serializer). Use offset- or zone-carrying
    types end to end where the original offset matters (C8.4). Write
    round-trip tests under a non-UTC host zone across DST dates, pinned
    to the configured versions.
  - Not a finding: documented, explicitly configured conversion at each
    hop with non-UTC round-trip tests.
  - Escalate: layers outside the review unit (vendor service, BI tool,
    partner API) whose conversion behavior cannot be established.
- C9.4 Time decisions left to defaults or skipped.
  - Facts: a single zone or internal deployment still has DST (23- and
    25-hour days, skipped and repeated hours, ambiguous zone-less
    timestamps), government rule changes, and every non-zone pitfall
    (unit lengths, leap days, clock error, precision). "Internal" grows
    (offices, remote staff, acquisitions). Infrastructure and SaaS
    integrations run or exchange data in UTC. Data leaves (exports to
    partners, regulators, auditors; restored backups). Staff travel.
    Records outlive their context. Trusted libraries still leave
    decisions to the team: elapsed versus calendar meaning (C7.1),
    governing zone (C14), month-end and Feb 29 policy (C7.2), date versus
    instant (C8), storage of future local events (C10), day, week,
    weekend, and holiday definitions (C3, C4), gap and overlap policy
    (C11), and layer configuration (C9.3). Defaults are often wrong for
    production: host zone, lenient parsing, locale formatting. Stacks
    offer both correct and incorrect types. Libraries can be misused
    (BP-1).
  - In code: naive local datetimes everywhere with no offsets in storage
    or logs. Business zone implied by the host. Jobs in host local time
    with no DST handling. Comments or decisions such as "timezones don't
    matter here" or "the framework handles timezones". Defaults relied on
    for parsing, formatting, zone, and arithmetic. No tests at DST
    transitions or in non-UTC zones.
  - Fix: store and log instants in UTC or with offsets even for
    single-site systems. Configure the business zone as an IANA ID.
    Record the team's time decisions (list above) next to the code, and
    test them. Treat zone handling as cheap insurance: retrofitting cost
    grows with every zone-less record.
  - Not a finding: throwaway scripts that persist no times and drive no
    decisions. Library defaults the team has reviewed, documented, and
    tested as intended policy.
  - Escalate: features whose time semantics are not stated anywhere.
    Systems storing zone-less times whose growth, integrations, or
    retention are not stated.
- Proposed severity (for the user to decide), per check: HIGH when stored
  values, billing, scheduling, expiry, payroll, or audit records depend
  on the host zone, become ambiguous or shift after a zone change, are
  double- or un-converted, or rest on an unexamined default, on a core
  path, or when scheduled jobs with financial or legal effect move or
  break at DST. MEDIUM for logs, reports, dashboards, display, other
  zone-less storage, and missing documentation and tests. LOW for
  test-only code, noting that tests passing only under UTC hide
  production defects.

Point ledger for C9:
- PA-8: host variety, containers, zone changes, database zone settings,
  CI default, call list, what to check, UTC "now" fix, named-zone fix,
  session-zone fix, multi-TZ tests, `TZ=UTC` defense, not-a-findings,
  escalation -> C9.1. GMT versus UTC and `Europe/London` -> C13
  (inbound). Severity -> C9 severity.
- PA-10: infrastructure changes, multi-region, DST host offsets, all
  code and data patterns, checks, storage fix, logging fix, scheduler
  fix, migration inventory, fleet checks, not-a-findings, escalation ->
  C9.2. Severity -> C9 severity.
- PA-90: all layer facts, double and missing conversion, lost offsets,
  upgrade changes, UTC-only tests, mapping fix, types fix, round-trip
  tests, not-a-finding, escalation -> C9.3. Python `astimezone()` and
  JS getters -> C9.1. Severity -> C9 severity.
- PA-91: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C9.4 (storage and logging fix also C9.2, DST schedules
  C11 and C18 by reference). Severity -> C9 severity.
- PA-92: decisions left to the team, required configuration, wrong
  defaults, correct and incorrect types, misuse, "framework handles it",
  policy-record fix, layer configuration, tests, not-a-finding,
  semantics escalation -> C9.4. Library gap and overlap defaults (Python
  fold, JS shift, Java shift) -> C11 (inbound). tz data maintenance ->
  C10 (already there via PA-35). Severity -> C9 severity.
