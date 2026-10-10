# C25 Testability and time control

(sources: PA-25, 26, 50, 95; inbound from PA-4, C6.4, C8.1, C18.4, C18.6, C19.1) Approved by the user.

Scope: controlling the time code sees, production as-of mechanisms and
overrides, the dates tests must cover, and testing devices whose zone
and date change. Multi-zone host testing is C9.1. Monitoring is C26.

- C25.1 Injectable clocks and one read per operation.
  - Facts: DST, leap days, month-ends, year-ends, expiries, and range
    limits can only be tested on demand by controlling "now". Incident
    replay needs the original time. Reproducible builds pin build time
    (`SOURCE_DATE_EPOCH`). Changing the real clock needs privileges,
    affects every process, and breaks TLS, Kerberos, and sync. Global
    mocking (`freezegun`, Jest or Sinon fake timers, `libfaketime`) misses
    C extensions, other threads, or the database. Database `NOW()` cannot
    be controlled from tests and differs from the app clock. Fake timers
    complete sleeps instantly unless advanced (C18.4).
  - In code: `now()` scattered through business logic with no injection.
    Several reads per operation (C19.1). Tests changing the system clock.
    SQL `NOW()` where application time must govern. Date-gated features
    testable only by waiting. Builds embedding the current time without
    `SOURCE_DATE_EPOCH`. Tests synchronizing with real sleeps.
  - Fix: inject a clock (Java `Clock`, .NET 8 `TimeProvider`, Go a clock
    func or interface, Python a `now` callable, JS a clock parameter or
    Luxon `Settings.now`). Read "now" once per operation and pass it down.
    Pass "now" into queries as a parameter where app time governs. Use
    fake clocks in tests, never the host clock on shared machines. Honor
    `SOURCE_DATE_EPOCH`.
  - Not a finding: edge code that reads the clock once and passes it
    down. Throwaway scripts with no time logic worth testing.
- C25.2 Production as-of mechanisms and overrides.
  - Facts: backfills, re-billing a past period, re-closes, incident
    replay, and disaster recovery run in production. Late data must be
    processed by event time (C8.1). Clock corrections, smears, and
    emergency rule changes change production time. Offline devices
    (ships, aircraft, air-gapped sites) have clocks set by hand.
  - In code: no as-of mechanism, so operators change host clocks or run
    ad hoc scripts. Jobs without an as-of parameter. Processing time where
    event time is required. Test overrides reachable in production
    (`FREEZE_TIME`, `FAKE_NOW`, fake clock as the DI default,
    `libfaketime` in an image, fake-timer setup loadable in production,
    C18.6). User-controllable time (`?now=`, `X-Debug-Time`) bypassing
    expiry, trials, promotions, and rate limits. Overridden runs leaving no
    trace.
  - Fix: provide an as-of parameter restricted to authorized operators
    and jobs, logged and audited, never changing the host clock. Record
    event and processing time and process by event time. Never accept
    "now" from end-user input. Exclude fake clocks from production builds
    or fail at startup if one is active. Stamp outputs with the as-of time
    used. Write runbooks for manual clock setting on offline devices.
  - Not a finding: test clocks that cannot be enabled in production.
    Authorized, audited operator as-of parameters.
  - Escalate: backfill, audit, or replay needs implied but not stated for
    jobs without as-of. Reprocessing without a stated rule for reproducing
    original results versus applying current rules (prices, tax rates,
    zone rules).
- C25.3 The dates tests must cover.
  - Facts: defects surface on DST transitions per zone and hemisphere;
    Feb 28, Feb 29, Mar 1 and day 366; the 29th to 31st; year-ends, ISO
    week 53, and week-year boundaries; 1970, 2036-02-07, 2038-01-19, and
    9999-12-31; GPS rollovers (1999-08-22, 2019-04-07, 2038-11-21,
    computed); rule and era changes; and moving two-digit-year windows.
    Incidents: Zune 2008-12-31, Azure 2012-02-29, New Zealand fuel payment
    terminals 2024-02-29, and Microsoft Exchange 2022-01-01 (a signed
    32-bit `yymmddHHMM` overflow: 2201010001 exceeds 2,147,483,647,
    verified arithmetic). Tests themselves depend on the run date ("expires
    in 30 days", "age is 30", failures at midnight, month-end, or the last
    week of the year, C19.1) and on the CI host zone (C9.1).
  - In code: date logic tested only for "today". No leap-day fixtures, so
    the leap path first runs in production. No parametrized or
    property-based tests over date ranges. Packed or narrow encodings that
    fit today and overflow later.
  - Fix: test a fixed matrix with an injected clock: DST start and end in
    several zones (including southern-hemisphere and non-hour zones), Feb
    28, 29, and Mar 1 in leap and common years, the 29th to 31st, Dec 31
    and Jan 1, an ISO week-53 year, 1970, 2036-02-07, 2038-01-19, and the
    domain's extremes. Add property-based tests where a supported tool
    exists (new dependencies need approval). Run the suite under several
    host zones and with the clock set forward, for example in a scheduled
    CI job. Check each encoding's overflow date before shipping.
  - Not a finding: an explicit boundary-date matrix with an injected
    clock.
  - Escalate: long-lived systems or devices with date-range limits and no
    stated service life.
- C25.4 Devices whose zone and date change.
  - Facts: phones, laptops, and in-flight or shipboard systems change zone
    in transit or on arrival. Eastbound across the date line the local
    date goes back: Tokyo 21:00 on 2026-01-10 plus a 7-hour flight lands
    in Honolulu at 09:00 on 2026-01-10, twelve local hours "before"
    departure (verified). The date line bends around island groups.
    Aviation and shipping use UTC while consumer devices use local time.
    Travelers skip or repeat local dates (C6.4).
  - In code: "arrival after departure" validated on local times.
    Durations from local times, negative or a day off. Bookings assuming
    arrival on the departure date or the next. "Today", streaks, and daily
    limits recomputed after a zone change, losing or repeating a day.
    Reminders, alarms, and medication schedules in device wall time firing
    twice, never, or a day off. Local-date-keyed caches, files, or records
    colliding. Tests that never change zone during a run.
  - Fix: compare and subtract instants, never local times from different
    zones. Store the zone with each event (departure, arrival, recorded).
    Define reminder and dosing semantics explicitly (fixed interval or
    local wall time; C7.1). Listen for zone-change events and recompute
    "today" and schedules by a documented rule. Test zone jumps across the
    line both ways (`Asia/Tokyo` to `Pacific/Honolulu`,
    `Pacific/Kiritimati` to `Pacific/Pago_Pago`).
  - Not a finding: server systems working only in UTC instants and never
    deriving local dates.
  - Escalate: daily entitlements, streaks, or medication schedules without
    defined behavior when the local date jumps.
- Proposed severity (for the user to decide), per check: CRITICAL when an
  end user can set the time the server uses for expiry, authorization, or
  payment. HIGH when time-critical core logic cannot be tested or
  backfilled without changing a real clock, tests change the clock on
  shared hosts, a fake clock can be switched on in production, core date
  logic has no boundary-date tests, an encoding overflows within service
  life, or medication, booking, or financial daily limits break on a
  crossing. MEDIUM for scattered `now()` calls, inconsistent reads,
  missing event-time handling, unaudited overrides, flaky date-dependent
  tests, streaks, reminders, and display. LOW for test-only code.

Point ledger for C25:
- Inbound from PA-4: leap-day fixtures, NZ fuel incident -> C25.3.
- Inbound from C6.4: travelers crossing the date line -> C25.4.
- Inbound from C8.1: event versus processing time in reprocessing ->
  C25.2.
- Inbound from C18.4: fake timers completing sleeps -> C25.1.
- Inbound from C18.6: fake timers in production -> C25.2.
- Inbound from C19.1: read once per operation -> C25.1.
- PA-25: all facts, code patterns, checks, fixes, not-a-findings ->
  C25.1. Batch jobs with no as-of, backfill escalation -> C25.2. Host UTC
  default -> C9.1 by reference. Severity -> C25 severity.
- PA-26: all facts, code patterns, checks, fixes, not-a-findings,
  escalation -> C25.2. Severity -> C25 severity.
- PA-50: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C25.4. Severity -> C25 severity.
- PA-95: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C25.3. Clock injection -> C25.1. Severity -> C25
  severity.
