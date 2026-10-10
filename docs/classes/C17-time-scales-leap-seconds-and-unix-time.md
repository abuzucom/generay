# C17 Time scales, leap seconds, and Unix time

(sources: PA-46, 47, 64, 104; inbound from PA-13, PA-20, PA-118, C1.1, C2.4, C16.3) Approved by the user.

Scope: leap seconds and how code represents them, where leap-second data
comes from, what Unix time is, how the epoch is defined, and offsets
between time scales. Smearing and clock rates are C16. Epoch values of
other platforms and type ranges are C22. Decimal-hour durations are
C21.

- C17.1 Minutes with 61 or 59 seconds.
  - Facts: a UTC minute with a positive leap second has 61 seconds
    (23:59:60). 27 were inserted from 1972 to 2016, changing the length of
    some UTC years, in both leap and common years (2015-06-30,
    2005-12-31). A negative leap second would give 59 seconds and has been
    discussed as Earth's rotation sped up. Before 1972 UTC used fractional
    steps and rate offsets. C89 allowed `tm_sec` 0 to 61, and C99 narrowed
    it to 0 to 60. Libraries differ (verified): Java
    `DateTimeFormatter.ISO_INSTANT` accepts `23:59:60Z`, maps it to
    23:59:59, and reports `parsedLeapSecond()`; Java `LocalTime.of(23,
    59, 60)` throws; Python `datetime` rejects second 60; JS `Date.parse`
    returns `NaN`. RFC 3339 allows second 60.
  - In code: validators, regexes, or types limiting seconds to 0 to 59 at
    UTC input boundaries. Inputs with second 60 rejected or crashing.
    Per-second arrays or buckets with exactly 60 slots per minute.
    `mm:ss` parsers rejecting `:60`. Leap-second handling only in leap
    years or on fixed dates.
  - Fix: accept second 60 where UTC input can contain leap seconds, and
    normalize it by a documented rule. Size per-second structures from the
    actual interval or tolerate 61 entries.
  - Not a finding: systems that receive only smeared or POSIX time and
    never see second 60, documented as such.
- C17.2 Leap-second data cannot be predicted and expires.
  - Facts: leap seconds follow observed rotation, which varies
    irregularly (tides, core, atmosphere, ice, earthquakes). The IERS
    decides each from measurements and announces it in Bulletin C about
    six months ahead. End of June or December is preferred, March or
    September second, any month end allowed. All 27 so far were positive.
    The last was at the end of 2016, and `leap-seconds.list` on this host
    ends with TAI-UTC of 37 s from 2017-01-01 (verified). The CGPM
    resolved in 2022 to raise the UT1-UTC tolerance by 2035, effectively
    ending leap seconds, with the replacement still being worked out.
    Lists expire: this host's file says "File expires on 28 December
    2026" (verified). GPS satellites broadcast upcoming leap seconds, and
    receivers mishandling the announcement have failed at the event.
  - In code: hardcoded leap-second tables with no update or expiry check.
    Formulas or schedules predicting leap seconds. Code assuming they are
    always positive, always in June or December, or finished.
  - Fix: read leap seconds from a maintained source (IERS via the OS,
    tzdata `leap-seconds.list`, or a library) and check its expiry, with
    an alert (C26). Handle positive and negative leap seconds at any month
    end. Treat future leap seconds as unknown, and use one smear or step
    policy across the fleet (C27.4).
  - Not a finding: smeared or POSIX-only systems documented as ignoring
    leap seconds.
  - Escalate: scientific, navigation, or regulated timing systems whose
    leap-second source and policy are not stated.
- C17.3 Unix time is an encoding of UTC, not a count of seconds.
  - Facts: POSIX defines "seconds since the Epoch" by a formula over UTC
    year, day, hour, minute, and second with every day 86,400 s. Leap
    seconds are not counted, so differences across them undercount SI
    seconds. A leap second has no Unix time: Python `calendar.timegm`
    maps 2016-12-31 23:59:60 and 2017-01-01 00:00:00 to 1483228800, and
    that day still measures 86,400 (verified). During a leap second
    kernels repeat, step, or smear, so Unix time can repeat or change rate.
    Unix time before 1972 does not map cleanly to elapsed seconds.
    Converting to local time needs a zone (C9).
  - In code: exact elapsed SI seconds from Unix-time differences across
    leap seconds in scientific, navigation, or long-span metering code.
    Unix time assumed strictly increasing (C19).
  - Fix: treat Unix time as civil-time encoding. For exact SI intervals,
    convert to TAI or GPS time with a maintained table (Astropy `Time`,
    SOFA/ERFA) or read Linux `CLOCK_TAI` where configured. Measure
    durations with a monotonic clock (C18).
  - Not a finding: business code where errors of up to one second per
    leap second do not matter.
  - Escalate: scientific, navigation, or regulated timestamping (EU
    MiFID II requires high-frequency trading clocks within 100 us of UTC)
    without a stated scale and accuracy.
- C17.4 The epoch is UTC midnight, and epoch arithmetic is easy to get
  wrong.
  - Facts: the epoch is 1970-01-01T00:00:00 UTC, not local midnight. The
    UK ran UTC+1 all year from 1968 to 1971, so London local midnight on
    1970-01-01 was 1969-12-31T23:00Z (`mktime` gives -3600, verified).
    Pre-1970 values are negative and valid. The unit varies (C20). C does
    not define `time_t` as seconds since 1970; POSIX does. Postgres
    `EXTRACT(EPOCH ...)` on `timestamp` gives nominal seconds with no zone,
    on `timestamptz` true Unix time. MySQL `UNIX_TIMESTAMP(datetime)` uses
    the session zone.
  - In code: epoch computed from a local date (Python
    `time.mktime((1970,1,1,...))`, naive `datetime(1970,1,1).timestamp()`,
    JS `new Date(1970, 0, 1)`), giving -3600 in London. "Epoch seconds" as
    naive local now minus naive 1970-01-01, off by the current offset
    (+3600 London, -14400 New York on 2026-10-03, verified). Java
    `LocalDateTime.toEpochSecond(offset)` given the wrong offset. SQL
    epoch extraction on zone-less columns or through a session zone, mixed
    with true Unix times. Validators rejecting negative epochs.
  - Fix: take Unix time from instant APIs (Python
    `datetime.now(timezone.utc).timestamp()` or `time.time()`, Java
    `Instant.getEpochSecond()`, JS `Date.now()`). Convert local values to
    instants with an explicit zone first. Use `timestamptz` and an explicit
    session zone before SQL epoch extraction. Allow negative values where
    the domain includes pre-1970 dates.
  - Not a finding: epoch values from instant APIs, documented with unit.
  - Escalate: stored epoch values whose producing code and zone handling
    cannot be established.
- C17.5 Offsets between time scales.
  - Facts: TAI-UTC is 37 s and GPS-UTC 18 s since 2017, and both change
    when leap seconds are added. TAI-GPS (19 s) is fixed. UT1 differs from
    UTC by under 0.9 s and varies with Earth's rotation (milliseconds per
    day in day length). A GPS receiver switches from GPS time to UTC when
    it receives the leap-second count, and devices showing GPS time differ
    from UTC by 18 s.
  - In code: literal 18, 19, or 37 s offsets near time code. TAI, GPS, or
    UTC conversions with a stale table.
  - Fix: read scale offsets from the maintained leap-second table (C17.2)
    or a library. Record each timestamp's scale (C16.2, C16.3).
  - Not a finding: genuinely fixed offsets such as TAI-GPS (19 s).
- Proposed severity (for the user to decide), per check: HIGH when
  leap-second input crashes or corrupts a core path, or exact durations,
  ordering, navigation, regulated timestamps, scale conversions, or
  stored and transmitted epochs on a core path rely on Unix time counting
  every second, predicted or stale leap-second data, or a locally
  computed epoch. MEDIUM for per-second metrics, monitoring, logs,
  leap-second input handling, and reports. LOW for test-only code.

Point ledger for C17:
- Inbound from PA-13: TAI-UTC and GPS-UTC literals, leap-second-table
  fix, TAI-GPS not-a-finding -> C17.5.
- Inbound from PA-20: 61- and 59-second minutes, POSIX repeat, second-60
  validation, accept-60 fix -> C17.1.
- Inbound from PA-118: leap seconds since 1972 changing UTC year lengths
  -> C17.1.
- Inbound from C1.1: UT1 day-length variation -> C17.5.
- Inbound from C2.4: leap seconds in common years, leap-second-table fix
  -> C17.1 and C17.2.
- Inbound from C16.3: GPS receiver scale switch -> C17.5.
- PA-46: POSIX formula, uncounted leap seconds, no Unix time for second
  60, kernel behavior, pre-1972, UTC basis, exact-SI code, TAI/GPS fix,
  `CLOCK_TAI`, not-a-finding, MiFID escalation -> C17.3. Leap-second
  representation failures, second-60 input -> C17.1. Strictly increasing
  assumption -> C19 by reference. Scale conversions by constant -> C17.5.
  Smear mixing -> C16.1. Monotonic durations -> C18. Severity -> C17
  severity.
- PA-47: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C17.4. Units -> C20 by reference. Other platform epochs ->
  C22 by reference. Severity -> C17 severity.
- PA-64: 61- and 59-second minutes, negative leap second, smeared
  minutes, pre-1972, C89 and C99, library table, validators, per-second
  arrays, `mm:ss` parsers, accept-60 fix, sizing fix, not-a-finding ->
  C17.1. Decimal hours versus `h:mm`, duration-unit fix, payroll format
  escalation -> C21 (inbound). Severity -> C17 severity (leap-second
  part) and C21 (decimal-hour part).
- PA-104: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C17.2. Stale-table conversions -> C17.5. Severity -> C17
  severity.
