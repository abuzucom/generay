# C2 Leap years and inserted days

(sources: PA-42, 43, 113; inbound from PA-2, PA-4) Approved by the user.

Scope: deciding which years are leap years, how far apart they fall,
handling February 29, days inserted outside Gregorian leap years, and
the spreadsheet phantom leap day. Year length is C1.4. Adding years to
February 29 is C7. Historical calendar transitions are C6.

- C2.1 Leap-year rules.
  - Facts: Gregorian years are leap when divisible by 4, except
    centuries, unless divisible by 400 (1900 and 2100 are not; 2000 and
    2400 are, verified). Other rules: Julian (every fourth year), Revised
    Julian (centuries leap only when the remainder by 900 is 200 or 600,
    first differing in 2800), Hebrew (7 leap months per 19 years),
    tabular Islamic (11 leap days per 30 years), Solar Hijri (observed
    equinox; arithmetic cycles disagree in some years), Ethiopian (the
    year before a Gregorian leap year), Chinese lunisolar (astronomical
    leap months). In astronomical numbering, years 0 and -4 are leap
    (verified in Java); in historical numbering those are 1 BC and 5 BC.
  - In code: `year % 4 == 0` or `(year & 3) == 0` as the whole test
    (correct only from 1901 to 2099). Firmware or clock chips with leap
    logic valid only until 2100 (for example DS1307). Gregorian tests
    applied to other calendars. Leap tests on historical BC numbers.
  - Fix: library leap tests (Python `calendar.isleap`, Java
    `Year.isLeap`, .NET `DateTime.IsLeapYear`, Luxon
    `DateTime.isInLeapYear`; in Go or plain JS, build February 29 and
    check the month, verified in JS). Calendar libraries for other
    calendars (C6). Document and enforce range limits where unavoidable.
    Test 1900, 2000, 2100, 2400, year 0, and negative years where
    supported.
  - Not a finding: `% 4` in code handling only Julian dates, documented.
    Range-limited logic whose range is enforced at input.
  - Escalate: firmware or devices expected to run past 2099 with
    range-limited leap logic.
- C2.2 Leap-year spacing and recurring February 29.
  - Facts: Gregorian leap years are usually 4 years apart but sometimes
    8 (1896 to 1904, 2096 to 2104, 2196 to 2204, 2296 to 2304, verified).
    Hebrew gaps are 2 or 3 years, Solar Hijri 4 or 5.
  - In code: next leap year as `last + 4`. Leap-day events, billing, or
    maintenance every fourth year. Hand-built February 29 recurrences.
    RFC 5545 recurrences skip years without February 29.
  - Fix: test each year with the library, never step by four. Generate
    February 29 recurrences with a recurrence library and a stated rule
    for missing years. Test across 2096 to 2104.
  - Not a finding: four-year stepping within an enforced 1901 to 2099
    range.
  - Escalate: long-horizon schedules (pensions, leases, leap-day
    contracts) without a stated leap rule.
- C2.3 February 29 validity.
  - Facts: February 29 exists in every Gregorian leap year. February 30
    and 31 never exist in the Gregorian calendar.
  - In code: validators, forms, and pickers capping February at 28 and
    rejecting valid dates such as a 2028-02-29 birth date. "End of
    February" hardcoded to the 28th, so month-end jobs miss February 29.
    Ranges ending on `02-28` dropping February 29 (half-open fix in C3).
    Validators allowing day 1 to 31 for every month, accepting 2026-02-30.
    Lenient APIs silently turning impossible dates into March dates (JS
    `Date`, Go `time.Date`).
  - Fix: get the last day of February from the library. Validate by
    constructing the date with a rejecting API (parsing detail in C23).
  - Not a finding: a literal 28 inside a February branch that also
    handles February 29 through a library leap test. Gregorian-only
    modern data validated by a library that rejects February 29 in
    common years.
- C2.4 Inserted time outside Gregorian leap years.
  - Facts: Julian-dated records contain February 29 in 1700, 1800, and
    1900 (Britain until 1752, Russia until 1918). The Ethiopian leap day
    (Pagume 6) falls in Gregorian common years, moving Ethiopian New Year
    to September 12. Hebrew leap months follow their own cycle. Leap
    seconds were inserted in common years (2015-06-30, 2005-12-31; C17).
    ISO and fiscal calendars add week 53 in years unrelated to leap years
    (2026, verified; C4, C5).
  - In code: validators rejecting February 29 of common Gregorian years
    in historical or Julian-dated data. "53 weeks only in leap years" or
    "extra day only in leap years" logic. Leap-second handling only in
    leap years.
  - Fix: validate each date in the calendar it is written in, and store
    that calendar (C6). Get week counts per year from the library. Read
    leap seconds from a maintained table (C17).
  - Escalate: historical or archival imports without a stated source
    calendar per date.
- C2.5 Spreadsheet phantom leap day.
  - Facts: Excel's 1900 date system includes the nonexistent 1900-02-29
    (serial 60), for Lotus 1-2-3 compatibility, so every serial before it
    is off by one day. The 1904 system has no phantom day. (The 1,462-day
    difference between the two systems is C24.)
  - In code: serial conversions with a fixed offset (for example 25569 to
    the Unix epoch) applied to dates on or before 1900-02-28 without the
    correction.
  - Fix: use the spreadsheet library's conversion, or apply the 1900
    correction explicitly with a comment.
  - Not a finding: 1904-system code.
  - Escalate: imports of dates that may fall before 1900-03-01 when the
    source date system is unknown.
- Proposed severity (for the user to decide), per check: HIGH when a wrong
  leap test or February 29 handling drives billing, scheduling, expiry,
  or long-horizon schedules, rejects valid input, drops leap-day
  records, silently stores or shifts an impossible or historical date,
  crashes on February 29 on a core path, or affects devices in service
  past 2099. MEDIUM for display, week-count logic, historical data, and
  reports. LOW for test-only code.

Point ledger for C2:
- Inbound from PA-2: Gregorian leap rule -> C2.1. Day 1-to-31 validators
  accepting February 30 -> C2.3. "Silently stores an impossible date"
  severity condition -> C2 severity.
- Inbound from PA-4: February 29 exists -> C2.3. Validators and pickers
  capping February at 28, end of February hardcoded, `BETWEEN ... 02-28`,
  literal-28 check and not-a-finding -> C2.3. Excel phantom day, serial
  offset, serial fix, 1900/1904 escalation, 1904 not-a-finding -> C2.5.
- PA-42: Gregorian rule, Julian, Revised Julian, Hebrew, tabular Islamic,
  Solar Hijri, Ethiopian, Chinese rules, BC numbering, `% 4` and bitmask
  tests, firmware limits, Gregorian logic on other calendars, BC tests,
  what to check, library table, calendar-library fix, range-limit fix,
  test years, not-a-findings, firmware escalation -> C2.1. 365.25 day
  counts -> C1.4. Severity -> C2 severity.
- PA-43: Julian-dated February 29, Ethiopian Pagume 6, Hebrew leap
  months, leap seconds in common years, week 53, validators rejecting
  historical February 29, "53 weeks only in leap years", leap seconds only
  in leap years, source-calendar fix, week-count fix, leap-second-table
  fix, archival escalation -> C2.4. Sweden 1700 and 1712, and the reverse
  Sweden case -> C6 (inbound). Excel phantom day and serial fix -> C2.5.
  Lenient parsers turning dates into March 1 -> C2.3. Gregorian
  not-a-finding -> C2.3. Severity -> C2 severity.
- PA-113: gaps of 8 years, other calendars' gaps, `last + 4`, every-fourth-
  year schedules, February 29 recurrences and RFC 5545, library fix,
  recurrence fix, 2096-to-2104 test, not-a-finding, long-horizon
  escalation -> C2.2. 365.25 used as exact -> C1.4. Severity -> C2
  severity.
