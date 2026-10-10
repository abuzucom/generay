# C7 Date arithmetic and composition

(sources: PA-44, 69, 70, 77, 78, 79; inbound from PA-1, PA-2, PA-3, C1.4, C4.5) Approved by the user.

Scope: adding and subtracting time, building dates from parts,
recurrence generation, business-time arithmetic, and ported date
algorithms. Unit lengths are C1. Monotonic measurement of elapsed time is
C18. Clock and source validity of timestamps is C15 to C19. Duration
units and negative durations are C21. Duration string grammars are C23.

- C7.1 Elapsed versus calendar meaning.
  - Facts: "add 1 day", "add 3 hours", or "add 1 week" means either
    elapsed time or the same wall-clock position later, and the two
    differ across DST and zone changes. Elapsed noon-to-noon weeks
    (verified): New York spring week 601,200 s, fall week 608,400 s, Lord
    Howe 606,600 s, Samoa 2011 518,400 s (six days). Languages disagree
    (verified):
    - Go: `t.Add(24*time.Hour)` elapsed, `t.AddDate(0,0,1)` calendar.
    - Java: `ZonedDateTime.plusHours(3)` elapsed; `plusDays(1)` and
      `plusWeeks(1)` calendar; `Instant.plus(1, DAYS)` always 86,400 s;
      `LocalDateTime.plusHours(3)` then attaching a zone is wall clock.
    - Luxon: `plus({ hours: 24 })` elapsed, `plus({ days: 1 })` and
      `plus({ weeks: 1 })` calendar.
    - JS `Date`: `new Date(t + n)` elapsed; `setDate`/`setHours` wall
      clock. From 00:30 New York on 2026-03-08, `+3h` elapsed is 04:30,
      `setHours(+3)` is 03:30.
    - Postgres: `timestamptz + interval '24 hours'` elapsed, `+ interval
      '1 day'` calendar in the session zone.
    - Python: `aware + timedelta(...)` is wall-clock arithmetic within
      one tzinfo (03:30 in the example above), not elapsed. Convert to
      UTC, add, convert back for elapsed time.
  - In code: `now + 604800`, `now + 86400`, or hour addition used for a
    calendar meaning and shown in local time, or calendar operations used
    where elapsed time is required. Hours added to naive local values.
    Weekly recurrences stored as instants 604,800 s apart, drifting an
    hour after a transition. Literals 604800, 604800000, 10080, 168 near
    date code (day constants are C1.2).
  - Fix: decide the meaning first. Elapsed time: add to UTC instants.
    Calendar or wall-clock time: use the library's zoned calendar
    operation in the relevant zone. Know each language's default.
  - Not a finding: fixed TTLs (86,400 or 604,800 s) where the requirement
    is elapsed time, computed on UTC instants.
  - Escalate: "expires in 1 day", "weekly", "within 72 hours", shift
    lengths, or SLA hours whose spec does not say elapsed or calendar.
- C7.2 Month and year addition and recurrence.
  - Facts: adding months or years from a day missing in the target
    month (verified): overflow in JS `setMonth` and Go `AddDate` (Jan 31
    + 1 month = Mar 3, 2026); clamp in Java `plusMonths`/`plusYears`,
    Luxon, Postgres `interval '1 month'`, dateutil `relativedelta` (Feb
    28); reject in Python `date.replace` and Java `LocalDate.of`. Feb 29
    + 1 year: Python raises, JS and Go give Mar 1, Java gives Feb 28.
    Month arithmetic is not associative: Jan 31 + 1 month + 1 month = Mar
    28, but + 2 months = Mar 31. Duration addition is order-dependent:
    2000-03-30 plus 1 day then 1 month is 2000-04-30, plus 1 month then
    1 day is 2000-05-01 (verified).
  - In code: "one month" as 30 days or 2,592,000 s, "one year" as 365
    days (constants also C1.3, C1.4). Monthly recurrences anchored on the
    29th to 31st. Each occurrence computed from the previous one, so it
    drifts down and never recovers. Feb 29 anniversaries via year
    setters with no Feb 29 path. Month addition through overflowing APIs.
  - Fix: use the library's month and year addition (BP-1). State the
    month-end and Feb 29 policies (clamp, roll, or reject), and make code
    match. Compute the Nth occurrence from the anchor date and zone, each
    separately. Use a recurrence library (RFC 5545 semantics) where
    recurrence rules matter. Apply multi-unit durations in a stated order.
  - Not a finding: named financial day-count conventions (C1).
  - Escalate: monthly billing, renewal, or due dates on the 29th to 31st
    without a month-end policy. Feb 29 anniversaries with legal effect
    (age of majority, contract terms, licenses), where jurisdictions
    differ between Feb 28 and Mar 1.
- C7.3 Gaps, overlaps, and time-of-day wrap.
  - Facts: wall-clock results can land in a gap (nonexistent local time)
    or an overlap (a local time that happens twice). Libraries resolve
    them differently: shift forward, pick the earlier offset, or raise.
    Java `ZonedDateTime.of(2026-03-08, 02:30, America/New_York)` silently
    becomes 03:30-04:00, while `ofStrict` throws (verified). Time-of-day
    types wrap silently: Java `LocalTime.of(22, 0).plusHours(3)` is 01:00
    with no day carry (verified). (Library defaults as unexamined policy
    are C11.)
  - In code: hand-written `HH:MM` arithmetic with `% 24` or `% 60`,
    losing the date carry. Time-of-day types for spans that can cross
    midnight. No handling for results or merged date-time values in a gap
    or overlap.
  - Fix: use date-time types when a span can cross midnight. Never do
    clock arithmetic on strings or with modulo. Choose gap and overlap
    handling explicitly (`ofStrict`, explicit earlier or later offset).
- C7.4 Building dates from parts.
  - Facts: day 29 to 31 or Feb 29 from one date may not exist in another
    month or year. Matching leap-year status does not make a merge safe:
    April 31 does not exist in any year, day 30 or 31 in February never
    does, and 1752-09-10 never existed in Britain although 1752 was a
    leap year there (C6.3). Leap status itself depends on the calendar
    (C2.1, C6). Setters behave differently and depend on order
    (verified): JS rolls over (Jan 31 then `setMonth(3)` gives May 1);
    Python `replace(month=2)` raises; Java `withMonth(2)` clamps and
    `withDayOfMonth(30)` on February throws. Week numbers paired with the
    wrong week-year name weeks that do not exist (C4.3). Fields from
    different calendars cannot be mixed.
  - In code: day, month, and year inputs combined without validating the
    whole date. "Birthday this year" by copying month and day. "Same day
    next month" by setting the month field. Validation that checks only
    `is_leap(year)`. Setters applied in sequence on mutable dates. Tests
    covering Feb 29 but not the 30th and 31st across months.
  - Fix: construct the whole date at once with a validating API and
    handle the error. Apply the stated impossible-combination policy
    (C7.2). Use library adjusters (Java
    `TemporalAdjusters.lastDayOfMonth`) and arithmetic, not raw setters.
    Use immutable date types.
  - Not a finding: library construction with a documented, tested policy.
  - Escalate: anniversaries, renewals, or recurring dates built from
    parts without a policy for missing days.
- C7.5 Subtracting timestamps.
  - Facts: a difference measures elapsed time only when both values come
    from one clock with no step, slew, or smear between them (C15, C16),
    share a time scale with leap seconds accounted for (C17), are
    instants rather than local wall-clock values, have adequate
    precision (C20), record the events in question (C8), and the clock
    ran through any suspension that should count (C18). Subtraction can
    ignore DST (verified): Python same-tzinfo aware values give `1 day,
    0:00:00` across a 23-hour day; Java `Duration.between` gives `PT24H`
    on `LocalDateTime` and `PT23H` on `ZonedDateTime`; Postgres
    `timestamp` and MySQL `TIMESTAMPDIFF` on `DATETIME` use wall-clock
    values. JS `Date` and Postgres `timestamptz` subtract instants.
  - In code: durations from local or same-zone aware values, local types,
    or zone-less SQL columns. Week or day counts as `(b - a) / 604800` or
    `/ 86400000` with truncation. Durations across machines or a clock
    step. No uncertainty reported where inputs carry it.
  - Fix: subtract instants (convert to UTC, or use `Instant`,
    `timestamptz`). Count calendar days and weeks on local dates. For
    in-process durations use a monotonic clock (C18). For cross-system
    durations, state the uncertainty or measure on one authoritative
    clock (C15).
  - Not a finding: differences of UTC instants from one clock where small
    errors do not matter.
  - Escalate: billing, payroll, SLA, or regulatory durations from
    timestamps whose source and type are not established.
- C7.6 Business-time arithmetic.
  - Facts: "4 business hours from now" or "T+2" must skip nights,
    weekends, regional holidays, partial days, and swapped workdays in
    the right zone (calendars in C4.4, C4.5).
  - In code: business deadlines from plain hour or day addition, fixed
    working-day assumptions, or SLA timers that pause only for whole
    holiday dates.
  - Fix: compute business time with a library or service holding the
    region's working hours, weekends, and holidays.
  - Escalate: SLAs, settlement, or deadlines stated in business time
    whose business calendar is not defined.
- C7.7 Published and ported date algorithms.
  - Facts: published algorithms carry assumptions. The XML Schema
    duration-addition algorithm uses fixed offsets with no zone rules and
    one month-end policy. XML Schema durations are only partially ordered
    (P1M versus P30D). XML Schema 1.0 had no year 0000, and 1.1 allows it
    as 1 BCE. Specifications publish errata. Spec helpers (`fQuotient`,
    `modulo`) use floor semantics, while Java, C, and JS `/` and `%`
    truncate (`-7 / 2` is -3 and `-7 % 2` is -1; `Math.floorDiv` -4,
    `Math.floorMod` 1; Python `//` and `%` floor) (verified). No
    published algorithm covers leap seconds, historical calendars, or
    regional rules unless it says so.
  - In code: hand-ported pseudocode. Truncating division or modulo in
    ported arithmetic. `xs:duration` values compared or summed as if
    months had fixed lengths. Data exchanged between systems on
    different specification versions.
  - Fix: prefer a maintained library (BP-1). When porting, use floor
    division and modulo explicitly and port the specification's tests.
    Record the version and errata followed. Check the algorithm's
    assumptions against the requirement. Test negatives, month-ends, leap
    years, year 0, and DST transitions.
  - Not a finding: library implementations used within their documented
    assumptions.
  - Escalate: interfaces whose duration semantics follow a specification
    version the requirement does not name.
- Proposed severity (for the user to decide), per check: HIGH when
  arithmetic with the wrong meaning, an impossible or silently rolled
  date, a lost date carry, or a wrong difference drives deadlines, SLAs,
  shifts, dosing, billing, renewals, appointments, payroll, or stored
  dates on a core path, or silently stores an impossible date. MEDIUM for
  display, reminders, reports, form validation, and data exchange. LOW
  for test-only code.

Point ledger for C7:
- Inbound from PA-1: language traps table, "decide intent first" fix,
  "expires in 1 day" escalation -> C7.1.
- Inbound from PA-2: monthly recurrence on 29 to 31, overflow, clamp,
  reject table, non-associativity, anchor recurrence fix, month-end
  policy fix and escalation -> C7.2. "Silently stores an impossible date"
  severity -> C7 severity.
- Inbound from PA-3: Feb 29 plus one year table, Feb 29 policy fix,
  Feb 29 legal escalation -> C7.2.
- Inbound from C1.4: add years with the library -> C7.2.
- Inbound from C4.5: business-hours SLA pauses -> C7.6.
- PA-44: two meanings, language table, gaps and overlaps, library
  resolution differences -> C7.1 and C7.3. Time-of-day wrap, `% 24`,
  time-of-day types, gap handling -> C7.3. Business-time arithmetic ->
  C7.6. Naive local addition, decide-meaning fix, language defaults,
  Python UTC fix, not-a-finding, elapsed-or-wall escalation -> C7.1.
  Business-calendar escalation -> C7.6. Severity -> C7 severity.
- PA-69: week elapsed-seconds table, leap-second week, `+ 604800`,
  weekly recurrence drift, library semantics, literals, meaning fix,
  library week addition, not-a-finding, weekly escalation -> C7.1. Week
  counts by division, count-on-local-dates fix -> C7.5. Anchor-based
  weekly occurrences -> C7.2. Severity -> C7 severity.
- PA-70: validity conditions, subtraction semantics table, local and
  mixed-source durations, missing uncertainty, what to check, instant
  fix, monotonic fix, cross-system fix, record-meaning fix,
  not-a-finding, escalation -> C7.5 (condition details stay in C8, C15 to
  C20 by reference). Severity -> C7 severity.
- PA-77: month-length and Feb 29 merges, setter table, week fields,
  mixed calendars, parts combined, birthday this year, same day next
  month, setters in sequence, construction fix, policy fix, adjusters,
  immutable types, not-a-finding, escalation -> C7.4. Date plus time plus
  zone gap and overlap, `ofStrict` -> C7.3. Separate clock reads ->
  C19 (already there via PA-53). Severity -> C7 severity.
- PA-78: April 31, February 30 and 31, 1752 gap, calendar-dependent
  leap status, Hebrew leap month, leap-only validation, test gap,
  construct-and-validate fix, historical validation reference ->
  C7.4. DST gap in merges -> C7.3. Severity -> C7 severity.
- PA-79: all points -> C7.7, except order-dependent addition -> C7.2,
  and month-end policy -> C7.2 by reference. Severity -> C7 severity.
