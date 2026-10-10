# C8 Meaning of a time value

(sources: PA-31, 96, 125, 127, 131; inbound from C7.5) Approved by the user.

Scope: what a stored or exchanged time value means: which event it
records, whether it is an instant, a local value, a date, or a time,
and what its offset does and does not say. Which zone governs a decision
is C14. Zone rule changes for future values are C10. Database type
semantics are C22. Wire format variants are C23.

- C8.1 Which event a timestamp records.
  - Facts: a timestamp often records something other than the event:
    receive, queue, process, index, flush, or commit time. Log shippers
    stamp ingest time unless event time is parsed. Kafka topics store
    producer time (`CreateTime`) or broker append time
    (`LogAppendTime`) by configuration. `DEFAULT now()` stamps insert
    time, so imports and backfills all get the import time, and Postgres
    `now()` is transaction start. `updated_at` triggers fire on
    maintenance writes. File modification times change on copy,
    extraction, restore, and git checkout. EXIF dates come from the
    camera clock, usually local with no zone. Email `Date` headers are set
    by the sender and can be forged. Offline events are stamped at sync.
    Batch jobs stamp the job start. Records are entered after the
    real-world event. Effective time differs from recorded time
    (bitemporal data in payroll, insurance, accounting). Users and
    attackers falsify values.
  - In code: analytics, SLAs, or ordering on ingestion or processing
    time. Multi-source events ordered by receive time. Legal, audit, or
    billing decisions on client-supplied or editable timestamps. Change
    detection on `updated_at`. Build or backup correctness by
    modification time. EXIF or email `Date` trusted as fact. One field
    serving as both event and record time. Pipelines processing by
    processing time where event time is required, so reprocessing gives
    different results.
  - Fix: model and name times separately (`occurred_at`, `received_at`,
    `processed_at`, `effective_from`, `recorded_at`), with source and
    trust level. Set ingestion times on the server. Parse event time from
    payloads, and choose the Kafka timestamp type deliberately. Carry
    original event times through imports. Use content hashes for change
    detection. Keep audit trails append-only with server-assigned times.
  - Not a finding: fields documented as receive or processing time and
    used as such.
  - Escalate: deadline decisions ("submitted on time") that do not say
    which time counts.
- C8.2 Instants, local values, dates, and times are different types.
  - Facts: a date without a zone is a range: 2026-07-01 runs from
    2026-06-30T10:00Z in Kiritimati to 2026-07-02T11:00Z in Pago Pago, 49
    hours of instants (50 counting `Etc/GMT+12`) (verified). A local
    date-time without a zone spans 25 hours of instants across inhabited
    zones (verified). With a zone, a local time can be ambiguous or
    nonexistent (C7.3), and a future local time is fixed only when it
    happens (C10). A time of day alone names no moment. Abbreviations,
    calendars, and repeated dates add ambiguity (C13, C6). The time scale
    matters (C17), and every value has a precision (C20). Identifying a
    moment needs date, time, precision, zone or offset resolved by the
    rules in force, calendar, and time scale.
  - In code: local date-times stored or compared as instants. Date
    strings used as keys for moments. APIs accepting instants without an
    offset. One type used for instants, local date-times, dates, and
    times.
  - Fix: use distinct types (BP-1): instant, zoned or offset date-time,
    local date-time, local date, local time (for example Java
    `Instant`, `ZonedDateTime`, `OffsetDateTime`, `LocalDateTime`,
    `LocalDate`, `LocalTime`; Luxon `DateTime` with an explicit zone and
    plain ISO date strings for dates). Require an offset or `Z` for
    instants in APIs.
  - Not a finding: local dates and times used deliberately as local
    values (birthdays, opening hours) with their zone held elsewhere.
  - Escalate: values whose meaning (instant, local wall time, or date) is
    not stated in the requirement or schema.
- C8.3 Dates are not UTC midnight.
  - Facts: a date's start is midnight in some zone, which is UTC
    midnight only for zero-offset zones. Layers convert differently (Los
    Angeles host, verified): JS `new Date("2026-10-03")` is UTC midnight
    and displays as 10/2/2026; `new Date("2026-10-03T00:00")` is local
    midnight (07:00Z); Python `datetime.combine(date, time())` is naive
    local midnight. HTML `valueAsDate` returns UTC midnight. Postgres
    casts `date` to `timestamptz` at session-zone midnight. Serializers
    often write dates as UTC midnight. Some local midnights do not exist
    (Santiago 2026-09-06 starts at 01:00). Birthdays, holidays, due dates,
    effective dates, and statutory deadlines are dates.
  - In code: date-only values stored in timestamp columns as UTC
    midnight. Dates compared with instants through implicit coercion.
    Dates shown a day early in negative-offset zones. Date ranges
    converted with UTC midnight boundaries for users in other zones.
  - Fix: keep dates as date types end to end (SQL `DATE`, Java
    `LocalDate`, ISO `YYYY-MM-DD` in JSON). When an instant range is
    needed, convert with an explicit zone to `[start of day, start of next
    day)` using the library's start-of-day operation (C3.6). Use one rule
    in every layer, and test negative and positive offsets.
  - Not a finding: UTC-midnight conversion where the requirement defines
    the day in UTC.
  - Escalate: deadlines or effective dates whose governing zone is not
    stated (C14).
- C8.4 Offsets are not zones.
  - Facts: an offset is one value at one instant. A zone is rules over
    time (Chicago -06:00 in January, -05:00 in July). Many zones share an
    offset (in January -05:00 is New York, Bogota, Lima, Panama, Cancun).
    Arithmetic on offset-only values ignores DST: Java
    `OffsetDateTime.parse("2026-10-30T09:00-05:00").plusDays(5)` is 08:00
    Chicago time, while the zoned equivalent stays at 09:00 local
    (verified). RFC 3339, most JSON dates, and Postgres `timestamptz`
    carry no zone. RFC 9557 adds a bracketed zone suffix
    (`2026-07-01T10:00-05:00[America/Chicago]`), used by Java
    `ZonedDateTime` and the JS Temporal proposal.
  - In code: user, location, recurring, or future local values stored
    with a fixed offset (zone storage also C10, C14). Offset-only types
    (`OffsetDateTime`, Python `timezone(timedelta(...))`) used for local
    arithmetic. Offsets mapped back to a zone (C14).
  - Fix: store IANA zone IDs wherever local semantics matter, and keep
    offsets only to identify instants. Do local arithmetic with zoned
    types. Exchange zone IDs with timestamps (RFC 9557 or a separate
    field).
  - Not a finding: offsets used only to identify instants (logs, audit,
    RFC 3339 exchange).
  - Escalate: interfaces where consumers need local semantics but get
    only offsets.
- C8.5 Zero offsets and unknown local offset.
  - Facts: `Z`, `+00:00`, and `-00:00` name the same instant but not the
    same local meaning. RFC 3339 defines `-00:00` as "unknown local
    offset". RFC 9557 gives `Z` that meaning too. RFC 5322 defines
    `-0000` the same way for email. ISO 8601 forbids negative zero, so
    strict ISO parsers may reject `-00:00`. Common parsers merge all three
    (Python `fromisoformat`, JS `Date`, Java `OffsetDateTime.parse`,
    verified), losing the distinction.
  - In code: a `Z` timestamp taken as evidence that the user or source is
    in UTC, and local dates or zones derived from it. Every UTC value
    serialized as `+00:00` or `Z` without considering what receivers
    infer. "Unknown local offset" lost on parse where it matters later.
    Strict parsers rejecting `-00:00` from systems that use it.
  - Fix: treat a zero offset as identifying the instant only, and get
    local time from a stored zone ID. Keep "local offset unknown" as
    explicit data where it matters. Accept and document `-00:00` where
    sources use it.
  - Not a finding: zero-offset timestamps used only as instants, with
    local context stored separately.
  - Escalate: email, audit, or legal records where the original local
    offset matters and the source used `-00:00` or `Z`.
- Proposed severity (for the user to decide), per check: HIGH when the
  wrong kind of time decides deadlines, legal records, billing, or SLAs;
  imports overwrite event times; local values are treated as instants;
  dates shift by a day; offset-only values drive scheduling or
  recurrence; or local dates are derived from a zero offset, on a core
  path. MEDIUM for analytics, change detection, keys, reports, display,
  and lost provenance. LOW for test-only code.

Point ledger for C8:
- Inbound from C7.5: "record the events in question" condition -> C8.1.
- PA-31: all pipeline, database, file, device, offline, batch,
  late-entry, bitemporal, and falsification facts, all code patterns,
  checks, fixes, not-a-finding, deadline escalation -> C8.1. Processing
  time versus event time in reprocessing (from PA-26) -> C8.1 with C25
  (PA-26 stays in C25). Audit trail append-only -> C8.1. Severity -> C8
  severity.
- PA-96: date range, local date-time range, what identifies a moment,
  code patterns, distinct-types fix, offset-required fix,
  not-a-finding, meaning escalation -> C8.2. Ambiguous and skipped local
  times -> C7.3 (and library gap defaults C11 via PA-92). Future rule changes ->
  C10. Offset fixes instant but not zone -> C8.4. Abbreviations -> C13.
  Calendars and repeated dates -> C6. Time scale -> C17. Precision ->
  C20. Date to half-open instant range -> C8.3. Severity -> C8 severity.
- PA-125: all facts, code patterns, checks, date-type fix, explicit
  range fix, layer consistency and tests, not-a-finding -> C8.3.
  Missing local midnight -> C8.3 with C11. Governing-zone escalation ->
  C8.3 with C14. Severity -> C8 severity.
- PA-127: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C8.4. Offsets mapped back to zones -> C14 (PA-89).
  Severity -> C8 severity.
- PA-131: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C8.5. Severity -> C8 severity.
