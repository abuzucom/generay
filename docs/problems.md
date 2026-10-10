# Problems and bad assumptions

Working notes for every problem and bad assumption (PA) the user supplied,
each recorded as a summary, never the user's own sentence. The class files
in `docs/classes/` and their point ledgers are authoritative where these
notes differ. Severities follow the rule in `TIME.md`; the per-PA severity
lines below are the original proposals.

Rule: never reproduce a user-supplied PA sentence verbatim. Record a
summary that keeps its intent and meaning.

- PA-1: Fixed day length. Code treats every calendar day as exactly
  24 hours.
  - Why it is false:
    - DST: a local calendar day lasts 23 or 25 hours on transition days.
    - Non-hour shifts: Lord Howe Island shifts 30 minutes (23.5 h or
      24.5 h days). Troll Station, Antarctica, shifts 2 hours (22 h or
      26 h days).
    - Zone changes by government: Samoa skipped 2011-12-30 entirely when
      it moved from UTC-10 to UTC+14. Offset changes can lengthen or
      shorten a day by any amount.
    - Leap seconds: a UTC day containing 23:59:60 lasts 86401 s. POSIX
      time, most OS clocks, and smearing NTP hide this. Leap seconds are
      scheduled to be discontinued by 2035.
  - How it appears in code:
    - Adding `86400`, `86400000`, or `24*60*60*1000` to a timestamp to
      mean "tomorrow" or "same time next day", then rendering in a local
      zone. The result lands at 23:00 or 01:00.
    - Days between two dates computed as `(b - a) / 86400000` with
      floor or truncation. Across a spring-forward day this is off by one.
    - Looping over days with a fixed 24 h step. The loop drifts off
      midnight, then skips or repeats a date.
    - Assuming 24 hourly buckets per day in reports, charts, billing, or
      rate limits. Transition days have 23 or 25.
    - Language traps:
      - Go: `t.Add(24*time.Hour)` is elapsed time. `t.AddDate(0,0,1)`
        is a calendar day.
      - Java: `ZonedDateTime.plusHours(24)` vs `plusDays(1)`. Note that
        `Instant.plus(1, ChronoUnit.DAYS)` is always 86400 s.
      - Luxon: `plus({ hours: 24 })` vs `plus({ days: 1 })`.
      - JS Date: `setDate(getDate() + 1)` keeps local wall time.
        `new Date(t + 86400000)` does not.
      - Postgres: `timestamptz + interval '24 hours'` vs `+ interval
        '1 day'`. The second follows the session TimeZone.
      - Python, the opposite trap: `aware_dt + timedelta(hours=24)` is
        wall-clock arithmetic within the same tzinfo. It does not give
        24 elapsed hours across DST. To get elapsed time, convert to UTC,
        add, then convert back.
  - What to check:
    - Literal 86400, 86400000, 1440, or `24*60*60` near a datetime value.
    - Integer division of a timestamp difference by a day constant.
    - Elapsed-time APIs used for calendar intent, and calendar APIs used
      for elapsed intent.
  - Fix:
    - Decide the intent first. A duration (elapsed time) is stored and
      added in UTC as an instant. A period (calendar day, same wall time
      tomorrow) is computed with the library's calendar-day operation in
      the relevant zone.
    - Count calendar days on local dates, not on timestamp differences.
    - Bucket by local date and allow 23, 24, or 25 hours.
  - Not a finding:
    - A fixed 86400 s TTL or timeout where the requirement really is
      elapsed time, for example "token valid for 24 hours", computed on
      UTC instants.
    - UTC-only systems with no local-day semantics anywhere. Ignoring
      leap seconds is normal POSIX behavior.
  - Escalate (NEEDS-HUMAN): a requirement such as "expires in 1 day"
    whose spec does not say whether it means 24 elapsed hours or the
    same local time on the next calendar day.
  - Proposed severity (for the user to decide): HIGH when the result
    drives money, deadlines, scheduling, or data retention on a core
    path. MEDIUM for reports and display. LOW for test-only code.
- PA-2: Fixed month length. Code treats every month as 30 or 31 days
  long.
  - Why it is false:
    - Gregorian February has 28 or 29 days. The leap rule is: divisible
      by 4, except centuries, except centuries divisible by 400. 2100 is
      not a leap year. 2000 was.
    - Calendar reform months: October 1582 (Catholic states) lost 10
      days. September 1752 (Britain and its colonies) had 19 days.
      February 1918 (Russia) had 15. Sweden had a February 30 in 1712.
      Proleptic Gregorian libraries and databases disagree with
      historical records for these dates.
    - Other calendars: Hebrew and Islamic months have 29 or 30 days.
      Solar Hijri months have 29 to 31 days. Ethiopian and Coptic
      calendars have a 13th month of 5 or 6 days.
    - Fiscal calendars (4-4-5, 4-5-4, 5-4-4) use "months" of 28 or 35
      days.
  - How it appears in code:
    - Hand-written days-in-month tables (`[31,28,31,...]`) with no leap
      handling, or a `year % 4 == 0` leap rule.
    - "One month" as `30 * 86400` seconds or `30` days.
    - Date validation that accepts day 1 to 31 for every month, for
      example a regex like `(0[1-9]|[12]\d|3[01])`, so 2026-02-30 is
      accepted.
    - "Last day of month" hardcoded to 30 or 31.
    - Monthly recurrence anchored on day 29, 30, or 31.
    - Month addition from a day that does not exist in the target
      month. Libraries disagree (verified):
      - Overflow: JS `Date.setMonth` and Go `AddDate(0,1,0)` turn
        Jan 31 + 1 month into Mar 3 (2026). JS `new Date(2026,1,30)`
        and Go `time.Date(2026,2,30,...)` silently become Mar 2.
      - Clamp: Java `plusMonths`, Luxon `plus({months:1})`, Postgres
        `+ interval '1 month'`, and dateutil `relativedelta` give
        Feb 28.
      - Reject: Python `date(2026,2,30)` and Java `LocalDate.of(2026,2,30)`
        raise.
    - Month arithmetic that is not associative: Jan 31 + 1 month + 1
      month = Mar 28, but Jan 31 + 2 months = Mar 31 (Java, verified).
      Code that adds one month per iteration drifts down and never
      recovers.
  - What to check:
    - Literal day-of-month tables, `% 4` leap tests, 28/29/30/31 or
      2592000 (30 days in seconds) near date code.
    - Month addition through overflowing APIs (JS Date, Go AddDate).
    - Recurring schedules that add one month to the previous occurrence
      instead of computing each occurrence from the original anchor.
    - Validators and parsers that accept impossible dates without
      round-trip checking.
  - Fix:
    - Use the library's days-in-month and month-addition operations
      (BP-1).
    - State the month-end policy in the requirement: clamp to the last
      day, roll to the next month, or reject. Code must match it.
    - Compute the Nth occurrence of a monthly series from the anchor
      date, not from the previous occurrence.
    - Validate dates by constructing them with a rejecting API, not
      with range checks.
  - Not a finding:
    - Financial day-count conventions such as 30/360 or Actual/360,
      when they are named and intentional.
    - A fiscal or non-Gregorian calendar that is handled through a
      library or an explicit table owned by that calendar's definition.
  - Escalate (NEEDS-HUMAN): monthly billing, renewal, or due dates on
    the 29th to 31st where the spec does not state the month-end policy.
  - Proposed severity (for the user to decide): HIGH when it drives
    billing, renewals, deadlines, or retention on a core path, or when
    it silently stores an impossible date. MEDIUM for reports and
    display. LOW for test-only code.
- PA-3: Fixed year length. Code treats every year as 365 days long.
  - Why it is false:
    - Gregorian leap years have 366 days (rule in PA-2).
    - Reform and government-change years: 1582 (Catholic states) and
      1752 (Britain) had 355 days. In England, legal 1751 began on
      March 25, so it ran only to December 31 (282 days). Russia 1918
      had 352. Sweden 1712 had 367. Samoa 2011 had 364.
    - Other calendars: Islamic years have 354 or 355 days. Hebrew years
      have 353 to 355 days, or 383 to 385 with a leap month.
    - Week-based years: ISO 8601 week-years and 52/53-week fiscal years
      have 364 or 371 days. Their boundaries differ from Jan 1. Verified:
      2027-01-01 is ISO week 53 of 2026.
  - How it appears in code:
    - "One year" as `365 * 86400` seconds or `365` days. Expiries,
      subscriptions, and retention drift one day per leap year.
    - Age or tenure as `days / 365` or `days / 365.25`. Wrong near
      birthdays and anniversaries.
    - Day-of-year arrays sized 365 or loops to 365. Day 366 overflows on
      Dec 31 of a leap year. Real outages: the Microsoft Zune freeze on
      2008-12-31, and the Azure leap-day certificate outage on
      2012-02-29.
    - Annual date from Feb 29. Libraries disagree (verified):
      - Raise: Python `date.replace(year=y+1)` raises ValueError.
      - Roll: JS `setFullYear` and Go `AddDate(1,0,0)` give Mar 1.
      - Clamp: Java `plusYears(1)` gives Feb 28.
    - Week-year confusion: Java `DateTimeFormatter` pattern `YYYY` is
      week-based year, not calendar year. With the default US locale,
      2026-12-31 formats as 2027-12-31 (verified). The result depends on
      the host locale.
  - What to check:
    - Literals 365, 366, 365.25, 31536000, 31557600, or 8760 near date
      code.
    - `replace(year=...)` and other year setters with no Feb 29 path.
    - Fixed-size day-of-year structures.
    - Age and anniversary logic built on day counts.
    - `YYYY` or `%G` and `%V` used where the calendar year was meant.
  - Fix:
    - Add years with the library's calendar operation (BP-1) and state
      the Feb 29 policy: Feb 28, Mar 1, or reject.
    - Compute age by comparing year, month, and day, not by dividing
      day counts.
    - Size day-of-year structures to 366, or use the library's day-of-
      year value.
    - Use `yyyy` or `uuuu` for calendar years. Use week-year tokens only
      for week-based reports.
  - Not a finding:
    - Named financial day-count conventions such as Actual/365 Fixed.
    - A 365-day duration that the requirement defines as exactly 365
      elapsed days, not "one year".
    - Week-year tokens in code that intends ISO week reporting.
  - Escalate (NEEDS-HUMAN):
    - Feb 29 anniversaries with legal effect: age of majority, contract
      terms, license renewals. Jurisdictions differ between Feb 28 and
      Mar 1.
    - "Valid for one year" with no definition of calendar year vs 365
      days.
  - Proposed severity (for the user to decide): HIGH when it drives
    expiry, billing, legal age, retention, or crashes a core path on a
    leap day. MEDIUM for reports and display. LOW for test-only code.
- PA-4: Fixed February length. Code treats February as always 28 days
  long.
  - Overlap: PA-2 covers month lengths and month addition. PA-3 covers
    Feb 29 plus one year and leap-day outages. PA-4 adds the
    February-specific cases below. Merged per the class ledgers.
  - Why it is false:
    - Feb 29 exists in every Gregorian leap year.
    - Historical Februaries: 30 days in Sweden 1712, 15 days in Russia
      1918, and a Feb 30 in the Soviet revolutionary calendar in 1930
      and 1931.
    - Spreadsheet epochs: Excel's 1900 date system treats 1900 as a
      leap year (Lotus 1-2-3 compatibility). Serial 60 is the
      nonexistent 1900-02-29. Every serial before it is off by one day.
  - How it appears in code:
    - Validators, forms, and date pickers that cap February at 28 and
      reject a valid 2028-02-29, for example a birth date.
    - "End of February" hardcoded to the 28th. Month-end jobs run a day
      early in leap years and miss Feb 29 records.
    - Range queries such as `BETWEEN 'YYYY-02-01' AND 'YYYY-02-28'` that
      drop Feb 29 data.
    - Excel serial conversion with a fixed offset (25569 to the Unix
      epoch) applied to dates on or before 1900-02-28 without the
      phantom-day correction.
    - Tests and frozen clocks that never exercise Feb 29. The leap-day
      path first runs in production. Real incident: payment terminals at
      New Zealand fuel stations failed on 2024-02-29.
  - What to check:
    - Literal `28` paired with month 2 or "Feb" in validation, range,
      and month-end code.
    - Closed date ranges that end on 02-28.
    - Spreadsheet import and export code that converts serial numbers.
    - Test suites with no leap-day fixture for date-handling code.
  - Fix:
    - Get the last day of February from the library (BP-1).
    - Use half-open ranges: `>= 'YYYY-02-01' AND < 'YYYY-03-01'`.
    - Use the spreadsheet library's serial conversion, or apply the
      1900 correction explicitly with a comment.
    - Add Feb 28, Feb 29, and Mar 1 fixtures for leap and non-leap
      years.
  - Not a finding:
    - A literal 28 inside a February branch that also handles Feb 29
      from a library leap test.
    - Excel 1904 date system code, which has no phantom day.
  - Escalate (NEEDS-HUMAN): spreadsheet imports of dates that may fall
    before 1900-03-01, when the source date system (1900 or 1904) is not
    known.
  - Proposed severity (for the user to decide): HIGH when it rejects
    valid user input on a core flow, drops leap-day records from billing
    or reporting, or crashes on Feb 29. MEDIUM for display and
    secondary reports. LOW for test-only code.
- PA-5: Window containment. Code treats a 24-hour span as falling inside
  a single calendar day, week, or month.
  - Why it is false:
    - Any 24-hour span that does not start at local midnight crosses a
      day boundary. Depending on where it starts, it also crosses a
      week, month, or year boundary.
    - The boundaries depend on the zone. The same span can sit inside
      one UTC day and cross a boundary in the user's zone.
    - On DST days, a 24-hour span that starts at midnight ends at 23:00
      or 01:00 on another date (PA-1).
    - Week boundaries depend on locale: Sunday in the US, Monday in ISO
      8601, Saturday in parts of the Middle East. Fiscal periods add
      their own boundaries.
  - How it appears in code:
    - Grouping, bucketing, or partitioning a span by its start time
      only. All activity is credited to the start's day, week, or
      month.
    - Computing `end = start + 24h` and then using the start's date,
      week, or month for both ends.
    - Assertions or branches such as `start.date() == end.date()`.
    - Daily quotas or rate limits mixing a rolling 24-hour window with
      a calendar-day reset. Users get double quota or are locked out
      across midnight.
    - Shift, session, stay, or rental billing that ignores overnight
      spans, for example night shifts and per-day overtime.
    - Daily file names, cache keys, or table partitions taken from the
      span start. Writes for the second day land in the wrong place.
    - Month-end or year-end batches that select spans by start month
      and miss the portion after the boundary.
  - What to check:
    - Date, week, or month extracted from only one end of a span.
    - Aggregation keyed on a span start with no splitting.
    - Rolling-window and calendar-period logic in the same feature.
    - The zone used to define day, week, and month boundaries.
  - Fix:
    - Decide the attribution rule in the requirement: by start, by
      end, split across periods, or by overlap.
    - When splitting, cut spans at period boundaries in the defining
      zone. Use the library's interval tools (BP-1), for example
      Luxon `Interval.splitAt` and `Interval.splitBy`.
    - Choose either a rolling window or a calendar period for each
      quota, not both.
    - Use half-open intervals so a boundary instant belongs to exactly
      one period.
  - Not a finding:
    - A documented attribution rule, for example "a session counts on
      its start date", that the code follows.
    - Rolling windows that are never mapped onto calendar periods.
  - Escalate (NEEDS-HUMAN): payroll, overtime, billing, tax, or
    regulatory daily limits where the attribution rule for spans that
    cross boundaries is not stated.
  - Proposed severity (for the user to decide): HIGH when it misstates
    pay, charges, quotas, or legal limits on a core path. MEDIUM for
    reports and analytics. LOW for test-only code.
- PA-6: Week-in-month containment. Code treats each calendar week as
  lying entirely within one month.
  - Overlap: PA-5 covers spans that cross period boundaries in general.
    PA-3 covers ISO week-years. PA-6 adds the week-to-month cases below.
    Merged per the class ledgers.
  - Why it is false:
    - A month starts on the first day of the week only by chance. Most
      months begin and end partway through a week.
    - A month covers 4, 5, or 6 calendar weeks. With weeks starting on
      Sunday (verified for 2026): February covers 4, March covers 5,
      and August covers 6.
    - The week start depends on locale (PA-5), so which weeks straddle a
      month boundary also depends on locale.
    - The week that straddles December and January also straddles the
      year, and ISO 8601 may assign it to either year (PA-3).
  - How it appears in code:
    - "Week of month" as `ceil(day / 7)`. These 7-day blocks do not
      match the calendar weeks a user sees.
    - Month calendar UIs with a fixed 4 or 5 rows. Days at the end of
      6-week months are cut off.
    - Weekly records grouped or partitioned by the month of the week
      start or week end, with no split.
    - Monthly totals built by summing weekly totals. Straddling weeks
      are counted twice or dropped.
    - Weekly payroll, invoicing, or digests reconciled against monthly
      accounting periods by week-start month.
    - Week start hardcoded to Sunday or Monday regardless of locale.
  - What to check:
    - Arithmetic that derives a week number from day of month.
    - Fixed row counts in month grid rendering.
    - Week-to-month mapping and roll-ups of weekly data into months.
    - Where the week start comes from: a literal, the locale, or ISO.
  - Fix:
    - State the week-to-month rule in the requirement: split the week
      at the month boundary, assign by start, assign by end, or assign
      by majority (for example the ISO-style Thursday rule).
    - Build month totals from daily data, or split straddling weeks,
      instead of summing whole weeks.
    - Size month grids from the library's own count of weeks in the
      month.
    - Get the week start from the library and locale (BP-1), for
      example Luxon `startOf('week', { useLocaleWeeks: true })`, or use
      ISO weeks deliberately.
  - Not a finding:
    - Fiscal calendars such as 4-4-5, whose periods are defined in
      whole weeks by design.
    - A documented week-to-month rule that the code follows.
  - Escalate (NEEDS-HUMAN): weekly payroll, billing, or compliance
    reporting that crosses a month-end close where the attribution rule
    is not stated.
  - Proposed severity (for the user to decide): HIGH when it misstates
    pay, revenue, or regulated reporting on a core path. MEDIUM for
    calendar UIs that hide days, and for analytics. LOW for test-only
    code.
- PA-7: Period-in-year containment. Code treats every week and every
  month as lying entirely within one year.
  - Overlap: PA-3 covers ISO week-year basics and the Java `YYYY`
    pattern. PA-5 and PA-6 cover boundary crossing in general. PA-7 adds
    the year-boundary cases below. Merged per the class ledgers.
  - Why it is false:
    - Weeks: the week containing Jan 1 usually starts in December. ISO
      week 1 of 2026 starts on 2025-12-29 (verified). Some years have an
      ISO week 53: 2020, 2026, and 2032 (verified).
    - Months, Gregorian: a calendar month never crosses Dec 31 in its
      own zone. In UTC it can. Local January in Tokyo starts at
      2026-12-31 15:00 UTC. A New York event at 2026-12-31 20:00 is
      2027-01-01 01:00 UTC (verified).
    - Months, other definitions: billing cycles anchored mid-month
      (Dec 15 to Jan 14), fiscal months in 4-4-5 calendars, and months in
      lunar calendars (an Islamic month can span Gregorian years).
    - Years that do not start on Jan 1: fiscal years (US federal from
      Oct 1), tax years (UK from Apr 6), academic years, and the Hebrew
      year. Whether a period crosses "the year" depends on which year.
  - How it appears in code:
    - Week labels built as `%Y-W%V`. This mixes calendar year with ISO
      week. 2024-12-30 becomes `2024-W01` instead of `2025-W01`
      (verified). The correct pattern is `%G-W%V`.
    - Weekly records assigned to the year of the week start, or stored in
      year-partitioned tables or indexes by week start.
    - Annual totals that sum 52 weeks and drop week 53, or count a
      straddling week in both years.
    - Year taken from a UTC timestamp for an event whose year is defined
      in local time. Events near New Year land in the wrong year.
    - Billing cycles, subscriptions, or accruals crossing Dec 31
      credited entirely to one year. Annual caps, tax-year totals, and
      year-end close are wrong.
    - Fiscal or tax year computed as the calendar year.
  - What to check:
    - Week labels and keys mixing `%Y`/`yyyy` with `%V`/`ww`.
    - Year extracted from the start or end only of a week, cycle, or
      span.
    - Year derived from a UTC instant where the business year is local.
    - Annual aggregation of weekly data, and handling of week 53.
    - Any "year" that is fiscal, tax, or academic but computed as Jan 1
      to Dec 31.
  - Fix:
    - Pair week numbers only with week-based years: `%G-W%V`, Java
      `IsoFields.WEEK_BASED_YEAR` with `IsoFields.WEEK_OF_WEEK_BASED_YEAR`
      (Java `YYYY`/`ww` follow the host locale, PA-3), or the library's
      ISO week-year field (BP-1).
    - Derive the business year from the local date in the defining zone.
    - State which year applies (calendar, fiscal, tax) and the rule for
      periods that cross it: split, by start, by end, or by majority.
    - Build annual totals from daily data, or split straddling periods.
  - Not a finding:
    - ISO week-year reporting that is used on purpose and labeled as
      such.
    - A documented attribution rule, such as "a billing cycle belongs to
      the year it starts in", that the code follows.
  - Escalate (NEEDS-HUMAN): tax-year, fiscal-year, or regulatory annual
    reporting where the attribution rule for straddling periods, or the
    defining zone, is not stated.
  - Proposed severity (for the user to decide): HIGH when it misstates
    tax, revenue, annual caps, or regulated reports. MEDIUM for
    analytics and labels. LOW for test-only code.
- PA-8: Host zone assumption. Code assumes the machine it runs on is set
  to UTC or GMT.
  - Why it is false:
    - Hosts vary: developer laptops, on-premises and Windows servers,
      VMs built from regional images, and end-user devices (browsers,
      mobile, desktop) all run in a local zone. Containers default to
      UTC only until someone sets `TZ` or mounts `/etc/localtime`.
    - The zone can change with no code change: a region migration, a new
      base image, an ops change to `TZ`, or a new deployment target.
    - Databases have their own zone setting, independent of the
      application host: MySQL `time_zone`/`system_time_zone`, Postgres
      `TimeZone` (set per server, role, or session).
    - "GMT" is not the same as UTC in common use. `Europe/London`
      displays as GMT in winter and BST (UTC+1) in summer. Only
      `Etc/GMT`/`UTC` are fixed at UTC+0.
    - CI runners often default to UTC, so tests pass in CI and fail, or
      pass wrongly, on machines in other zones.
  - How it appears in code (calls that read the host zone):
    - Python: naive `datetime.now()`, `date.today()`,
      `datetime.fromtimestamp(ts)`, `time.mktime`. Naive
      `datetime.utcnow().timestamp()` is read as local time: on a New
      York host it is 4 hours off (verified).
    - JS: `new Date(y, m, d)`, `getHours()`/`getDate()`, `toString()`.
      `new Date("2026-07-01T09:00")` is parsed as host local time, but
      `new Date("2026-07-01")` is parsed as UTC midnight (verified).
    - Java: `LocalDateTime.now()`, `LocalDate.now()`,
      `ZoneId.systemDefault()`, `TimeZone.getDefault()`, and
      `SimpleDateFormat` with no zone set.
    - Go: `time.Now()` carries `time.Local`, and formatting uses it.
      `time.Parse` with no offset gives UTC, while `time.ParseInLocation`
      uses the given zone (verified).
    - .NET: `DateTime.Now`, `DateTime.Today`, `ToLocalTime()`, and
      `DateTime.Parse` producing `Kind.Local` or `Unspecified`.
    - SQL: `NOW()`, `CURRENT_DATE`, and `timestamptz` to `date` casts
      follow the session zone. Connections that never set the session
      zone inherit the server's.
    - Ops: cron entries, log timestamps without offset, and shell
      `date` calls in scripts.
  - What to check:
    - Any call above whose result is stored, compared, sent over the
      wire, or used for "today" or a business deadline.
    - Whether the code states a zone anywhere, or relies on deployment
      config (`TZ` in Dockerfiles, Kubernetes manifests, systemd units).
    - Database connection setup: is the session zone set explicitly?
    - Tests that never pin or vary `TZ`.
  - Fix:
    - Read the current instant in explicit UTC: Python
      `datetime.now(timezone.utc)`, Java `Instant.now()`, Go
      `time.Now().UTC()`, .NET `DateTimeOffset.UtcNow`, Luxon
      `DateTime.utc()` (BP-1).
    - For local meaning ("today", "end of business day"), use the
      user's or business's named zone explicitly, never the host's.
    - Set the database session zone on every connection.
    - Run tests under several `TZ` values, including UTC, a negative
      offset, a positive offset over +12, and a non-whole-hour offset
      such as `Asia/Kathmandu` (+05:45).
    - Setting `TZ=UTC` in deployment is good defense in depth. It does
      not replace explicit zones in code.
  - Not a finding:
    - Desktop or CLI tools whose requirement is to show the user's own
      local time.
    - A process that sets its zone explicitly and asserts it at startup,
      failing fast if it differs, where that is documented.
  - Escalate (NEEDS-HUMAN): code that stores or acts on host-local values
    when the deployment config that sets the zone is outside the review
    unit.
  - Proposed severity (for the user to decide): HIGH when stored values,
    billing, scheduling, or expiry depend on the host zone. MEDIUM for
    logs, reports, and display. LOW for test-only code, but note that
    tests passing only under UTC hide production defects.
- PA-9: Static zone assumption. Code assumes the zone a program serves,
  and that zone's rules, stay fixed over the program's lifetime.
  - Overlap: PA-8 covers the host zone. PA-9 covers change over time: of
    the zone the program serves, of a user's zone, and of a zone's rules.
    Merged per the class ledgers.
  - Why it is false:
    - The zone being served changes: a business expands across zones,
      moves headquarters, or migrates hosting regions (PA-8).
    - The user's zone changes: travel, relocation, or a device that
      updates its zone automatically mid-session.
    - The zone's rules change by government decision. IANA tzdata ships
      several releases a year. Examples (verified against tzdata 2026b
      on this host):
      - Mexico City dropped DST: summer offset -05:00 in 2022, -06:00 in
        2023.
      - Egypt (`Africa/Cairo`) restored DST in 2023: +03:00 in summer.
      - Greenland (`America/Nuuk`) moved standard time from -03:00 to
        -02:00 in 2023.
      - Kazakhstan (`Asia/Almaty`) moved from +06:00 to +05:00 on
        2024-03-01.
      - Paraguay (`America/Asuncion`) adopted permanent -03:00 in late
        2024.
    - Notice can be days. Egypt cancelled DST in 2016 days before it was
      due to start. Lebanon reversed a 2023 DST postponement within days.
  - How it appears in code:
    - Hardcoded offsets for a named place, for example `-05:00` for New
      York or `+08:00` for a region, instead of an IANA zone ID.
    - Hand-written DST rules (`if month in 3..10: offset += 1`).
    - A single global constant such as `APP_TZ = "America/Chicago"` used
      for every user and every entity.
    - Future local-time events (appointments, store openings, deadlines)
      converted to UTC once at write time. A later rule change moves the
      real event, but the stored instant does not move.
    - Zone abbreviations or raw offsets stored instead of zone IDs. The
      code can no longer recompute when rules change.
    - Computed offsets or UTC conversions cached for long periods.
    - User zone read once at login or signup and never refreshed.
    - Stale tz data in any layer. Each layer carries its own copy:
      - OS packages (`/usr/share/zoneinfo`).
      - Java runtime tzdb (updated via JDK release or TZUpdater).
      - Python: `zoneinfo` uses system data or the `tzdata` package;
        pytz ships its own copy.
      - Node and browsers: ICU data bundled in the binary.
      - Android and iOS: updated with the OS.
      - MySQL: zone tables loaded once with `mysql_tzinfo_to_sql`.
      - Postgres: compiled-in or system data, depending on the build.
    - Layers on different tz data versions disagree about the same
      instant.
  - What to check:
    - Literal offsets and DST month rules near datetime code.
    - Global or config-level zone constants applied to all users.
    - How future local-time events are stored: as an instant only, or
      as local time plus zone ID.
    - Whether user zone is per user or entity, and when it refreshes.
    - Whether tz data has an update process in every layer.
  - Fix:
    - Store IANA zone IDs, not offsets or abbreviations.
    - Past events: store the UTC instant (optionally with the offset in
      effect).
    - Future local-time events: store local date-time plus zone ID.
      Resolve to an instant when needed, so rule changes apply.
    - Make the zone an attribute of the user, location, or entity, not a
      global constant.
    - Treat tz data as an operational dependency. Keep it current in
      every layer and keep versions aligned.
    - Use the library's zone handling (BP-1). Do not hand-write offsets
      or DST rules.
  - Not a finding:
    - Protocols or contracts defined in UTC or a fixed offset by design.
    - Past events stored as UTC instants.
    - Future events whose requirement is a fixed instant, for example a
      global launch at a stated UTC time.
  - Escalate (NEEDS-HUMAN):
    - Future events with legal or financial effect stored only as UTC
      instants.
    - Events whose spec does not say whether they are tied to local wall
      time or to a fixed instant, for example a meeting across zones.
  - Proposed severity (for the user to decide): HIGH when future
    appointments, deadlines, billing, or expiries shift after a rule
    change, or when a hardcoded offset is wrong on a core path. MEDIUM
    for stale tz data with no update process, and for display. LOW for
    test-only code.
- PA-10: Frozen production zone. Code and data assume the production
  environment's zone setting will never change.
  - Overlap: PA-8 covers code assuming the host is UTC. PA-9 covers the
    served zone and zone rules changing. PA-10 adds what breaks in
    production, especially in data already stored, when the production
    zone setting changes. Merged per the class ledgers.
  - Why it is false:
    - Infrastructure changes: region migration, new base image, cloud
      provider change, managed-service default change, or an ops change
      to `TZ` or the database zone.
    - Multi-region and failover: active-active regions, disaster-recovery
      sites, read replicas, and blue/green fleets can run with different
      zone settings at the same time.
    - A production host on a local zone with DST changes its effective
      offset twice a year. The autumn transition repeats an hour.
  - How it appears in code and data:
    - Timestamps stored without zone or offset (naive values, SQL
      `DATETIME`, Postgres `timestamp without time zone`) written in the
      host or session zone. After a zone change, old and new rows mean
      different instants and cannot be told apart.
    - MySQL `TIMESTAMP` columns read through a changed session zone
      return different wall-clock values for the same stored instant.
    - Logs and audit trails written in local time without offset. Across
      a zone change or DST repeat, entries cannot be ordered or
      correlated.
    - Cron jobs and schedulers running in the host zone move to a
      different real time after the change.
    - Mixed fleets during a rollout or failover: different hosts write
      the same field in different zones.
    - Idempotency keys, file names, or partitions derived from local
      date. They collide or split after the change.
  - What to check:
    - Columns, fields, and log formats that carry no zone or offset.
    - Whether the zone in effect when old data was written is recorded
      anywhere.
    - Scheduler and cron configuration that relies on the host zone.
    - Multi-region, replica, and failover configs for zone consistency.
  - Fix:
    - Store instants with an explicit offset or in UTC (`timestamptz`, or
      UTC by documented convention), never in the host zone.
    - Write logs in UTC with an explicit offset, in RFC 3339 / ISO 8601
      form.
    - Configure schedulers with an explicit zone (PA-9 for local-time
      jobs).
    - Before any production zone change, inventory zone-less data and
      plan a migration that records the original zone per row or per
      period.
    - Check zone settings in every region, replica, and fleet as part of
      deployment.
  - Not a finding:
    - Zone-less columns that are documented as UTC and written only
      through code that converts to UTC explicitly.
    - Local-time storage that is intentional and carries the zone ID
      next to it (PA-9, future events).
  - Escalate (NEEDS-HUMAN): an existing dataset with zone-less timestamps
    whose original zone cannot be established from code or config.
  - Proposed severity (for the user to decide): HIGH when stored
    timestamps on a core path become ambiguous or shift, or when
    scheduled jobs with financial or legal effect move. MEDIUM for logs
    and audit trails that lose ordering. LOW for test-only code.
- PA-11: Clock correctness assumption. Code assumes the system clock
  always reads the correct current time.
  - Overlap: PA-8 covers a wrong or assumed zone setting. PA-11 covers
    the clock value itself being wrong or jumping. Merged per the class ledgers.
  - Why it is false:
    - Drift: quartz clocks drift by seconds per day without sync.
    - No or broken sync: NTP absent, blocked by a firewall, or
      misconfigured. Sync often completes only after boot, so early
      events carry wrong times.
    - Virtualization: VMs drift or jump after pause, snapshot restore,
      or live migration. Containers inherit the host clock, right or
      wrong.
    - Hardware: devices without a battery-backed clock (many embedded
      and IoT boards) boot at the epoch or a stale saved time. A dead
      CMOS battery does the same.
    - Users: device owners set clocks by hand, wrongly or on purpose,
      for example to extend a trial or cheat a game timer.
    - Hardware clock in local time: dual-boot machines (Windows keeps the
      RTC in local time by default, Linux in UTC) end up hours off.
    - Adjustments jump: a sync step moves the clock forward or backward.
      Providers handle leap seconds differently (smear or step), so
      synced clocks still disagree briefly.
  - How it appears in code:
    - Wall-clock time used for elapsed time, timeouts, retries, and rate
      limits. A backward jump gives negative durations or timeouts that
      never fire. A forward jump fires them at once.
    - Client- or device-supplied timestamps trusted for ordering, expiry,
      audit records, trial periods, or rate limits.
    - Timestamp-based ID generators (Snowflake-style, UUIDv7) with no
      handling for a clock that moves backward. They produce duplicates
      or out-of-order IDs.
    - Token and certificate checks (`exp`, `nbf`, `iat`) with no skew
      tolerance, or with tolerance so large it defeats the check.
    - Licensing or trial logic that trusts the local clock.
    - Timestamps from different machines compared as if they shared one
      clock.
    - No sanity bounds: dates before the software existed, or far in the
      future, are accepted and stored.
  - What to check:
    - Wall-clock APIs used to measure durations: Python `time.time()`,
      JS `Date.now()`, Java `System.currentTimeMillis()`, .NET
      `DateTime.Now`/`UtcNow` subtraction.
    - Any authoritative decision based on a timestamp from a client.
    - ID generators that read the clock.
    - Leeway settings in token and certificate validation.
    - Infrastructure config for time sync (chrony, systemd-timesyncd,
      cloud time services) where it is in scope.
  - Fix:
    - Measure elapsed time with a monotonic clock: Python
      `time.monotonic()`, JS `performance.now()`, Java
      `System.nanoTime()`, Go `time.Since` (uses the monotonic reading),
      .NET `Stopwatch`.
    - Assign authoritative timestamps on the server. Keep client time
      only as a separate, untrusted field.
    - Make ID generators detect backward jumps and wait or fail.
    - Allow a small, explicit skew leeway in token checks.
    - Run time sync and monitor offset. Reject or flag timestamps outside
      sane bounds.
  - Not a finding:
    - Showing a user their own device time for their own reference.
    - Client time recorded as a labeled, untrusted extra field.
  - Escalate (NEEDS-HUMAN): security or billing decisions (tokens,
    licenses, trials, audit trails) that depend on a clock whose sync
    status cannot be established from the review unit.
  - Proposed severity (for the user to decide): CRITICAL when a
    client-controlled clock decides authorization, payment, or token
    validity. HIGH for wall-clock timeouts and ID generators on core
    paths. MEDIUM for logs and analytics. LOW for test-only code.
- PA-12: Bounded clock error assumption. Code assumes that even when the
  system clock is wrong, it is only slightly wrong.
  - Overlap: PA-11 covers clocks that are wrong or jump. PA-12 covers
    errors of hours to decades, and the damage that only large errors
    cause. Merged per the class ledgers.
  - Why it is false:
    - Boot defaults: devices without a working RTC start at the Unix
      epoch, a firmware default such as 2000-01-01, or the firmware build
      date.
    - Bad RTC reads and dead batteries can give dates decades in the
      future or past.
    - GPS week-number rollover: the GPS week counter wraps every 1024
      weeks (about 19.7 years). Rollovers fell on 1999-08-22 and
      2019-04-07. Affected receivers jumped back by nearly 20 years.
    - VM restore from an old snapshot sets the clock back weeks or
      months until sync catches up.
    - Manual mistakes and test settings: a wrong year typed by hand, or
      a deliberately future-dated test clock left in place.
    - Sync can refuse or crawl: ntpd by default exits when the offset is
      over its 1000 s panic threshold unless started with `-g`. chrony
      slews by default (up to about 83 ms per second), so a large
      offset takes a long time to remove unless `makestep` is set.
  - How it appears in code (damage specific to large errors):
    - Retention and cleanup jobs: with the clock far in the future,
      every record is past its retention period and the job deletes
      everything.
    - Expiry sweeps: sessions, tokens, licenses, and caches all expire
      at once (clock ahead) or never expire (clock behind).
    - Catch-up schedulers that run every missed occurrence after a
      forward jump, causing job storms or duplicate billing.
    - Sync cursors and high-water marks (`max(updated_at)`) set from a
      far-future clock. After the clock is corrected, new records sort
      below the mark and are never synced or replicated.
    - Time-based IDs generated far in the future. After correction, new
      IDs sort before old ones permanently.
    - TLS fails outright (certificates not yet valid or expired), so the
      device cannot reach an HTTPS time source to fix itself.
    - Tokens signed with a wrong clock are already expired, or valid for
      decades.
  - What to check:
    - Destructive or bulk actions driven by "now": purges, expiry
      sweeps, archival, account deactivation.
    - Missed-run handling in schedulers.
    - Cursors, watermarks, and IDs derived from the local clock.
    - Plausibility checks on "now" before acting on it.
    - Time-sync configuration for large offsets, where in scope.
  - Fix:
    - Check "now" against a floor (build time, or the last known good
      time persisted by the program) and a ceiling. Never accept a
      clock earlier than the persisted floor.
    - Refuse, or cap per run, destructive time-based actions when the
      clock is implausible or has just jumped.
    - Bound catch-up: skip or coalesce missed runs by policy.
    - Use server-assigned sequence numbers or logical clocks for sync
      cursors instead of wall-clock timestamps.
    - Configure sync to step large offsets at startup (`ntpd -g`,
      chrony `makestep`). Consider authenticated time (NTS, RFC 8915).
  - Not a finding:
    - Offline tools where a wrong clock affects only display.
    - Test harnesses that set a fake clock on purpose.
  - Escalate (NEEDS-HUMAN): destructive, financial, or security actions
    driven by the clock on hosts or devices whose sync cannot be
    established from the review unit.
  - Proposed severity (for the user to decide): CRITICAL when a clock
    jump can trigger mass deletion, mass expiry, or an authorization
    bypass. HIGH for sync cursors, IDs, and catch-up billing on core
    paths. MEDIUM for logs and display. LOW for test-only code.
- PA-13: Constant clock error assumption. Code assumes a wrong clock is
  wrong by a fixed amount, so one measured correction stays valid.
  - Overlap: PA-11 covers wrong and jumping clocks. PA-12 covers large
    errors. PA-13 covers the error changing over time, and code that
    measures it once. Merged per the class ledgers.
  - Why it is false:
    - Drift rate varies with temperature, age, and load. Unsynced error
      grows over time and not at a steady rate.
    - Sync changes the error: a step changes it at once, a slew changes
      it gradually, and frequency corrections change the rate itself.
    - Sleep, suspend, VM pause, and live migration add jumps on resume.
    - Leap-second smearing shifts a smeared clock gradually against an
      unsmeared one over the smear window.
    - Each machine drifts differently, so the skew between two machines
      also changes.
    - A measured client-to-server offset includes network delay, which
      varies per request and is often asymmetric.
  - How it appears in code:
    - A client-to-server offset (`serverTime - Date.now()`) measured
      once at login or startup and applied for the rest of the session.
    - Countdowns, auction end times, and game timers driven by that
      one-time offset.
    - Offsets measured without accounting for round-trip time.
    - Whole log files "corrected" after the fact with one global offset.
    - Distributed leases, locks, or consensus timeouts that assume a
      fixed skew between nodes instead of a bounded drift rate.
    - Hardcoded offsets between time scales that change when leap
      seconds are added: TAI-UTC (37 s since 2017) and GPS-UTC (18 s
      since 2017).
  - What to check:
    - Cached clock offsets and when, if ever, they refresh.
    - Offset estimation code: does it use round-trip timing?
    - Lease and lock code: what skew or drift does it assume?
    - Literal time-scale offsets (18, 19, 37 seconds) near time code.
  - Fix:
    - Refresh offsets periodically. Estimate with round-trip timing
      (NTP-style midpoint) and keep an error bound with the estimate.
    - Enforce deadlines on the server. Client offsets drive display
      only.
    - Design leases and locks for a bounded drift rate and explicit
      uncertainty, and measure elapsed time with a monotonic clock
      (PA-11).
    - Correct logs per segment between sync points, not with one global
      offset.
    - Read time-scale offsets from a maintained leap-second table (for
      example IERS data or the tzdata `leap-seconds.list`), not
      literals.
  - Not a finding:
    - A one-time offset used only for display, refreshed periodically,
      with the server enforcing the real deadline.
    - Offsets between time scales that are genuinely fixed, such as
      TAI-GPS (19 s).
  - Escalate (NEEDS-HUMAN): distributed correctness (leases, locks,
    leader election) that depends on clock-skew bounds the review unit
    does not state.
  - Proposed severity (for the user to decide): HIGH when lock or lease
    safety, or deadline enforcement, relies on a fixed offset. MEDIUM for
    client countdowns and log correction. LOW for test-only code.
- PA-14: Client-server clock agreement. Code assumes the client and the
  server clocks read the same time.
  - Overlap: PA-11 covers trusting client timestamps for authority.
    PA-13 covers measuring the offset once. PA-14 adds the defects that
    come from comparing values across the client-server boundary. Merged per the class ledgers.
  - Why it is false:
    - Client and server have independent clocks, different sync sources
      or none, and different drift (PA-11 to PA-13).
    - Users set device clocks by hand. Mobile devices may take network
      time or not.
    - Client and server usually sit in different zones. Even when the
      instants agree, local wall-clock values differ (PA-8).
  - How it appears in code:
    - Clients comparing a server-issued absolute expiry (token `exp`,
      session end) with the local clock. Results: early logout, refresh
      loops, or tokens never refreshed.
    - Absolute expiry sent where a relative one works: cookie `Expires`
      instead of `Max-Age`, HTTP `Expires` instead of
      `Cache-Control: max-age`. The browser evaluates the absolute value
      against its own clock.
    - Signed requests stamped with client time that the server checks
      for freshness. AWS S3 rejects with `RequestTimeTooSkewed` when the
      difference exceeds 15 minutes.
    - TOTP codes rejected because the device clock is off by more than
      the server's accepted step window.
    - Client-generated `createdAt` stored as authoritative. Chat messages
      and events then sort out of order.
    - Last-write-wins conflict resolution on client timestamps. A device
      with a fast clock overwrites newer data.
    - Clients sending absolute time filters (`since = Date.now() - 1h`)
      that the server applies to its own data.
    - The same "date must be in the future" rule checked on client and
      server giving different results near the boundary.
    - Relative-time labels ("5 minutes ago") computed from a server
      timestamp and the client clock, showing negative or future values.
  - What to check:
    - Any comparison between a server-issued time and the client clock.
    - Absolute expiry fields in cookies, caches, and tokens where a
      relative duration is available.
    - Client timestamps used for ordering, conflict resolution, or
      filtering on the server.
    - Skew tolerance in request signing and TOTP validation.
  - Fix:
    - Send relative durations (`expires_in`, `Max-Age`, `max-age`) and
      track them on the client with a monotonic clock (PA-11).
    - Keep the server authoritative for ordering, expiry, and
      validation. Assign timestamps or sequence numbers on the server.
    - Where the client must reason about server time, send server time
      in each response (for example the HTTP `Date` header) and estimate
      the offset with an error bound (PA-13).
    - Allow an explicit skew window in signing and TOTP checks, and use
      SDK clock-skew correction where available.
    - Clamp relative-time labels so they never show negative values.
  - Not a finding:
    - Purely local apps, or reminders a user sets on their own device in
      device time.
    - Client time stored as a labeled, untrusted extra field (PA-11).
  - Escalate (NEEDS-HUMAN): offline-first apps where the client clock is
    the only time source for records that later sync. The ordering and
    conflict design (for example hybrid logical clocks) needs a decision.
  - Proposed severity (for the user to decide): CRITICAL when the client
    clock decides authorization (PA-11). HIGH for refresh loops, TOTP
    lockouts, and data loss from last-write-wins on client time. MEDIUM
    for display labels and filters. LOW for test-only code.
- PA-15: Bounded client-server skew assumption. Code assumes that client
  and server clocks, even when they differ, are always close.
  - Overlap: PA-12 covers large clock errors on one machine. PA-14 covers
    client-server comparisons. PA-15 adds the defects that appear when
    client-server skew is large. Merged per the class ledgers.
  - Why it is false:
    - Client clocks can be hours, days, or years off for every reason in
      PA-12, and users change them on purpose.
    - Wrong zone, right wall clock: a user sets the clock to show the
      correct local time but with the wrong zone selected. The device's
      UTC instant is then off by whole hours (or 30 or 45 minutes).
    - Devices that were offline for a long time sync late or never.
  - How it appears in code:
    - Fixed skew tolerances (for example 5 minutes) with no recovery path.
      Users with large skew fail every request with no explanation.
    - Offset estimation that clamps or discards large measurements as
      outliers, so large skew is never corrected.
    - Clients scheduling server-relevant actions (polls, submissions,
      reminders) at absolute times computed with the local clock. They
      run hours early or late.
    - Client caches holding absolute server expiries that never expire or
      always look expired, causing request storms.
    - Client-generated time-based IDs (UUIDv7) or timestamps far in the
      past or future, accepted and indexed by the server.
    - Servers storing client timestamps from 1970 or decades ahead,
      corrupting analytics, ordering, and retention (PA-12).
    - Offline queues replayed later with far-off client timestamps.
    - Rate limits or replay windows keyed on client time.
  - What to check:
    - Skew tolerances and what happens when a request falls outside them.
    - Offset estimation code: are large values clamped or dropped?
    - Server validation of client-supplied timestamps and IDs.
    - Client-side absolute scheduling and cache expiry.
  - Fix:
    - Detect large skew explicitly, for example by comparing the client
      clock with the server's HTTP `Date` header.
    - Surface an actionable error ("device clock is about 3 hours off")
      instead of a silent failure, or correct automatically using the
      SDK's skew correction where available.
    - Bound client timestamps on the server: reject or flag values
      outside a plausible window, and always store the server receive
      time alongside.
    - Never clamp or discard a large offset measurement without
      handling it.
    - Use relative durations and server-authoritative time (PA-14).
  - Not a finding:
    - Narrow tolerance windows required by security design (request
      signing, replay protection) when the failure path tells the user or
      corrects the skew.
  - Escalate (NEEDS-HUMAN): security windows where widening tolerance for
    skewed clients weakens replay protection. The trade-off needs a
    decision.
  - Proposed severity (for the user to decide): HIGH when users are
    locked out of a core flow with no recovery, or when far-off client
    timestamps corrupt core data. MEDIUM for caches, scheduling, and
    analytics. LOW for test-only code.
- PA-16: Constant client-server skew assumption. Code assumes that when
  client and server clocks differ, the difference stays the same.
  - Overlap: PA-13 covers a single clock's error changing over time,
    including a client offset measured once at login. PA-16 adds causes
    and defects specific to the client-server pair. Merged per the class ledgers.
  - Why it is false:
    - Either side's clock changes: sync corrections, drift, a user
      editing the device clock mid-session, or a device changing zone
      and time source when it changes networks.
    - Sleep and resume: mobile apps backgrounded and laptops suspended
      come back with a different offset.
    - "The server" is often a fleet. Behind a load balancer, each request
      can reach a different host with its own clock, so the measured
      offset jumps between requests.
    - Cached responses: a CDN or HTTP cache serves a stored response with
      its original `Date` header. An offset computed from it is off by
      the response's `Age`.
  - How it appears in code:
    - An offset measured once and reused for the whole session (PA-13),
      or persisted (for example in `localStorage`) and reused in later
      sessions.
    - No re-measurement after resume, tab visibility change, or network
      change.
    - Offset computed from a `Date` header on a cacheable response,
      without accounting for `Age`.
    - A single offset assumed valid for every server in a fleet.
    - Each new measurement accepted as-is, so offsets swing with network
      delay and host changes.
  - What to check:
    - Where the client offset is stored, how long it lives, and what
      triggers a refresh.
    - Which response the offset is measured from, and whether it can be
      cached.
    - Whether server hosts in the fleet are themselves kept in sync.
  - Fix:
    - Re-measure periodically and on resume, visibility change, and
      network change. Do not persist offsets across sessions.
    - Measure against an uncacheable time endpoint
      (`Cache-Control: no-store`), or subtract `Age`.
    - Keep fleet clocks synced and monitored, or have one authoritative
      time source for the client to measure against.
    - Filter measurements, for example by keeping the samples with the
      lowest round-trip time (NTP-style), and keep an error bound.
    - Keep deadlines enforced on the server (PA-13, PA-14).
  - Not a finding:
    - Display-only offsets refreshed on resume, with server enforcement
      of the real deadline.
  - Escalate (NEEDS-HUMAN): client features (auctions, timed exams,
    trading cut-offs) whose fairness depends on client-side offset
    accuracy, where the required accuracy is not stated.
  - Proposed severity (for the user to decide): HIGH when deadline or
    fairness enforcement on a core path depends on a client offset
    measured once or persisted. MEDIUM for display countdowns and
    analytics. LOW for test-only code.
- PA-17: Shared client-server zone assumption. Code assumes the client
  and the server use the same time zone.
  - Overlap: PA-8 covers code assuming the host is UTC. PA-14 covers
    client-server clock comparisons. PA-17 adds defects from values that
    cross the client-server boundary between different zones. Merged per the class ledgers.
  - Why it is false:
    - Users are spread across zones. Servers usually run in UTC or in the
      operator's zone.
    - Users travel. A VPN changes the apparent location but not the
      device zone.
    - Privacy settings can report a different zone: Firefox with
      `privacy.resistFingerprinting` and Tor Browser report UTC.
    - A user's profile zone and current device zone can differ.
    - Multi-region server fleets can differ from each other (PA-10).
  - How it appears in code:
    - Date-times sent without an offset in either direction. JS parses
      `"2026-07-01T09:00"` as client local time (PA-8, verified). A
      server parses a naive string as server local time.
    - Date-only values sent as instants. A date picked as 2026-07-01 in
      Tokyo, sent with `toISOString()`, arrives as
      `2026-06-30T15:00:00.000Z` and is stored as June 30. A server
      date `"2026-07-01"` shown in Los Angeles displays as 6/30/2026
      (both verified).
    - "Today" and day boundaries computed in the server zone for
      user-facing logic: streaks, "due today", daily limits resetting at
      server midnight.
    - Server-side rendering formats in the server zone. Client hydration
      formats in the client zone. Output flickers or the hydration fails.
    - Zone-less form inputs (`<input type="datetime-local">`, date
      pickers) interpreted by the server in its own zone.
    - Emails, notifications, and exports rendered on the server in the
      server zone with no zone label.
    - Report filters built from the client's local date but applied to
      UTC days on the server.
  - What to check:
    - Wire formats for every date and time crossing the boundary: is an
      offset or zone present, and is a date-only value sent as a date?
    - Where the user zone comes from, whether it is stored, and whether
      server code uses it.
    - Server-side "today" and day-boundary calculations for user-facing
      features.
    - Server-rendered dates and times: zone used and zone labeled.
  - Fix:
    - Send instants with an explicit offset or `Z` (RFC 3339).
    - Send date-only values as date strings (`YYYY-MM-DD`), never as
      instants.
    - Send local wall-clock intent as local date-time plus IANA zone ID
      (PA-9).
    - Capture the user zone explicitly (for example
      `Intl.DateTimeFormat().resolvedOptions().timeZone`), store it on the
      profile, and let the user change it.
    - Compute user-facing day boundaries in the user's zone on the
      server.
    - Render server-side output in the user's stored zone and label it,
      or defer formatting to the client.
  - Not a finding:
    - Service-to-service traffic where both sides are UTC by explicit
      contract.
  - Escalate (NEEDS-HUMAN): business boundaries ("daily limit resets at
    midnight", "order by end of day") where the spec does not say whose
    zone applies: the user's, the merchant's, or a legal jurisdiction's.
  - Proposed severity (for the user to decide): HIGH when dates shift on
    a core path (birthdays, due dates, bookings, deadlines). MEDIUM for
    display, rendering mismatches, and reports. LOW for test-only code.
- PA-18: Clock range assumption. Code assumes "now" always falls in a
  narrow, recent range, never in the distant past or far future.
  - Overlap: PA-12 covers how clocks end up far off and the damage to
    retention, expiry, and sync. PA-18 adds range limits: what overflows,
    wraps, or crashes when "now", or "now" plus a duration, reaches an
    extreme. Merged per the class ledgers.
  - Why it is false:
    - Clocks reach extremes by accident (PA-12: epoch boots, GPS
      rollover, bad RTC reads) and on purpose: time-travel testing,
      Y2038 readiness checks, and users or attackers setting clocks far
      ahead or behind to extend trials or reuse expired credentials.
    - Real dates also approach range limits: 30-year mortgages,
      pensions, long certificates, and multi-decade retention already
      reach past 2038 today.
  - Range limits (verified where marked):
    - Signed 32-bit Unix seconds: 1901-12-13 20:45:52 to 2038-01-19
      03:14:07 UTC (verified). Unsigned 32-bit: to 2106.
    - NTP 32-bit seconds since 1900 roll over on 2036-02-07 06:28:16 UTC
      (verified).
    - MySQL `TIMESTAMP`: 1970-01-01 00:00:01 to 2038-01-19 03:14:07 UTC.
      MySQL `DATETIME`: years 1000 to 9999.
    - SQL Server `datetime`: from 1753. .NET `DateTime`: years 1 to 9999.
    - Python `datetime`: years 1 to 9999. `datetime(9999,12,31) +
      timedelta(days=1)` raises OverflowError (verified).
    - JS `Date`: +/-8.64e15 ms, up to +275760-09-13. One millisecond more
      gives an invalid date (`NaN`, verified).
    - Postgres `timestamp`: 4713 BC to 294276 AD.
    - File systems and formats: FAT 1980 to 2107. Classic Mac HFS+ 1904
      to 2040. Windows FILETIME counts from 1601. Excel has no dates
      before its 1900 or 1904 epoch (PA-4). RFC 3339 allows years 0000
      to 9999 only.
    - Some platforms reject negative (pre-1970) epoch values, for example
      the Microsoft C runtime's `localtime`.
  - How it appears in code:
    - 32-bit fields or columns for epoch seconds, including in binary
      protocols, file formats, and embedded firmware.
    - MySQL `TIMESTAMP` used for values that can pass 2038.
    - Sentinel values: `9999-12-31` or `MAX_DATE` for "never expires",
      then arithmetic on them overflows. `0` or `1970-01-01` for "unset",
      which collides with a real "now" on an epoch-booted device.
    - `now + duration` near a range end raising or wrapping with no
      handling.
    - Parsers and formatters that assume four-digit, positive years.
    - Code that rejects or mishandles pre-1970 dates (birth dates,
      historical records).
  - What to check:
    - Width and type of every stored or transmitted time value.
    - Sentinel dates and arithmetic performed on them.
    - Behavior of "now"-based arithmetic at 1970, 2036-02-07,
      2038-01-19, and year 9999.
    - Handling of negative epoch values and years outside 1000 to 9999.
  - Fix:
    - Use 64-bit epoch values and wide database types. Do not use MySQL
      `TIMESTAMP` for values that can reach 2038.
    - Use explicit nullable fields or flags for "never" and "unset"
      instead of sentinel dates. If sentinels remain, saturate arithmetic
      instead of overflowing.
    - Apply plausibility bounds to "now" (PA-12).
    - Test with the clock set to each range boundary above.
  - Not a finding:
    - A documented, validated domain range narrower than the type range,
      for example birth dates after 1900, enforced at input.
  - Escalate (NEEDS-HUMAN): long-lived values (loans, pensions,
    certificates, archival retention) when the full storage and transport
    path's range cannot be established from the review unit.
  - Proposed severity (for the user to decide): CRITICAL when storage
    cannot represent values the system already writes, for example a
    2050 loan maturity in a MySQL `TIMESTAMP` column. HIGH for 32-bit
    time on core paths and sentinel overflow. MEDIUM for parsers and
    display. LOW for test-only code.
- PA-19: Unbounded time assumption. Code assumes time values have no
  starting point and no limit, so any date can be represented and
  converted.
  - Overlap: PA-18 lists representation limits and what fails when "now"
    reaches them. PA-19 covers the beginnings themselves: epochs, calendar
    starts, era numbering, and the start of zone history. Merged per the class ledgers.
  - Why it is false:
    - Every representation counts from an epoch and stops at a maximum
      (ranges in PA-18).
    - Epochs differ between systems (verified offsets from Unix epoch
      where marked):
      - Unix and Java: 1970-01-01.
      - NTP: 1900-01-01.
      - GPS: 1980-01-06 (315964800 s after Unix, verified).
      - Apple Cocoa (`NSDate` reference date): 2001-01-01 (978307200 s
        after Unix, verified).
      - Windows FILETIME: 1601-01-01. .NET ticks: 0001-01-01.
      - Excel: 1899-12-30 (1900 system, PA-4) or 1904-01-01.
    - Calendars have starts and gaps. The historical AD/BC count has no
      year 0: 1 BC is followed by AD 1. ISO 8601 astronomical numbering
      has year 0 = 1 BC and year -1 = 2 BC. The Gregorian calendar began
      in 1582. Earlier dates in most libraries are proleptic Gregorian
      and differ from Julian records (PA-2).
    - Zone history has a start. Before standard time, places used local
      mean time (LMT). `America/New_York` before 1883-11-18 is
      -04:56:02 (verified). tzdata is reliable mainly from 1970.
    - Zone rules have no known end: future rules are projections (PA-9).
  - How it appears in code:
    - Values converted between systems with the wrong epoch, or a
      hand-typed epoch constant. An Apple reference-date value read as
      Unix time is 31 years early.
    - BC and year-0 handling: astronomical and historical year numbers
      mixed. Java `uuuu` prints 44 BC as `-0043`, while `yyyy` with `G`
      prints `0044 BC` (verified).
    - Java strict parsing with `yyyy` (year of era) and no era field
      fails even for modern dates (verified). Use `uuuu`.
    - Historical local times converted with modern rules, or with LMT
      offsets nobody expected. Passing a pytz zone as `tzinfo=` to the
      `datetime` constructor attaches the zone's first (LMT) offset, a
      library misuse under BP-1.
    - Postgres `infinity` and `-infinity` timestamps reaching application
      code. Drivers map them to extreme values or raise errors.
    - Iteration over an "unbounded" range with no termination at the
      type's maximum.
    - Historical, genealogical, or astronomical data accepted into types
      that cannot hold it (PA-18).
  - What to check:
    - Epoch constants and conversions between platforms and formats.
    - Year numbering for BC dates and year 0, and the format patterns
      used.
    - Handling of dates before 1970, before 1883 (pre-standard time), and
      before 1582.
    - Database special values (`infinity`) and how drivers map them.
  - Fix:
    - Use library conversions with named epochs, not literal constants
      (BP-1).
    - Pick one year-numbering scheme. Use era-aware formatting where
      users see BC dates. In Java, use `uuuu` unless era is formatted.
    - Choose types whose range covers the domain, and validate input
      against it.
    - Handle `infinity` explicitly, or forbid it in the schema.
    - For historical records, keep the original date text and calendar,
      and note the limits of tzdata before 1970.
  - Not a finding:
    - Modern-date applications whose inputs are validated to a modern
      range.
  - Escalate (NEEDS-HUMAN): historical, genealogical, legal-archive, or
    astronomical data where the source calendar (Julian or Gregorian) or
    year-numbering scheme is not stated.
  - Proposed severity (for the user to decide): HIGH when wrong epochs or
    year numbering corrupt stored records on a core path. MEDIUM for
    historical display and parsing. LOW for test-only code.
- PA-20: Uniform clock rate assumption. Code assumes a minute measured on
  the system clock lasts exactly as long as a minute on any other clock.
  - Overlap: PA-13 covers changing offsets between clocks. PA-20 covers
    the length of a measured interval: clocks tick at different rates,
    and some intervals are stretched, skipped, or not counted. Merged per the class ledgers.
  - Why it is false:
    - Drift: every oscillator runs slightly fast or slow, so minutes on
      two machines differ (PA-13).
    - Slewing: sync corrects error by speeding up or slowing down the
      clock. ntpd slews at up to 500 ppm. chrony's default maximum is
      about 83,000 ppm (8.3%), so a "minute" can last about 55 to 65
      real seconds during a large slew.
    - Leap smearing: Google and AWS spread a leap second over many hours
      (Google: 24 hours, noon to noon UTC). Each smeared second is
      slightly longer than a UTC second. Mixing smeared and unsmeared
      sources gives clocks that disagree during the smear.
    - Leap seconds: a UTC minute with a leap second has 61 seconds (59
      for a negative leap second). POSIX time hides this by repeating a
      second.
    - Sleep and suspend: monotonic clocks differ on whether they count
      suspended time. Linux `CLOCK_MONOTONIC` excludes suspend, and
      `CLOCK_BOOTTIME` includes it. macOS `mach_absolute_time` stops
      during sleep.
    - Throttled timers: browsers throttle timers in background tabs (at
      most once per second, and Chrome throttles long-hidden pages to
      about once per minute). Mobile OSes suspend background apps.
    - Virtualization: guest clocks can tick unevenly under host load or
      during pauses.
    - Relativity (user addition): a minute in orbit, a minute on an
      aircraft at altitude, and a minute at ground level are different
      lengths.
      - Gravity: a clock higher in Earth's gravity field runs faster,
        by about 1.1e-16 per meter of height near the surface. Optical
        clocks have measured a 33 cm height difference (NIST, 2010).
        A clock at Boulder (about 1,650 m) gains about 15 ns per day on
        one at sea level. TAI corrects contributing clocks to a common
        reference surface for this reason.
      - Speed: a moving clock runs slower.
      - GPS satellites (about 20,200 km up, 3.9 km/s): about +45.7
        microseconds per day from gravity and -7.2 from speed, net about
        +38.5 per day. Satellite clocks are deliberately tuned slow
        before launch to compensate.
      - ISS (about 400 km, 7.66 km/s): speed dominates. Net about 25
        microseconds per day slower than the ground (computed).
      - Aircraft at cruise: tens of nanoseconds per day, depending on
        altitude, speed, and direction relative to Earth's rotation.
        Hafele and Keating (1971) flew atomic clocks eastward (lost
        about 59 ns) and westward (gained about 273 ns).
      - Moon: lunar surface clocks gain about 56 microseconds per day on
        Earth clocks. A 2024 US directive tasked NASA with defining a
        Coordinated Lunar Time.
      - Standard time scales exist for this: TT (Terrestrial Time), TCG
        (Geocentric Coordinate Time), TCB and TDB (Barycentric).
  - How it appears in code:
    - Clocks built by counting ticks: `seconds += 1` on every
      `setInterval(..., 1000)` or every loop iteration with `sleep(1)`.
      Throttling and scheduling delay make them run slow.
    - Durations started on one host and ended on another, or measured
      on the client and billed on the server.
    - Precise measurements (benchmarks, SLAs, trading, metering) taken
      with the wall clock during a slew or smear.
    - A monotonic clock with the wrong sleep behavior: a session timeout
      that should count laptop sleep uses a clock that pauses during
      sleep, or the reverse.
    - Parsers and validators that reject second `60`, even though RFC
      3339 allows it for leap seconds.
    - Fleets syncing from a mix of smeared and unsmeared time sources.
    - Space, satellite, aviation, and precision-timing software treating
      an onboard or remote clock's seconds as equal to ground UTC
      seconds, with no relativistic correction or time-scale conversion.
    - Hardcoded relativistic correction constants (for example a
      literal 38.5 microseconds per day) instead of values computed for
      the actual orbit or altitude, or taken from a maintained source.
    - Timestamps from different platforms (spacecraft, aircraft, ground
      stations) compared without naming the time scale of each.
  - What to check:
    - Any elapsed time computed by counting timer callbacks or loop
      iterations.
    - Durations whose start and end come from different clocks.
    - Which monotonic clock is used, and whether it should include
      suspended time.
    - Time-sync sources across a fleet: all smeared, or all unsmeared.
    - Validation of the seconds field.
  - Fix:
    - Measure elapsed time as the difference between two readings of one
      monotonic clock (PA-11), never by counting ticks.
    - Pick the monotonic clock whose sleep behavior matches the
      requirement (for example `CLOCK_BOOTTIME` when suspended time must
      count).
    - Measure each duration on one clock, preferably the authoritative
      server's.
    - Use one smear policy across every host that compares time. Do not
      mix smeared and unsmeared sources.
    - Accept second `60` wherever UTC leap seconds can appear in input.
    - For high-precision domains, use a dedicated time source (for
      example PTP or GPS-disciplined clocks) and a stated accuracy
      budget.
    - In space, satellite, aviation, and precision-timing domains, name
      the time scale of every timestamp (UTC, TAI, TT, GPS time, onboard
      proper time). Convert between scales with a maintained library
      (for example the SOFA/ERFA routines or Astropy's `Time` class)
      instead of hand-written corrections.
  - Not a finding:
    - UI animation and coarse timers where small rate errors are
      acceptable.
    - Relativistic effects in ordinary ground-based software. At tens of
      nanoseconds per day or less, they are far below other error
      sources. Raise them only in space, satellite, navigation, aviation
      timing, or metrology code.
  - Escalate (NEEDS-HUMAN): billing, metering, SLA, or timed-assessment
    durations measured across clocks, or in precision domains, where the
    required accuracy is not stated. Also escalate space, satellite, or
    aviation timing code whose time scale or relativistic handling is
    not stated.
  - Proposed severity (for the user to decide): HIGH when billing,
    metering, or safety timeouts rely on tick counting or on durations
    measured across different clocks. MEDIUM for analytics and UI
    timers. LOW for test-only code.
- PA-21: Bounded clock rate error assumption. Code assumes that even if
  minutes differ between clocks, they differ only slightly.
  - Overlap: PA-20 covers rate differences in general. PA-21 covers large
    rate differences, including clocks and timers that stop, and the
    damage only large differences cause. Merged per the class ledgers.
  - Why it is false:
    - Large slews: chrony can slew by about 8.3%, so a minute can be off
      by about 5 seconds (PA-20).
    - Stopped clocks: across suspend, VM pause, or a debugger breakpoint,
      a clock that excludes sleep (Linux `CLOCK_MONOTONIC`) advances not
      at all while hours pass.
    - Throttled and suspended timers: Chrome can throttle hidden pages
      to about one timer wake-up per minute, so a tick-counted "second"
      lasts a minute (60 times slow). Mobile OSes suspend background apps
      completely.
    - Process pauses: stop-the-world garbage collection (seconds or
      more), CPU starvation and container CPU throttling, swapping, and
      a blocked event loop all delay timers by arbitrary amounts.
    - Deliberate time scaling: simulations, backtesting replays, and
      games run time faster or slower on purpose. Cheat tools such as
      Cheat Engine's speedhack scale a process's time functions.
    - Faulty hardware: bad oscillators, temperature extremes, and
      unsynchronized TSC counters across CPU cores on some older systems
      (Linux then marks the TSC clocksource unstable).
  - How it appears in code:
    - Timers assumed to fire on time: code after `setTimeout(fn, 60000)`
      assumes exactly 60 seconds passed.
    - Distributed locks and leases checked before a pause and acted on
      after it. A GC pause longer than the lease lets two holders write
      at once (described in Martin Kleppmann's 2016 analysis of Redis
      Redlock).
    - Heartbeat and watchdog logic that treats any missed beat as death,
      or treats a resumed process as still healthy.
    - Client-side timing trusted for game rules, timed exams, or
      cooldowns. Speed hacks defeat it.
    - Physics, animation, or simulation stepping by a fixed `dt` per
      frame instead of the measured elapsed time.
    - Tests that call real `sleep` and assert on timing. They fail under
      CI load.
  - What to check:
    - Logic after a timer or sleep that assumes how much time passed.
    - Lease and lock code: is validity rechecked right before a side
      effect, and are writes fenced?
    - Client-side timing that decides outcomes.
    - Fixed time steps in loops.
    - Tests that depend on real-time sleeps.
  - Fix:
    - Read a monotonic clock in each callback and act on the measured
      elapsed time, not the requested delay.
    - Protect writes guarded by leases with fencing tokens, and recheck
      lease validity immediately before any side effect.
    - Detect pauses (a gap between consecutive monotonic readings larger
      than expected) and handle them: recheck sessions, leases, and
      deadlines on resume.
    - Keep timing that decides outcomes on the server.
    - Use the measured elapsed time per step, clamped to a maximum.
    - Use controllable fake clocks in tests instead of real sleeps.
  - Not a finding:
    - UI timers and animations where a stall only delays display.
    - Simulations that scale time on purpose and document it.
  - Escalate (NEEDS-HUMAN): distributed locks or leases without fencing,
    where the maximum pause the design tolerates is not stated.
  - Proposed severity (for the user to decide): CRITICAL when a pause can
    break lock or lease safety and let two writers corrupt data. HIGH for
    client-side timing that decides game, exam, or billing outcomes.
    MEDIUM for watchdogs and simulations. LOW for test-only code.
- PA-22: Bounded gap assumption. Code assumes the real time between two
  consecutive clock readings, or across one measured "minute", can never
  exceed an hour.
  - Overlap: PA-21 covers clocks that slow or stop. PA-22 covers
    unbounded real-time gaps between consecutive steps of a program, and
    the overflow and staleness bugs that follow. Merged per the class ledgers.
  - Why it is false:
    - Suspension: laptops closed over a weekend, hibernation, mobile apps
      backgrounded for weeks, `SIGSTOP`, and a debugger left paused.
    - Snapshots: VMs restored from snapshots, and containers restored
      with checkpoint/restore tools (CRIU), resume months later in
      the middle of execution.
    - Serverless freezing: AWS Lambda and similar platforms freeze the
      execution environment between invocations and reuse it later.
      Module-level state survives with whatever time it captured.
    - Long-running work: batch jobs, migrations, and streams run for
      hours or days, across midnights and month-ends.
    - On resume, the wall clock jumps far forward, while a sleep-excluding
      monotonic clock shows almost no elapsed time (PA-20).
  - How it appears in code:
    - "Now" cached at module load or startup and reused, especially in
      serverless handlers (`const now = Date.now()` at module scope).
    - A deadline or token validity checked before a long `await`, sleep,
      or suspension, then acted on after it.
    - "Today" computed once at the start of a job that runs past
      midnight.
    - In-memory TTL caches and sessions that assume they are checked
      often.
    - Overflow on large elapsed values:
      - Node `setTimeout` with a delay of 2^31 ms (about 24.8 days) or
        more fires after 1 ms, with only a warning (verified).
      - Windows `GetTickCount` (32-bit milliseconds since boot) wraps
        every 49.7 days.
      - Large nanosecond durations truncated into 32-bit milliseconds.
    - Rates or averages divided by elapsed time: huge gaps give rates
      near zero, and a sleep-excluding clock can give zero elapsed time
      (division by zero).
  - What to check:
    - Time values captured at module, class, or startup scope.
    - Time-based checks separated from their action by an `await`,
      sleep, queue, or retry.
    - "Today" or day boundaries in long-running jobs.
    - Timer delays and tick counters: width and maximum.
    - Division by elapsed time without a zero or size guard.
  - Fix:
    - Read the clock again after every suspension point, and recheck
      validity immediately before acting.
    - Never cache "now" at module scope. In serverless code, read it per
      invocation.
    - In long jobs, either recompute day boundaries as the job runs, or
      fix one documented "as-of" time on purpose.
    - Saturate or clamp large elapsed values. Use 64-bit counters.
    - Schedule long delays with a persistent scheduler, or chain timers
      shorter than the platform maximum.
    - Use a sleep-including clock or the wall clock where real elapsed
      time matters, such as session expiry after resume (PA-20).
    - Revalidate on resume events (page visibility, OS power
      notifications).
    - Guard division by elapsed time.
  - Not a finding:
    - A single "as-of" time fixed on purpose for consistency, such as a
      report snapshot, when documented.
  - Escalate (NEEDS-HUMAN): long-running jobs that cross midnight or a
    period boundary where the spec does not say whether the job's start
    date or the current date applies.
  - Proposed severity (for the user to decide): HIGH when a stale "now"
    or overflowed timer drives expiry, authorization, billing, or mass
    actions on a core path. MEDIUM for caches, metrics, and reports. LOW
    for test-only code.
- PA-23: Second-resolution assumption. Code assumes one second is the
  smallest unit of time it needs to represent or will receive.
  - Why it is false:
    - Platforms carry finer units: milliseconds (JS `Date`, Java
      `currentTimeMillis`), microseconds (Python `datetime`, Postgres,
      MySQL `DATETIME(6)`), 100-nanosecond ticks (.NET), and nanoseconds
      (Go `time`, Java `Instant`, Linux `timespec`).
    - Many events happen within the same second.
    - Wire formats carry fractions. RFC 3339 allows any number of
      fractional-second digits.
    - Systems disagree on the unit of a bare number: Unix time and JWT
      claims use seconds, JS and Java use milliseconds.
  - How it appears in code:
    - Unit confusion between seconds and milliseconds (verified):
      - JS `new Date(seconds)` lands in January 1970
        (`new Date(1782900000)` is 1970-01-21).
      - Python `datetime.fromtimestamp(milliseconds)` raises "year 58467
        is out of range".
    - Second-precision storage: MySQL `DATETIME` and `TIMESTAMP` default
      to 0 fractional digits, and MySQL rounds (not truncates) by default.
      23:59:59.6 is stored as 00:00:00 the next day.
    - Ordering or uniqueness by second-level timestamps: ties make
      "latest" ambiguous. Keyset pagination on a timestamp without a
      tie-breaker skips or repeats rows.
    - IDs or file names built from second timestamps collide
      (`int(time.time())` as an ID, `backup-20260701-0900.tar`).
    - Precision lost on round trips between layers (ns in Go or Java,
      us in Postgres and Python, ms in JS). Values that should match
      compare unequal after a round trip, breaking optimistic-locking
      version checks and cache keys.
    - Floating-point epochs:
      - float32 epoch seconds near 1.78e9 are spaced 128 seconds apart
        (verified).
      - float64 seconds lose sub-microsecond detail.
      - Nanosecond epochs in JSON exceed 2^53 and lose precision when
        parsed as JS numbers (verified).
    - Durations measured with second resolution read as zero, then used
      as a divisor (PA-22).
  - What to check:
    - The unit of every numeric time value at each boundary: API fields,
      database columns, JWT claims, config values.
    - Fractional-second precision of each column and format, and whether
      writes round or truncate.
    - Uniqueness, ordering, and pagination keyed on timestamps alone.
    - Float types holding epoch values.
    - Equality comparisons of timestamps that crossed a layer boundary.
  - Fix:
    - Choose and document the precision for each field end to end. Use
      types that hold it (`DATETIME(6)`, `timestamptz`, 64-bit integers).
    - Put the unit in the field name (`created_at_ms`) or use typed
      durations and instants (Go `time.Duration`, Java `Duration`/
      `Instant`).
    - Never use a timestamp alone as a unique ID. Add a tie-breaker
      (ID or sequence) to ordering and pagination.
    - Truncate explicitly to the target precision before writing, or set
      MySQL's `TIME_TRUNCATE_FRACTIONAL` mode, so values never round into
      the next second, day, or period.
    - Compare timestamps at a stated common precision.
    - Do not store epochs as floats. Send high-precision values as RFC
      3339 strings or as integer strings in JSON.
  - Not a finding:
    - Second precision where it is the documented requirement and no
      ordering, uniqueness, or arithmetic depends on finer detail.
  - Escalate (NEEDS-HUMAN): audit, legal, trading, or event-sourcing
    records where the required precision is not stated.
  - Proposed severity (for the user to decide): HIGH for unit confusion
    on core paths, ID collisions that overwrite data, pagination that
    skips records, and rounding that moves a value into the next day or
    period. MEDIUM for ordering ambiguity in logs and analytics. LOW for
    test-only code.
- PA-24: Millisecond-resolution assumption. Code assumes one millisecond
  is the smallest unit of time it needs to represent or will receive.
  - Overlap: PA-23 covers resolution and unit confusion in general.
    PA-24 adds what breaks at the millisecond boundary specifically.
    Merged per the class ledgers.
  - Why it is false:
    - Sources finer than milliseconds: microseconds (Postgres, Python
      `datetime`, BigQuery `TIMESTAMP`, Spark), nanoseconds (Go, Java
      `Instant`, Linux, Protobuf `Timestamp`, pandas), and Parquet time
      types in ms, us, or ns.
    - Millisecond-only sinks sit next to them: JS `Date`, Java
      `java.util.Date`, MongoDB BSON dates, Kafka record timestamps, and
      Elasticsearch `date` (it offers `date_nanos` separately).
    - Clocks can be coarser than their unit: Windows' default system
      timer ticks about every 15.6 ms, so `Sleep(1)` and some `DateTime`
      readings move in about 15.6 ms steps. Browsers deliberately coarsen
      `performance.now()` (a Spectre mitigation), by an amount that
      depends on browser and cross-origin isolation.
    - Many operations take less than a millisecond.
  - How it appears in code:
    - Values truncated on the way through a millisecond layer (JS
      client, MongoDB, Kafka), then compared with the microsecond or
      nanosecond original. Optimistic-concurrency checks that send a
      timestamp back from a JS client fail every time against a
      microsecond Postgres column.
    - Parsers that handle only three fractional digits:
      - JS `new Date("...00.123456Z")` silently drops digits past
        milliseconds (verified).
      - Java `SimpleDateFormat` with `SSS` reads `.123456` as 123,456
        milliseconds and adds about 2 minutes: `09:00:00.123456` becomes
        `09:02:03.456` (verified).
    - Durations under a millisecond recorded as 0. Latency metrics,
      percentiles, and rates are wrong.
    - Ties within one millisecond: high-frequency events, UUIDv7 values,
      and Snowflake-style IDs that need a per-millisecond counter, which
      can overflow.
    - Consecutive readings on a coarse clock returning identical values.
  - What to check:
    - Every layer a timestamp passes through, and the smallest unit each
      can hold.
    - Equality and version checks on timestamps that pass through a
      millisecond layer.
    - Fractional-second parsing patterns, especially `SSS` in
      `SimpleDateFormat`.
    - ID generators: behavior when many IDs are needed in one
      millisecond.
    - Units and clocks used for latency metrics.
  - Fix:
    - Choose the precision per field end to end (PA-23). Where a
      millisecond layer is unavoidable, truncate to milliseconds at the
      source and compare at milliseconds everywhere.
    - Use version numbers, not timestamps, for optimistic concurrency.
    - Parse fractions with the library's ISO 8601 parser (Java
      `DateTimeFormatter.ISO_INSTANT` or `appendFraction`), never
      `SimpleDateFormat` `SSS` (BP-1).
    - Measure short durations with a high-resolution monotonic clock
      (`System.nanoTime()`, `time.perf_counter_ns()`, Go `time.Since`)
      and record them in microseconds or nanoseconds.
    - Give ID generators a per-millisecond counter with defined overflow
      behavior (RFC 9562 describes methods for UUIDv7).
  - Not a finding:
    - Millisecond precision where it is the documented requirement and
      every layer agrees on it.
  - Escalate (NEEDS-HUMAN): trading, telemetry, or event-ordering
    systems where the required sub-millisecond precision is not stated.
  - Proposed severity (for the user to decide): HIGH when truncation
    breaks concurrency checks or ID uniqueness, or a parser shifts times
    on a core path. MEDIUM for latency metrics and ordering in logs. LOW
    for test-only code.
- PA-25: No time-override assumption. Code assumes nobody will ever need
  "now" to be anything other than the real current time, so it gives no
  way to control the time it sees.
  - Why it is false:
    - Testing: DST transitions, leap days, month-ends, year-ends,
      expiries, and range limits (PA-1 to PA-4, PA-18) can only be
      tested on demand by controlling "now".
    - Reproducing incidents: replaying a failure requires the time it
      happened.
    - Backfills and reprocessing: jobs must run "as of" a past date to
      rebuild data.
    - Simulation, demos, staging, and audits often need future or past
      dates.
    - Reproducible builds pin the build time (`SOURCE_DATE_EPOCH`) so
      artifacts are byte-identical.
    - The system clock itself is often deliberately UTC, not local time
      (PA-8).
  - How it appears in code:
    - Direct `now()` calls scattered through business logic, with no
      injectable clock.
    - Several reads of "now" in one operation, giving inconsistent
      values within the same request or transaction.
    - Tests that change the real system clock. This needs elevated
      privileges, affects every process on the host, and breaks TLS,
      Kerberos, and time sync.
    - Global time mocking (Python `freezegun`, Jest or Sinon fake timers,
      `libfaketime`) used in place of injection. It often misses some
      paths, such as C extensions, other threads, or the database.
    - SQL `NOW()` or `CURRENT_TIMESTAMP` in queries whose "now" must
      match the application's. The database clock cannot be controlled
      from tests, and it differs from the application clock in
      production (PA-14).
    - Batch jobs with no "as-of" parameter. Backfills require changing a
      clock.
    - Date-gated features (launch dates, promotions, sunsets) that can
      only be tested by waiting.
    - Build steps embedding the current time without honoring
      `SOURCE_DATE_EPOCH`.
  - What to check:
    - Where business logic reads the current time, and whether a clock
      is injected.
    - How tests control time.
    - Whether jobs accept an as-of time.
    - Database functions that read the clock inside time-critical
      queries.
  - Fix:
    - Inject a clock: Java `java.time.Clock`, .NET `TimeProvider`
      (.NET 8 and later), Go a `func() time.Time` or a clock interface,
      Python a `now` callable or clock object, JS a clock parameter or
      Luxon `Settings.now` (BP-1).
    - Read "now" once per operation and pass it down.
    - Give jobs an explicit as-of parameter.
    - Pass "now" into queries as a parameter where application time must
      govern.
    - Use fake clocks in tests. Never change the host clock in shared
      environments.
    - Honor `SOURCE_DATE_EPOCH` in builds.
  - Not a finding:
    - Code at the outer edge that reads the clock once and passes the
      value down. That is the fix.
    - Throwaway scripts with no time-dependent logic worth testing.
  - Escalate (NEEDS-HUMAN): backfill, audit, or replay requirements that
    are implied but not stated for jobs with no as-of parameter.
  - Proposed severity (for the user to decide): HIGH when time-critical
    core logic (billing, expiry, scheduling) cannot be tested or
    backfilled without changing a real clock, or when tests change the
    clock on shared hosts. MEDIUM for scattered `now()` calls and
    inconsistent reads within one operation. LOW for test-only code.
- PA-26: Test-only time-override assumption. Code assumes controlling
  "now" is needed only in testing, never in production.
  - Overlap: PA-25 covers the absence of any way to control "now".
    PA-26 covers production's own need for it, and test-only overrides
    that leak into production. Merged per the class ledgers.
  - Why it is false:
    - Backfills and reprocessing run in production against production
      data: rebuilding aggregates, re-running billing for a past period
      after a fix, end-of-period re-close.
    - Incident replay and disaster recovery re-run events at their
      original times.
    - Late-arriving data must be processed by event time, not by the
      time it happens to arrive.
    - Operational events change production time: clock corrections after
      outages (PA-12), leap-second smears (PA-20), and emergency zone-rule
      changes (PA-9).
    - Devices without network access (ships, aircraft, air-gapped sites,
      embedded hardware) have clocks set by hand in the field.
  - How it appears in code:
    - No supported as-of mechanism in production. Operators change the
      host clock, or run ad-hoc scripts, to backfill.
    - Pipelines that use processing time (`now()`) where event time is
      required. Reprocessing produces different results from the
      original run.
    - Test-only overrides reachable in production:
      - An environment variable or config flag (`FREEZE_TIME`,
        `FAKE_NOW`) that enables a fake clock.
      - A fake clock wired as the default in dependency injection.
      - `libfaketime` preloaded in a production image.
    - User-controllable time: a request parameter or header (`?now=`,
      `X-Debug-Time`) that sets the server's "now". Users bypass expiry,
      trials, promotions, and rate limits.
    - Overrides that leave no trace: outputs do not record that they were
      produced "as of" a different time.
  - What to check:
    - How production backfills and replays are run.
    - Whether pipelines distinguish event time from processing time.
    - Every path that can change the clock the application sees: config,
      environment, request input, dependency injection defaults, and
      image contents.
    - Audit records for runs with an overridden time.
  - Fix:
    - Provide a production-grade as-of mechanism: an explicit parameter,
      restricted to authorized operators and jobs, logged and audited,
      and never changing the host clock.
    - Record both event time and processing time, and process by event
      time.
    - Never accept "now" from end-user input.
    - Exclude fake clocks from production builds, or fail at startup if a
      fake clock is active in a production configuration.
    - Stamp outputs produced under an override with the as-of time used.
    - Write runbooks for manual clock setting on offline devices.
  - Not a finding:
    - Test-only clocks that cannot be enabled in production builds.
    - Authorized, audited operator as-of parameters.
  - Escalate (NEEDS-HUMAN): reprocessing where the spec does not say
    whether re-runs must reproduce the original result or apply current
    rules (prices, tax rates, zone rules).
  - Proposed severity (for the user to decide): CRITICAL when an end user
    can set the time the server uses for expiry, authorization, or
    payment. HIGH when a fake clock can be switched on in production, or
    when backfills require changing a production clock. MEDIUM for
    missing event-time handling and unaudited overrides. LOW for
    test-only code.
- PA-27: Single-format assumption. Code assumes timestamps always arrive
  as bare numeric epoch values that everyone reads the same way.
  - Overlap: PA-23 and PA-24 cover numeric units and precision. PA-19
    covers differing epochs. PA-27 covers format variety and ambiguity
    at input. Merged per the class ledgers.
  - Why it is false:
    - Bare numbers are ambiguous. The user's two examples (verified):
      - `1339972628` read as seconds is 2012-06-17 22:37:08 UTC.
      - `133997262837` has 12 digits: as milliseconds it is
        1974-03-31, as microseconds 1970-01-02, and as seconds the year
        6216. Neither unit is obvious, and digit-count guessing fails.
    - Text formats are common and differ:
      - ISO 8601 and RFC 3339, with or without offset or fraction.
      - RFC 5322 email dates (`Sun, 17 Jun 2012 22:37:08 +0000`).
      - HTTP dates: IMF-fixdate, plus the obsolete RFC 850 and asctime
        forms that RFC 9110 says recipients must accept.
      - Locale formats (`01/02/2026` is January 2 or February 1).
      - X.509 `UTCTime` (two-digit year: 50-99 means 19xx, 00-49 means
        20xx) and `GeneralizedTime`.
      - BSD syslog (RFC 3164): no year and no zone.
    - Structured and platform encodings: Protobuf `Timestamp` (seconds
      plus nanos), MongoDB Extended JSON `{"$date": ...}`, legacy
      ASP.NET JSON `/Date(1339972628000)/`, Excel serials (PA-4),
      Windows FILETIME, .NET ticks, Apple reference dates (PA-19), Julian
      dates, and GPS week plus seconds.
  - How it appears in code:
    - Unit guessed from magnitude or digit count (`if ts > 1e12: ms`).
      Values near 1970, far-future values, and microsecond or nanosecond
      inputs are misread.
    - Numeric-only parsing applied to text. JS
      `parseInt("2026-07-01T09:00:00Z")` returns `2026` (verified).
    - JS `Date.parse` and `new Date(string)` on non-ISO strings. Only
      the ISO format is specified. Others are engine-dependent: V8 reads
      `"01/02/2026"` as January 2 and accepts
      `"2026-07-01 09:00"` as local time (verified).
    - Fuzzy parsers guessing day and month order, such as Python
      `dateutil.parser.parse` (month first unless `dayfirst=True`).
    - Locale-dependent parsing of month and day names: Python
      `strptime("%b")` and Java `DateTimeFormatter` with `MMM` use the
      current locale by default.
    - Two-digit years expanded with an arbitrary pivot.
    - Syslog lines given the current year, so December entries read in
      January land in the wrong year.
  - What to check:
    - Every input boundary that accepts time values: which formats are
      accepted, and whether the format and unit are declared.
    - Unit or format detection by heuristics.
    - Parsing calls without an explicit format and locale.
    - Two-digit-year handling, and year or zone inference for formats
      that omit them.
  - Fix:
    - Declare the wire format of every interface. Prefer RFC 3339 with
      an explicit offset for text. For numeric epochs, state the epoch
      and unit in the schema and field name (PA-23).
    - Parse strictly with an explicit format and a fixed locale (Java
      `Locale.ROOT`, POSIX/C locale). Reject ambiguous input instead of
      guessing.
    - Use library parsers for standard formats: HTTP dates, email dates,
      X.509 times (BP-1).
    - Apply the two-digit-year rule the format's standard defines.
    - For formats without year or zone, attach them from known context
      and document the rule.
    - Validate in the schema (for example OpenAPI `format: date-time`).
  - Not a finding:
    - A documented internal interface that uses one numeric format with
      a named unit, validated at the boundary.
  - Escalate (NEEDS-HUMAN): inputs whose format or unit cannot be
    established from code, schema, or documentation, such as partner
    feeds and imported files.
  - Proposed severity (for the user to decide): HIGH when misread inputs
    store wrong dates on a core path (imports, payments, bookings).
    MEDIUM for logs and analytics. LOW for test-only code.
- PA-28: Format consistency assumption. Code assumes a given source or
  field always uses one timestamp format, across every record and over
  time.
  - Overlap: PA-27 covers the variety of formats across sources. PA-28
    covers variation within one source, field, or standard. Merged per the class ledgers.
  - Why it is false:
    - One standard, many shapes. Valid ISO 8601 / RFC 3339 variations
      include:
      - Fractional seconds present or absent, with any number of digits.
      - `Z`, `+00:00`, `+0000`, or `-00:00` for UTC.
      - `T`, `t`, or a space as the separator.
      - Basic format (`20260701T090000Z`), week dates, ordinal dates,
        and reduced precision (`2026-07`).
    - Producers vary output by value. Python `isoformat()` omits
      microseconds when they are zero: `2026-07-01T09:00:00+00:00` next
      to `2026-07-01T09:00:00.500000+00:00` (verified).
    - Producers change over time: library upgrades, new app versions,
      and serializer configuration changes alter output. Consumers change
      too: Python `fromisoformat` accepts `Z` only from 3.11.
    - Several producers write one field: old and new mobile app versions,
      partners, migrations, and legacy rows.
    - Schemaless storage mixes types: a MongoDB field holding a BSON date
      in some documents and a string in others, or JSON fields holding
      strings in some records and numbers in others.
    - Spreadsheets rewrite dates on save in the editor's locale format.
  - How it appears in code:
    - One strict pattern applied to a field whose valid values vary. Valid
      records fail to parse and are dropped or crash the import.
    - Lenient parsing that accepts every variant and misreads some
      (PA-27).
    - Timestamp strings sorted, compared, or deduplicated as text.
      `2026-07-01T09:00:00.5Z` sorts before `2026-07-01T09:00:00Z`
      although it is later, because `.` sorts before `Z` (verified).
      Different offsets and fraction lengths break text ordering the
      same way.
    - Timestamps stored in string columns, so every reader must cope
      with every historical format.
    - Parse failures swallowed silently.
  - What to check:
    - Fields stored or compared as strings instead of typed values.
    - The set of formats each field actually contains, including legacy
      rows and every producer version.
    - Parsers: do they accept the full declared profile, and what happens
      on failure?
    - Serializer settings and versions on every producer.
  - Fix:
    - Parse at the boundary into typed values. Compare, sort, and
      deduplicate only typed values.
    - Use a library parser that accepts the full declared profile, for
      example RFC 3339 (BP-1).
    - Normalize on write to one canonical form (for example UTC with
      `Z` and a fixed number of fraction digits).
    - Store typed datetime columns, not strings. Enforce types in
      schemaless stores with schema validation.
    - Version producer contracts and add contract tests for the format.
    - Migrate legacy rows to the canonical form.
    - Reject unparseable values loudly and report them. Never drop them
      silently.
  - Not a finding:
    - Text sorting of timestamps whose canonical fixed-width UTC form is
      enforced on every write.
  - Escalate (NEEDS-HUMAN): legacy datasets whose mix of formats cannot be
    established from code or schema.
  - Proposed severity (for the user to decide): HIGH when inconsistent
    formats cause wrong ordering, deduplication, or filtering, or drop
    records, on a core path. MEDIUM for logs and analytics. LOW for
    test-only code.
- PA-29: Uniform precision assumption. Code assumes every timestamp in a
  field or system carries the same precision.
  - Overlap: PA-23 and PA-24 cover the smallest unit a system handles.
    PA-28 covers varying fraction digits as a format issue. PA-29 covers
    values of different precision mixed together, and the comparison,
    range, and duration bugs that follow. Merged per the class ledgers.
  - Why it is false:
    - Layers truncate differently, so the same field holds values of
      different precision depending on which path wrote them (PA-24).
    - Precision changes over time: a column widened from `DATETIME` to
      `DATETIME(6)` leaves old rows at whole seconds. Platform upgrades
      change the clock, for example Java 9 raised `Instant.now()`
      precision beyond milliseconds on common platforms.
    - Sources differ: devices, partners, and logs report seconds,
      milliseconds, or finer.
    - Some values are inherently coarser: date-only values, month-only
      or year-only values, and approximate values ("sometime in 2019")
      stored next to full timestamps.
    - Representation is not accuracy: a millisecond value from a clock
      that ticks every 15.6 ms (PA-24), or a midnight timestamp that
      really means a date, claims precision it does not have.
  - How it appears in code:
    - Equality and deduplication between truncated and full-precision
      copies of the same event fail (PA-24).
    - Closed ranges at whole-second precision: `ts <= '2026-07-01
      23:59:59'` misses rows at 23:59:59.5.
    - Ordering: a truncated value sorts before the full-precision value
      of the same moment, and whole-second rows tie with each other.
    - Negative durations: a start of 09:00:00.900 at full precision and
      an end of 09:00:00.950 truncated to 09:00:00 give -0.9 seconds.
    - Sync cursors: `ts > last_seen` with a truncated `last_seen` skips
      or repeats rows.
    - Date-only values coerced to midnight timestamps, then compared with
      full timestamps. "Happened on that day" checks fail.
    - Cache or idempotency keys built from string forms of different
      precision.
    - Time-series bucketing where coarse sources pile up at `.000`.
  - What to check:
    - The precision each writer produces for each field, including old
      rows.
    - Range conditions with closed upper bounds.
    - Durations and comparisons whose two sides come from different
      sources or layers.
    - Fields that mix dates, timestamps, and coarser values.
  - Fix:
    - Declare the precision of each field and normalize on write by
      truncating consistently to it.
    - Keep inherently coarse values in their own types (date, year-month)
      or store their granularity explicitly. Do not pad them into fake
      full timestamps.
    - Compare at an explicit common precision, normally the coarser one.
    - Use half-open ranges (`>= start AND < next_start`).
    - Add tie-breakers to ordering, and use sequence IDs or `>=` with
      deduplication for cursors.
    - Clamp durations computed across sources at zero, and log negative
      values as data errors.
  - Not a finding:
    - Fields where one precision is enforced on every write path.
  - Escalate (NEEDS-HUMAN): datasets mixing granularities (exact times,
    dates, months, approximate values), such as historical or medical
    records, where the intended comparison rules are not stated.
  - Proposed severity (for the user to decide): HIGH when mixed precision
    drops or repeats records, breaks deduplication, or produces wrong
    durations on a core path. MEDIUM for ordering in logs and analytics.
    LOW for test-only code.
- PA-30: Timestamp uniqueness assumption. Code assumes a timestamp with
  enough precision is unique and can serve as an identifier.
  - Overlap: PA-23 and PA-24 cover collisions at second and millisecond
    resolution. PA-30 covers why no precision guarantees uniqueness, and
    the use of timestamps as identifiers and tokens. Merged per the class ledgers.
  - Why it is false:
    - Precision is not resolution. A nanosecond field filled from a clock
      that ticks every 15.6 ms, every microsecond, or at a
      browser-coarsened rate repeats values (PA-24).
    - Concurrency: threads, cores, processes, and hosts read the same
      tick at the same time.
    - Clocks repeat values: backward steps (PA-11), VM restores
      (PA-12), the repeated hour at a DST fall-back in local time (PA-1),
      and the repeated second POSIX time uses for a leap second (PA-20).
    - Precision is lost downstream, collapsing distinct values (PA-24).
    - One "now" per transaction: Postgres `now()` and
      `CURRENT_TIMESTAMP` return the transaction start time, so every row
      in a transaction gets the same value. `clock_timestamp()` returns
      the actual time.
    - At volume, collisions follow from probability even with fine
      resolution.
  - How it appears in code:
    - Timestamps as primary keys, file names, object-storage keys, temp
      directories, lock names, message IDs, or idempotency keys.
    - Upserts or `ON CONFLICT ... DO UPDATE` keyed on a timestamp. A
      collision silently overwrites another record.
    - Security values derived from time: password-reset tokens, session
      IDs, or nonces built from timestamps, or random generators seeded
      with the current time. They are predictable.
    - Merges and event ordering that rely on timestamp alone for strict
      order.
  - What to check:
    - Any key, name, or identifier built only from a timestamp.
    - Conflict handling on timestamp-keyed writes.
    - Tokens, nonces, and random seeds that involve the clock.
    - Ordering logic with no tie-breaker.
  - Fix:
    - Use real unique identifiers: database sequences, UUIDv4, or UUIDv7
      with its random or counter bits (RFC 9562).
    - When time order is needed, combine timestamp, node ID, and a
      counter (Snowflake-style), with backward-clock handling (PA-11).
    - Generate security tokens with a cryptographically secure random
      generator. Never derive them from time.
    - Make conflicts on unique keys fail or retry, never silently
      overwrite.
    - Add a sequence tie-breaker to ordering.
  - Not a finding:
    - Timestamps stored as ordinary non-unique attributes.
    - Composite keys that pair a timestamp with a unique discriminator.
  - Escalate (NEEDS-HUMAN): deduplication keyed on timestamps where the
    business rule for two genuinely distinct events at the same time is
    not stated.
  - Proposed severity (for the user to decide): CRITICAL when
    time-derived values serve as security tokens or session IDs. HIGH
    when collisions overwrite or lose records on a core path. MEDIUM for
    temp files, logs, and caches. LOW for test-only code.
- PA-31: Event-time fidelity assumption. Code assumes a timestamp records
  the moment the event actually happened.
  - Overlap: PA-26 introduces event time versus processing time for
    reprocessing. PA-11 and PA-14 cover wrong client clocks. PA-31 covers
    what a timestamp actually records, in general. Merged per the class ledgers.
  - Why it is false: a timestamp often records something other than the
    event.
    - Pipeline times: when a record was received, queued, processed,
      indexed, flushed, or committed. Log shippers often stamp ingest
      time unless the event time is parsed from the line. Kafka topics
      store either the producer's time (`CreateTime`) or the broker's
      append time (`LogAppendTime`), depending on configuration.
    - Database defaults: `DEFAULT now()` stamps insert time. Imported or
      backfilled historical records all get the import time. Postgres
      `now()` gives transaction start, not statement time (PA-30).
    - Maintenance updates: `updated_at` triggers fire on any write,
      including bulk migrations, so the value reflects the last touch,
      not the last meaningful change.
    - Files: modification times change on copy, extraction, restore, and
      git checkout (git does not store mtimes).
    - Device and sender metadata: photo EXIF dates come from the camera's
      clock, usually local time with no zone, and often wrong. Email
      `Date` headers are set by the sender's client and can be forged.
    - Offline and queued events stamped when they sync, not when they
      happened.
    - Batch jobs stamping every record with the job's start time.
    - Records created in the system after the real-world event, such as
      an order taken by phone yesterday and entered today.
    - Effective time versus recorded time: back-dated corrections in
      payroll, insurance, and accounting take effect at one time and are
      recorded at another (bitemporal data).
    - Values falsified on purpose by users or attackers.
  - How it appears in code:
    - Analytics, SLAs, or ordering based on ingestion or processing time.
    - Events from several sources merged and ordered by receive time.
    - Legal, audit, or billing decisions based on client-supplied or
      editable timestamps.
    - Sync and change detection keyed on `updated_at` that maintenance
      writes also change.
    - Builds, caches, or incremental backups that decide correctness by
      file modification time.
    - Trusting EXIF or email `Date` values as fact.
    - One timestamp field serving as both event time and record time.
  - What to check:
    - For each timestamp field: what event sets it, who sets it, and
      whether that matches how it is used.
    - Defaults and triggers that set times automatically.
    - Import and backfill paths: do they carry original event times?
    - Pipeline configuration: where event time is parsed, and Kafka
      timestamp type.
  - Fix:
    - Model and name the times separately: `occurred_at` (event),
      `received_at` (ingestion), `processed_at`, and `effective_from`/
      `recorded_at` for bitemporal data.
    - Record each time's source and trust level. Set ingestion times on
      the server.
    - Parse event time from the payload in pipelines. Choose the Kafka
      timestamp type deliberately.
    - Carry original event times through imports. Never let
      `DEFAULT now()` stand in for them.
    - Use content hashes, not modification times, where correctness
      depends on change detection.
    - Keep audit trails append-only with server-assigned times.
  - Not a finding:
    - Fields documented as receive or processing time and used as such.
  - Escalate (NEEDS-HUMAN): deadline decisions ("submitted on time")
    where the spec does not say which time counts: created, sent,
    received, or processed.
  - Proposed severity (for the user to decide): HIGH when deadlines,
    legal records, billing, or SLAs are decided by the wrong kind of
    time, or when imports overwrite event times with import time on core
    data. MEDIUM for analytics and change detection. LOW for test-only
    code.
- PA-32: Universal readable-date assumption. Code assumes one
  human-readable date format, such as ISO-style `YYYY-MM-DD`, is
  understood the same way by everyone.
  - Overlap: PA-27 covers machine input formats, including locale
    formats. PA-17 covers date-only values across zones. Adorno class
    2.22 covers locale-aware display. PA-32 covers the correctness
    defects that come from human-readable forms: misread input, display
    strings reused as data, and non-Gregorian or non-ASCII output.
    Generay checks this independently of adorno (user decision).
  - Why it is false:
    - Field order and separators vary. The same date 2025-10-03 formats
      by default as (verified with Node `Intl`):
      - `en-US`: `10/3/2025`
      - `en-GB`: `03/10/2025`
      - `de-DE`: `3.10.2025`
      - `hu-HU`: `2025. 10. 03.`
    - `03/10/2025` is October 3 to one reader and March 10 to another.
      ISO 8601 is clear to technical readers but unfamiliar to much of
      the general public.
    - Non-Gregorian calendars are in daily use, and locale defaults
      select them (verified):
      - `th-TH` shows the Buddhist-era year 2568 by default.
      - `fa-IR` shows the Solar Hijri date 1404/7/11 by default, in
        Persian digits.
      - With the calendar requested, Japanese era shows `R7/10/3`
        (Reiwa 7) and the Taiwan (Minguo) calendar shows year 114.
    - Digits and marks: `ar-EG` output uses Arabic-Indic digits and
      inserts invisible right-to-left marks (U+200F) between fields
      (verified). Persian output uses Persian digits.
    - Month and day names differ by language, and users type dates with
      native digits.
  - How it appears in code:
    - Display strings reused as data: locale-formatted dates written to
      storage, used as keys or file names, or parsed back into values.
      Calendar, digit, and mark differences break the round trip.
    - Free-text date inputs parsed with one assumed order. Day and month
      swap silently for days 1 to 12.
    - A Gregorian year assumed from locale-formatted output. A Thai-locale
      year of 2568 is stored as the Gregorian year.
    - Parsers that accept only ASCII digits rejecting native-digit input,
      or lenient parsers that strip marks and misread fields.
    - Machine-facing exports (CSV, reports, APIs) produced with
      `toLocaleDateString()` or the server's locale (PA-17).
  - What to check:
    - Every place a formatted date string flows back into data: storage,
      keys, exports, re-parsing.
    - Date input handling: structured picker or free text, and with what
      parsing rules.
    - Locale and calendar settings on formatters that feed machines.
  - Fix:
    - Keep a strict split: ISO 8601 / RFC 3339 for storage and transport,
      locale-aware formatting only at the display edge. Never parse
      display strings back into data.
    - Use structured date inputs (pickers, separate fields) where
      possible. For free text, parse with an explicit locale and order,
      and reject ambiguous input.
    - When a Gregorian value or ASCII digits are required, request them
      explicitly (for example `Intl` options `calendar: "gregory"` and
      `numberingSystem: "latn"`).
    - Accept native digits in user input by normalizing them first.
    - For displays that must be unambiguous across locales, include the
      month name (`3 Oct 2025`) or show ISO with a label.
  - Not a finding:
    - ISO 8601 shown to technical audiences in logs, admin tools, or
      developer UIs.
    - Locale-specific display that never flows back into data and is
      correct for its locale.
  - Escalate (NEEDS-HUMAN): multi-locale products where the display and
    input format requirements, including calendar system, are not
    stated.
  - Proposed severity (for the user to decide): HIGH when formatted or
    typed dates are parsed into wrong stored values on a core path
    (day/month swap, Buddhist-era year stored as Gregorian). MEDIUM for
    machine exports in locale formats. LOW for test-only code.
- PA-33: Constant zone-difference assumption. Code assumes the offset
  between two time zones stays the same.
  - Overlap: PA-9 covers zone rules changing by government decision.
    PA-33 covers the difference between two zones varying through the
    year under current rules. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b for 2026):
    - DST starts and ends on different dates. The US switches in early
      March and early November, the EU in late March and late October.
      London minus New York is 5 hours most of the year, but 4 hours
      around 2026-03-20 and 2026-10-30.
    - Hemispheres run DST in opposite seasons. Sydney minus London is
      11 hours in January, 9 in April, and 10 for a few weeks in October.
    - Some zones skip DST. Los Angeles and Phoenix match in summer and
      differ by 1 hour in winter.
    - Differences need not be whole hours: Kathmandu (+05:45) minus
      Kolkata (+05:30) is 15 minutes. Lord Howe Island's 30-minute DST
      and Troll's 2-hour shift (PA-1) change differences by those
      amounts.
    - Some zones suspend DST temporarily. Morocco (`Africa/Casablanca`)
      moves from +01:00 to +00:00 during Ramadan (+00:00 on 2026-02-25).
    - Rule changes alter differences permanently (PA-9).
  - How it appears in code:
    - Hardcoded differences: `london = new_york + 5`, "the customer is
      8 hours behind the server".
    - Conversion by adding a difference computed once, then reused for
      other dates.
    - Recurring cross-zone events (weekly meetings, market opens, batch
      windows) computed with one fixed difference. They are an hour off
      for the weeks between two zones' transitions.
    - Static zone tables mapping each zone to one offset, and zone pickers
      that store the displayed offset ("(GMT-05:00) Eastern Time")
      instead of the zone ID.
    - Business-hours, cutoff, or SLA logic for another region computed
      with a fixed difference from headquarters.
  - What to check:
    - Literal hour or minute differences between named regions.
    - Zone conversions that do not pass through an instant for the
      specific date.
    - Recurring cross-zone schedules.
    - Zone pickers: stored value and displayed label.
  - Fix:
    - Convert through the instant every time, for the specific date:
      local time in zone A to UTC instant to local time in zone B, with
      the library (BP-1).
    - Never store or reuse a difference between zones.
    - Anchor each recurring cross-zone event to one owner zone and
      convert each occurrence separately.
    - Store IANA zone IDs from pickers. Compute the displayed offset for
      the relevant date.
    - Test conversions in the weeks between different zones'
      transitions, and with non-whole-hour zones.
  - Not a finding:
    - Differences between fixed-offset zones by design (UTC and
      `Etc/GMT` zones).
  - Escalate (NEEDS-HUMAN): recurring cross-zone events whose spec does
    not say whose local time anchors them, for example a weekly meeting
    at 09:00 New York time or 14:00 London time.
  - Proposed severity (for the user to decide): HIGH when scheduling,
    trading windows, billing cutoffs, or SLAs on a core path use a fixed
    difference. MEDIUM for display. LOW for test-only code.
- PA-34: Future zone-difference stability assumption. Code assumes
  differences between zones, as known today, will hold for future dates.
  - Overlap: PA-9 covers zone rules changing and how to store future
    local events. PA-33 covers differences varying under current rules.
    PA-34 covers future cross-zone values computed now and kept. Merged per the class ledgers.
  - Why it is false:
    - Governments change rules, sometimes with days of notice (PA-9).
      Every change alters differences with every other zone.
    - Changes are pending or proposed. The European Parliament voted in
      2019 to end seasonal clock changes, but the Council has not
      adopted it. The US Senate passed the Sunshine Protection Act in
      2022, but it was not enacted. Either could change future
      differences on short notice.
    - Calendar invitations carry their own rules. iCalendar (RFC 5545)
      can embed `VTIMEZONE` definitions in each invite. A stale embedded
      definition and a recipient's current tzdata disagree about future
      occurrences.
    - Different systems update tzdata at different times (PA-9), so they
      disagree about the same future date for a while.
  - How it appears in code:
    - Future cross-zone conversions computed once and stored: a meeting
      converted into each attendee's local time at booking.
    - Long-range schedules materialized far ahead with today's rules:
      timetables, flight and broadcast schedules, recurring billing
      runs.
    - Future offsets or differences stored in database columns or
      shipped as static tables in apps and front-end bundles.
    - Contracts, SLAs, or configs written as paired local times ("14:00
      London = 09:00 New York").
    - Embedded `VTIMEZONE` data trusted over the IANA zone it names.
    - Tests asserting specific future offsets with literals. They break
      on a tzdata update, and the tempting fix is to edit the literal.
  - What to check:
    - Stored or cached conversions for future dates.
    - Materialized future schedules, and what regenerates them.
    - Static offset tables in apps, bundles, or configs.
    - iCalendar handling: which zone definition wins.
  - Fix:
    - Store future events as local time plus zone ID, anchored to one
      owner zone, and convert at use (PA-9).
    - Regenerate materialized schedules when tzdata changes. Track tzdata
      releases (the IANA `tz-announce` list) and trigger recomputation.
    - Ship zone IDs, not offset tables. Let the platform's tz data do the
      conversion.
    - When an invite's `TZID` names an IANA zone, recompute with current
      data rather than trusting the embedded rules, where the product
      allows.
    - Derive expected future offsets in tests from the library, or pin
      the tzdata version the test runs with.
  - Not a finding:
    - Future events defined as fixed instants by design (PA-9).
  - Escalate (NEEDS-HUMAN):
    - Pending legislation affecting zones the product serves.
    - Long-lived contracts or schedules written as paired cross-zone
      local times.
  - Proposed severity (for the user to decide): HIGH when future
    appointments, travel, broadcasts, or contract deadlines on a core
    path rely on stored cross-zone conversions. MEDIUM for static offset
    tables in display. LOW for test-only code.
- PA-35: Advance-notice assumption. Code and operations assume zone rule
  changes are announced well ahead, so slow update processes are good
  enough.
  - Overlap: PA-9 lists rule changes and the layers that carry tz data.
    PA-34 covers stored future conversions. PA-35 covers update latency:
    how fast every copy of tz data can change once a rule changes. Merged per the class ledgers.
  - Why it is false:
    - Notice can be days: Egypt cancelled DST in 2016 days before it was
      due, and Lebanon postponed and then restored DST within days in
      2023 (PA-9). The tz database maintainers ask governments for at
      least a year of notice and often get far less.
    - Official and de facto time can differ. Some communities keep an
      unofficial local time, such as UTC+6 in parts of Xinjiang while
      official China time is UTC+8. tzdata's `Asia/Urumqi` uses +06.
    - Update latency is long in many layers:
      - Mobile apps wait for store review. OS tz data arrives with OS
        updates (Android can also update it through system updates since
        Android 10).
      - Java runtimes update through JDK releases or TZUpdater.
      - Container base images and pinned packages (`tzdata`,
        Python `tzdata`) stay old until rebuilt.
      - Embedded firmware may never be updated.
      - Libraries that bundle their own data go stale with the app
        release: moment-timezone data files, Noda Time's TZDB file. By
        contrast, Luxon and date-fns-tz use the platform's `Intl` data.
  - How it appears in code and operations:
    - tz data updated only as part of full application releases on long
      cycles.
    - Bundled tz data pinned in front-end bundles, app packages, or
      lockfiles with no update owner.
    - No emergency path to correct a region's offset before new data
      ships.
    - Reminders, notifications, and schedules computed far in advance
      and never recomputed (PA-34).
  - What to check:
    - Every copy of tz data in the system, its version, and who updates
      it (PA-9).
    - Whether tz data can ship independently of feature releases.
    - Whether bundled libraries carry their own tz data.
    - What recomputes scheduled items after an update.
  - Fix:
    - Treat tz data like a security patch: a fast update path that does
      not wait for feature releases.
    - Keep an inventory of tz data copies and versions, and alert on
      IANA `tz-announce` releases.
    - Prefer platform data that updates automatically (OS, `Intl`) over
      bundled copies, or give bundled copies an update pipeline (BP-1).
    - Provide an operator override for a region's zone rules in an
      emergency, with audit.
    - Recompute reminders and schedules at send time, or after any tz
      data update (PA-34).
  - Not a finding:
    - Systems with a documented, tested fast tz data update process.
  - Escalate (NEEDS-HUMAN): products serving regions with a history of
    short-notice changes, where no fast update path exists.
  - Proposed severity (for the user to decide): HIGH when core scheduling
    depends on tz data that cannot be updated quickly. MEDIUM for display
    and reports. LOW for test-only code.
- PA-36: Fixed DST schedule assumption. Code assumes DST transitions fall
  on the same dates and times every year.
  - Overlap: PA-9 and PA-35 cover rule changes and notice. PA-33 covers
    zones switching on different dates. PA-36 covers transition dates
    moving from year to year within one zone, and hand-coded DST logic.
    Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b where marked):
    - Rules are relative ("second Sunday in March"), so dates move.
      New York switches on 2026-03-08 and 2026-11-01, but on 2027-03-14
      and 2027-11-07 (verified).
    - The local transition time differs by zone. US zones switch at
      02:00 local. EU zones switch together at 01:00 UTC, so local times
      differ. Some zones switch at midnight: in Santiago, Chile, 23:59
      on 2026-09-05 is followed by 01:00, so midnight does not exist
      that day (verified).
    - Rules change. The US moved its DST dates in 2007 (Energy Policy
      Act of 2005). Hardcoded pre-2007 rules have been wrong since.
    - Some rules follow religious or lunar calendars. Morocco's Ramadan
      suspension moves about 11 days earlier each year: 2026-02-15 to
      2026-03-22, then 2027-02-07 to 2027-03-14 (verified). Iran's
      former DST followed Persian calendar dates until it was abolished
      in 2022.
    - Southern-hemisphere DST spans New Year.
    - Some years skip DST entirely by decision, as Fiji did in 2022.
    - "Is DST" flags are unreliable. tzdata's main format models
      Ireland's winter time as negative DST. Some builds use a
      compatibility format that does not: this host reports 0 DST for
      Dublin in January and 1 hour in July (verified). Platforms
      disagree.
  - How it appears in code:
    - Hardcoded transition dates, or DST tested by month range
      (`month in 4..10`, `between Mar 8 and Nov 1`).
    - Hand-written rules ("last Sunday of October") that are outdated or
      apply only to some zones.
    - Hand-rolled DST detection, such as comparing January and July
      offsets in JS. It fails for zones without DST, with negative DST,
      or with rule changes between the sampled dates.
    - Logic keyed on an `isDST` flag instead of on the actual offset.
    - Code that assumes midnight always exists on every local date.
    - Tests pinned to one year's transition dates.
  - What to check:
    - Literal months, dates, or weekday rules near offset or DST logic.
    - Any DST detection not performed by the library.
    - Uses of DST flags.
    - Construction of local midnight or start of day.
  - Fix:
    - Never hardcode transitions. Ask the library for the offset at the
      instant, or for the next transition (for example Java
      `ZoneRules.nextTransition`) (BP-1).
    - Base decisions on the actual offset, not on a DST flag.
    - Get start of day from the library (for example Java
      `LocalDate.atStartOfDay(zone)`, Luxon `startOf('day')`), which
      handles a missing midnight.
    - Test several years, both hemispheres, midnight-transition zones
      (Santiago), Morocco, and Dublin.
  - Not a finding:
    - Library-driven offset handling with no hand-coded DST logic.
  - Escalate (NEEDS-HUMAN): business rules written in terms of "DST
    periods" where the intended zone and rule source are not stated.
  - Proposed severity (for the user to decide): HIGH when hardcoded
    transitions drive scheduling, billing, or deadlines on a core path.
    MEDIUM for display. LOW for test-only code.
- PA-37: Simultaneous DST assumption. Code assumes every zone changes for
  DST at the same moment.
  - Overlap: PA-33 covers zones switching on different dates. PA-36
    covers transition dates and local transition times within one zone.
    PA-37 covers transitions happening at different instants across
    zones, including zones under the same rule, and global DST handling
    in code. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b):
    - Same rule, different instants. US zones each switch at 02:00 local
      time, so the change rolls west hour by hour. New York minus Chicago
      is normally 1 hour, but it is 2 hours from 07:00 to 08:00 UTC on
      2026-03-08, and 0 hours from 06:00 to 07:00 UTC on 2026-11-01.
    - Coordinated regions are the exception. EU zones all switch at
      01:00 UTC, so London, Paris, and Helsinki change together on
      2026-03-29 and keep their differences.
    - Different dates in different regions (PA-33), and opposite seasons
      in the two hemispheres.
    - Many zones never observe DST: most of Asia and Africa, and regions
      such as Arizona, Hawaii, Saskatchewan, and Queensland inside
      countries that otherwise do.
  - How it appears in code:
    - One global DST flag or setting for the whole application
      (`DST_ACTIVE = true`).
    - One "+1 hour in summer" adjustment applied to every user or region.
    - Per-region schedules derived from one reference zone's transition.
    - Global jobs, maintenance windows, or alert suppression scheduled at
      a single instant "after the DST change", while other regions have
      not changed yet or changed hours earlier.
    - Offsets for all regions cached per day, computed from the server's
      zone.
  - What to check:
    - Global flags, constants, or config controlling DST.
    - DST adjustments applied without a zone.
    - Cross-region jobs and windows timed around DST changes.
  - Fix:
    - Compute offsets per zone, per instant, with the library (BP-1). No
      global DST state.
    - Schedule cross-region work per region, or in UTC with per-region
      local handling.
    - Test the hours between different zones' transition instants on
      transition days (for example 06:00 to 09:00 UTC on US transition
      Sundays).
  - Not a finding:
    - Library-driven per-zone offset handling.
  - Escalate (NEEDS-HUMAN): global operations planned around "the DST
    change" where the regions involved and their transition instants are
    not stated.
  - Proposed severity (for the user to decide): HIGH when a global DST
    flag or single adjustment drives scheduling, billing, or deadlines on
    a core path. MEDIUM for display and monitoring windows. LOW for
    test-only code.
- PA-38: One-hour DST assumption. Code assumes a DST change always moves
  clocks by exactly one hour.
  - Overlap: PA-1 cites Lord Howe and Troll for day length. PA-33 covers
    offsets that are not whole hours. PA-36 covers negative DST and DST
    flags. PA-38 covers the size of the DST shift. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b):
    - Lord Howe Island (`Australia/Lord_Howe`) shifts by 30 minutes:
      +10:30 in winter, +11:00 in summer.
    - Troll Station (`Antarctica/Troll`) shifts by 2 hours: +00:00 in
      winter, +02:00 in summer.
    - Historical double summer time: the UK ran +01:00 all year during
      the Second World War and +02:00 in summer (1942: +01:00 in January,
      +02:00 in June).
    - Negative and suspended DST: Ireland's winter time is modeled as
      negative DST, and Morocco drops an hour during Ramadan (PA-33,
      PA-36).
    - Historical shifts of other sizes appear in tzdata's historical
      data, and governments can choose any size in future.
  - How it appears in code:
    - `offset + 60` minutes, `hour += 1`, or `timedelta(hours=1)` applied
      when DST is active.
    - A DST boolean stored, then the offset rebuilt as standard offset
      plus one hour.
    - The gap or overlap at a transition assumed to be exactly 60
      minutes: "skip 02:00 to 03:00", "the repeated hour".
    - Offset validation or UI controls that allow only whole-hour DST
      shifts.
    - Day lengths assumed to be only 23 or 25 hours (PA-1).
  - What to check:
    - Literal 60-minute or one-hour adjustments tied to DST.
    - Offsets reconstructed from flags.
    - Gap and overlap handling at transitions.
  - Fix:
    - Get the full offset for each instant from the library, and store
      the zone ID or full offset, never a DST boolean (BP-1).
    - Get the size of each gap or overlap from the library (for example
      Java `ZoneOffsetTransition.getDuration()`).
    - Test with Lord Howe, Troll, and historical London dates.
  - Not a finding:
    - Library-driven offset handling with no hand-coded shift size.
  - Escalate (NEEDS-HUMAN): none specific beyond PA-36.
  - Proposed severity (for the user to decide): HIGH when a hardcoded
    one-hour shift drives scheduling, billing, or deadlines on a core
    path for zones with other shift sizes. MEDIUM for display and
    historical data. LOW for test-only code.
- PA-39: Bounded month-length assumption. Code assumes every month has
  28, 29, 30, or 31 days.
  - Overlap: PA-2 covers month lengths in general, including reform
    months, lunar months, and fiscal months. PA-39 adds month lengths
    outside 28 to 31, lengths not known in advance, region-dependent
    month boundaries, and month length in hours. Merged per the class ledgers.
  - Why it is false:
    - Shorter months:
      - The Ethiopian and Coptic 13th month (Pagume) has 5 or 6 days.
      - The Baha'i calendar has 19 months of 19 days, plus 4 or 5
        intercalary days.
      - The French Republican calendar (historical) had 5 or 6
        complementary days after 12 months of 30.
      - Reform months: October 1582 had 21 days, September 1752 in
        Britain had 19, and February 1918 in Russia had 15 (PA-2).
    - Longer months: 4-4-5 and similar fiscal calendars have 35-day
      periods. 13-period fiscal years use 28-day periods (PA-2).
    - Lengths not known in advance: observational Islamic calendars set
      each month's length (29 or 30) by moon sighting, announced on the
      29th evening. Computed variants such as Umm al-Qura differ from
      observed dates.
    - Region-dependent boundaries: countries following moon sighting can
      start the same Islamic month on different Gregorian days.
    - Month length in hours varies: a 31-day month containing a DST
      transition has 743 or 745 local hours (PA-1).
  - How it appears in code:
    - Assertions, enums, or validators that allow only 28 to 31
      (`assert 28 <= days <= 31`).
    - Day-of-month arrays or grids fixed at 28 to 31 slots, failing for 5,
      6, 19, or 35.
    - Non-Gregorian month lengths computed by fixed formula where the
      calendar is observational.
    - Month length in hours computed as `days * 24`.
  - What to check:
    - Hardcoded bounds on month length.
    - Which calendars the product supports, and whether each month
      length comes from that calendar's library.
    - Hour-based monthly calculations (billing, capacity, SLAs).
  - Fix:
    - Get month length from the calendar library for the specific month,
      calendar, and, where needed, region (BP-1). For example, ICU
      calendars and Java `java.time.chrono` (`HijrahChronology`,
      `JapaneseChronology`, `ThaiBuddhistChronology`, `MinguoChronology`).
    - For observational calendars, treat future month lengths as
      provisional and allow correction.
    - Compute hours in a month from instants at its local boundaries,
      not from `days * 24`.
  - Not a finding:
    - Gregorian-only products that validate 28 to 31 through a library
      days-in-month call.
  - Escalate (NEEDS-HUMAN): products using Islamic, Hebrew, Ethiopian,
    Baha'i, or fiscal calendars where the calendar variant (observed or
    computed, and for which region) is not stated.
  - Proposed severity (for the user to decide): HIGH when billing,
    payroll, or religious-observance dates on a core path depend on
    wrong month lengths. MEDIUM for display and reports. LOW for
    test-only code.
- PA-40: Contiguous date assumption. Code assumes the local day of the
  month always advances by one (or wraps to 1), never skipping or
  repeating a date.
  - Overlap: PA-2 and PA-39 cover reform months. PA-1 covers Samoa's
    missing day as a day-length issue. PA-40 covers local dates that are
    skipped or repeated, and code that iterates or expects every date.
    Merged per the class ledgers.
  - Why it is false (tzdata cases verified with tzdata 2026b):
    - Date-line moves skip a date:
      - Samoa (`Pacific/Apia`) and Tokelau (`Pacific/Fakaofo`): 2011-12-29
        is followed by 2011-12-31.
      - Kwajalein (`Pacific/Kwajalein`): 1993-08-20 is followed by
        1993-08-22.
      - The Philippines (`Asia/Manila`): 1844-12-30 is followed by
        1845-01-01.
    - Date-line moves can repeat a date: Alaska (`America/Sitka`) in 1867
      goes from 1867-10-19 back to 1867-10-18 in tzdata's proleptic
      Gregorian model, as Alaska moved from Russian to American dating.
    - Calendar reform skips dates: Britain went from 1752-09-02 to
      1752-09-14, and Catholic states from 1582-10-04 to 1582-10-15.
      Proleptic Gregorian libraries do not show these gaps (PA-2, PA-19).
    - Travelers and ships crossing the International Date Line skip or
      repeat a date in their own local reckoning.
  - How it appears in code:
    - Loops over local dates that assert each date is the previous date
      plus one.
    - Gap detection in time series that reports skipped dates as data
      loss.
    - Daily jobs, partitions, or reports keyed on local date that expect
      every date to exist exactly once. They fail or alert on a skipped
      date, or overwrite on a repeated one.
    - "Yesterday" computed as `today - 1 day` to find a partition that
      never existed locally.
    - Streak or consecutive-day logic that breaks on a skipped date or
      double-counts a repeated one.
    - Date iteration by adding 86400 seconds (PA-1).
  - What to check:
    - Logic that assumes local dates are contiguous and unique.
    - Daily partitioning and gap detection keyed on local dates.
    - Date iteration methods.
  - Fix:
    - Iterate local dates with the library's calendar-day operations in
      the relevant zone, and let the zone's history decide which dates
      exist (BP-1).
    - Key partitions on UTC dates, or tolerate missing and repeated
      local dates explicitly.
    - Treat gap detection results for zones with known date-line changes
      as expected, not as data loss.
    - For historical data, keep the original calendar and dates
      (PA-19).
  - Not a finding:
    - Modern-date products that iterate dates with library operations.
  - Escalate (NEEDS-HUMAN): consecutive-day rules (streaks, daily
    entitlements, interest accrual) whose spec does not say how skipped or
    repeated local dates count.
  - Proposed severity (for the user to decide): HIGH when daily billing,
    interest, or entitlement logic on a core path mishandles a skipped or
    repeated date. MEDIUM for reports, partitions, and gap alerts. LOW
    for test-only code.
- PA-41: Single-calendar assumption. Code assumes only one calendar
  system is in use at a time.
  - Overlap: PA-32 covers locale defaults that select non-Gregorian
    calendars in display. PA-39 covers month lengths in other calendars.
    PA-41 covers several calendars coexisting in one society, one user,
    or one system, and code that silently picks one. Merged per the class ledgers.
  - Why it is false:
    - Several calendars are in official or daily use alongside the
      Gregorian calendar:
      - Solar Hijri in Iran and Afghanistan (official civil calendar).
      - Islamic (Hijri) in Saudi Arabia and elsewhere for religious and
        some official purposes.
      - Ethiopian in Ethiopia, Bikram Sambat in Nepal, and the Hebrew
        calendar in Israel.
      - The Indian national calendar plus regional Hindu calendars in
        India.
      - Buddhist-era years in Thailand, Japanese era years in Japan, and
        Minguo years in Taiwan, on Gregorian months.
      - Chinese and Korean lunisolar dates for festivals and lunar
        birthdays.
    - One person often uses several: a Gregorian work calendar, a
      religious calendar for holidays, a lunar birthday.
    - Calendars coexisted historically: Julian and Gregorian ran side by
      side for centuries (Britain switched in 1752, Russia in 1918, Greece
      in 1923). Orthodox churches still keep Julian feast dates, so
      Orthodox Christmas falls on January 7.
    - Eras change. Japan moved from Heisei to Reiwa on 2019-05-01, so 2019
      is both Heisei 31 and Reiwa 1. Java renders 2019-04-30 as Heisei
      31 and 2019-05-01 as Reiwa 1 (verified). Software needed data
      updates for the new era.
    - Business calendars run alongside civil ones: fiscal 4-4-5 and ISO
      week calendars (PA-3, PA-6).
    - Users and devices choose a calendar. iOS lets users set a Buddhist
      or Japanese calendar system-wide. Java `Calendar.getInstance()`
      with a `th-TH` locale returns `BuddhistCalendar` (year 2568 for
      2025), and with the `ja-JP-JP` locale returns
      `JapaneseImperialCalendar` (year 7) (verified).
  - How it appears in code:
    - Default-calendar APIs (iOS `Calendar.current`, Java
      `Calendar.getInstance()`) used with fixed formats or year
      arithmetic. Users with a non-Gregorian setting produce wrong years
      in stored values, API payloads, and file names.
    - Annual events from another calendar (Hijri anniversaries, lunar
      birthdays, religious holidays) implemented as Gregorian annual
      repeats. Hijri dates drift about 11 days earlier each Gregorian
      year.
    - Static holiday tables that assume Gregorian-fixed dates for
      movable feasts (Easter, Orthodox Easter, Eid, Lunar New Year,
      Diwali).
    - Era names hardcoded, or era data left outdated.
    - Age counted by one system where users or law use another (Korean
      age counting, standardized to international age in Korean law in
      2023).
  - What to check:
    - Calls that pick up a default or user calendar.
    - Recurring events and holidays: which calendar defines them.
    - Year values sent to machines: which calendar they come from.
  - Fix:
    - Compute and store in one canonical system (ISO 8601, proleptic
      Gregorian) and convert at the edges.
    - For machine-facing formats, set the Gregorian calendar and a fixed
      locale explicitly (iOS: `Calendar(identifier: .gregorian)` with
      `en_US_POSIX`; Java: `java.time` ISO types or `Locale.ROOT`).
    - Compute recurrences and holidays in the calendar that defines them,
      using a library that supports it (ICU, Java `java.time.chrono`,
      `Intl` with a `calendar` option) (BP-1).
    - Keep the source calendar and original value where it matters.
    - Keep era and calendar data current (PA-35).
  - Not a finding:
    - Gregorian-only products that pin the Gregorian calendar and a fixed
      locale explicitly.
  - Escalate (NEEDS-HUMAN): products for markets that use another
    calendar, where the calendars to support for display, input,
    holidays, and recurrence are not stated.
  - Proposed severity (for the user to decide): HIGH when a user's
    calendar setting corrupts stored or transmitted dates on a core path,
    or when religious or legal dates are wrong. MEDIUM for display and
    holiday tables. LOW for test-only code.
- PA-42: Divisible-by-four leap rule assumption. Code assumes every year
  divisible by 4 is a leap year.
  - Overlap: PA-2 and PA-3 state the Gregorian rule briefly. PA-4 covers
    Excel's 1900 bug, which is this assumption. PA-42 covers the rule in
    depth, other calendars' rules, BC years, and range-limited
    implementations. Merged per the class ledgers.
  - Why it is false:
    - Gregorian rule: divisible by 4, except years divisible by 100,
      unless also divisible by 400. 1900 and 2100 are not leap years.
      2000 and 2400 are (verified with Python `calendar.isleap`).
    - The Julian calendar does use every fourth year. Code for Julian
      dates (historical records, Orthodox feasts) needs that rule, not
      the Gregorian one.
    - The Revised Julian calendar, used by some Orthodox churches, makes
      a century year leap only when the year divided by 900 leaves 200
      or 600. It first differs from Gregorian in 2800.
    - Other calendars have their own rules:
      - Hebrew: 7 leap months in each 19-year cycle.
      - Tabular Islamic: 11 leap days in each 30-year cycle.
      - Solar Hijri: leap years follow the observed equinox.
        Arithmetic cycle approximations disagree with it in some years.
      - Ethiopian: a leap year every 4 years, falling in the Ethiopian
        year before a Gregorian leap year.
      - Chinese lunisolar: leap months inserted by astronomical rule.
    - BC years: in astronomical numbering, year 0 and -4 are leap years
      (Java `Year.isLeap(0)` and `Year.isLeap(-4)` return true,
      verified). In historical numbering with no year 0, those are 1 BC
      and 5 BC. `year % 4` on BC numbers is off by one (PA-19).
  - How it appears in code:
    - `year % 4 == 0` or `(year & 3) == 0` as the full leap test.
      Correct only from 1901 to 2099.
    - Day counts using 365.25 days per year (PA-3).
    - Hardware or firmware with range-limited leap logic. Some real-time
      clock chips document leap-year compensation as valid only until
      2100 (for example the DS1307).
    - Gregorian leap logic applied to Julian, Hebrew, Islamic, or other
      calendar dates.
    - Leap tests applied to historical BC year numbers.
  - What to check:
    - Hand-written leap-year tests and 365.25 constants.
    - The calendar each leap test is meant for.
    - Documented valid date ranges for hardware clocks and firmware.
  - Fix:
    - Use the library's leap test (BP-1): Python `calendar.isleap`, Java
      `Year.isLeap`, .NET `DateTime.IsLeapYear`, Luxon
      `DateTime.isInLeapYear`. In Go or plain JS, construct February 29
      and check that the month is still February (verified for JS
      `Date.UTC`).
    - Use calendar libraries for non-Gregorian leap rules (PA-41).
    - Where range-limited logic is unavoidable (embedded clocks),
      document the valid range and enforce it.
    - Test 1900, 2000, 2100, 2400, and year 0 and negative years where
      supported.
  - Not a finding:
    - A `% 4` rule in code that handles only Julian-calendar dates and
      says so.
    - Range-limited logic whose documented range is enforced at input.
  - Escalate (NEEDS-HUMAN): firmware or devices expected to operate past
    2099 whose leap logic is range-limited.
  - Proposed severity (for the user to decide): HIGH when a wrong leap
    test drives billing, scheduling, expiry, or stored dates on a core
    path, or embedded devices in service past 2099. MEDIUM for display
    and historical data. LOW for test-only code.
- PA-43: No-leap-day assumption. Code assumes a Gregorian common
  (non-leap) year never contains a leap day or other inserted time.
  - Overlap: PA-4 covers Excel's phantom 1900-02-29. PA-42 covers leap
    rules in other calendars. PA-43 covers inserted days and time that
    land in Gregorian common years, and validators that reject them.
    Merged per the class ledgers.
  - Why it is false:
    - Julian-dated records: countries on the Julian calendar had
      February 29 in 1700, 1800, and 1900, which are common years in
      Gregorian. Britain used Julian until 1752 and Russia until 1918.
      Historical documents dated in the old style contain these dates.
    - Sweden's transition: Sweden skipped the leap day in 1700, then
      added February 30 in 1712 to return to the Julian calendar.
    - Spreadsheet epochs: Excel's 1900 date system contains 1900-02-29
      (PA-4).
    - Other calendars insert days in Gregorian common years. The
      Ethiopian leap day (Pagume 6) falls in the Gregorian year before a
      Gregorian leap year, for example September 2023, and Ethiopian New
      Year then moves from September 11 to September 12. Hebrew leap
      months follow a 19-year cycle unrelated to Gregorian leap years.
    - Leap seconds were inserted in common years, for example on
      2015-06-30 and 2005-12-31 (PA-20).
    - Fiscal and ISO week calendars add a 53rd week in years unrelated
      to Gregorian leap years. 2026 is a common year with an ISO week 53
      (PA-7, verified).
    - The reverse also happens: Sweden's 1700 was a leap year in the
      Julian calendar it followed, yet had no leap day.
  - How it appears in code:
    - Validators and parsers that reject February 29 in Gregorian common
      years when reading historical, Julian-dated, or Excel-sourced data.
    - Lenient parsers or APIs that silently turn such a date into
      March 1 (JS `Date`, Go `time.Date`; PA-2).
    - "53 weeks only in leap years" or "extra day only in leap years"
      logic in fiscal, ISO-week, or non-Gregorian code.
    - Leap-second handling that runs only in leap years or only on
      specific dates.
  - What to check:
    - Validation of February 29 and other inserted dates: by which
      calendar, and for which data sources.
    - Week-count and year-length logic tied to Gregorian leap years.
    - Import paths for historical or spreadsheet data.
  - Fix:
    - Validate each date in the calendar it is written in, with a
      calendar library (BP-1, PA-41). Store the source calendar.
    - Convert Excel serials with the spreadsheet library's conversion
      (PA-4).
    - Get week counts per year from the library, not from leap-year
      tests.
    - Read leap seconds from a maintained leap-second table (PA-13).
  - Not a finding:
    - Gregorian-only modern data validated with a library that rejects
      February 29 in common years.
  - Escalate (NEEDS-HUMAN): imports of historical or archival data where
    the source calendar of each date is not stated.
  - Proposed severity (for the user to decide): HIGH when valid
    historical or calendar-specific dates are rejected or silently
    shifted on a core path. MEDIUM for week-count and reporting logic.
    LOW for test-only code.
- PA-44: Simple time-offset assumption. Code assumes adding a number of
  hours and minutes to a point in time is simple arithmetic.
  - Overlap: PA-1 covers adding a day versus 24 hours. PA-38 covers
    shift sizes. PA-44 covers adding hours and minutes: what "add" means,
    how languages disagree, gaps and overlaps, time-of-day wrap, and
    business-hours arithmetic. Merged per the class ledgers.
  - Why it is false:
    - "Add 3 hours" has two meanings: 3 elapsed hours, or the wall clock
      moved forward 3 hours. Across a DST change they differ.
    - Languages disagree on the same expression. From 00:30 on
      2026-03-08 in New York, adding 3 hours gives (verified):
      - Java `ZonedDateTime.plusHours(3)`: 04:30 (3 elapsed hours).
      - JS `new Date(t + 3 * 3600000)`: 04:30 (elapsed).
      - JS `setHours(getHours() + 3)`: 03:30 (wall clock, 2 elapsed
        hours).
      - Python `aware + timedelta(hours=3)`: 03:30 (wall clock, 2 elapsed
        hours).
      - Java `LocalDateTime.plusHours(3)` then attaching the zone: 03:30.
    - Wall-clock results can land in a gap (a local time that does not
      exist) or an overlap (a local time that happens twice). Libraries
      resolve these differently: shift forward, pick the earlier offset,
      or raise.
    - Time-of-day types wrap silently. Java `LocalTime.of(22, 0)
      .plusHours(3)` is 01:00, with no record that the day changed
      (verified).
    - Business-time arithmetic ("4 business hours from now") must skip
      nights, weekends, regional holidays, and partial days, all in the
      right zone.
  - How it appears in code:
    - Hours added to zoned values without deciding elapsed versus
      wall-clock meaning, or with a language whose default is the other
      one.
    - Hours added to naive local values, ignoring transitions.
    - Hand-written `HH:MM` arithmetic with `% 24` or `% 60`. The date
      carry is lost: 22:00 plus 3 hours becomes 01:00 on the same date.
    - Time-of-day-only types used for spans that can cross midnight.
    - No handling for results in a gap or overlap.
    - Business-hours deadlines computed with plain hour addition or
      fixed working-day assumptions.
  - What to check:
    - Every hour or minute addition on zoned, local, or time-of-day
      values: intended meaning and actual language semantics.
    - String or modulo arithmetic on clock times.
    - Gap and overlap handling.
    - SLA and business-hours calculations.
  - Fix:
    - Decide the meaning first (PA-1). For elapsed time, add to the
      instant (UTC). For wall-clock time, use the library's zoned
      operation and state the gap and overlap policy (BP-1).
    - Know each language's default. In Python, convert to UTC, add,
      and convert back for elapsed time.
    - Use date-time types, not time-of-day types, when a span can cross
      midnight.
    - Never do clock arithmetic on strings or with modulo.
    - Compute business time with a library or service that holds the
      region's working hours and holidays.
  - Not a finding:
    - Elapsed-time addition on UTC instants where elapsed time is the
      requirement.
  - Escalate (NEEDS-HUMAN): SLAs, shift lengths, or deadlines stated in
    hours where the spec does not say elapsed or wall-clock, or whose
    business calendar is not defined.
  - Proposed severity (for the user to decide): HIGH when deadlines,
    SLAs, shifts, dosing or billing on a core path are computed with the
    wrong meaning or lose the date carry. MEDIUM for display and
    reminders. LOW for test-only code.
- PA-45: Location-independent month assumption. Code assumes a given
  month has the same number of days everywhere.
  - Overlap: PA-2, PA-39, and PA-40 cover reform months, sighted months,
    and skipped dates. PA-45 covers the same month differing by place,
    and global month tables. Merged per the class ledgers.
  - Why it is false:
    - Date-line moves: December 2011 had 30 local days in Samoa
      (`Pacific/Apia`) and 31 in Auckland (verified). August 1993 had
      30 days in Kwajalein. December 1844 had 30 days in the Philippines
      (PA-40).
    - Calendar reform happened in different years by country. October
      1582 had 21 days in Spain and the Italian states, and 31 in England.
      September 1752 had 19 days in Britain and its colonies, and 30 in
      France. February 1918 had 15 days in Russia. February 1923 had 15
      days in Greece.
    - Sighted Islamic months can have 29 days in one country and 30 in
      another (PA-39).
    - Local hours per month differ by zone: a month with a DST change has
      743 or 745 local hours in that zone and 744 in a zone without DST.
      Hemispheres change in different months (PA-33).
    - Local month boundaries are different instants in each zone (PA-7).
    - Fiscal months differ by organization (PA-2).
  - How it appears in code:
    - One global days-in-month table or call used for every region.
    - Monthly proration, billing, or capacity in hours computed once and
      applied to all regions.
    - Historical dates for a country computed in proleptic Gregorian, or
      with a library's default cutover. Java's legacy `GregorianCalendar`
      switches from Julian at 1582-10-15 by default, while `java.time` is
      proleptic Gregorian, so the two disagree for older dates. The
      legacy class also reports 31 as the maximum day of October 1582
      even though that month had only 21 days (verified).
    - Monthly reports comparing regions with one month definition.
  - What to check:
    - Days-in-month and hours-in-month calculations: are zone, region,
      and calendar inputs?
    - Historical date handling: which cutover is used for which country.
    - Use of maximum day-of-month as the number of days.
  - Fix:
    - Compute month length per zone, region, and calendar with the
      library and current tz data (BP-1, PA-41).
    - Compute hours in a month from the local month boundaries in that
      zone (PA-39).
    - For historical data, use per-country calendar adoption dates (for
      example `GregorianCalendar.setGregorianChange`, or ICU equivalents)
      and keep original dates (PA-19).
    - Count days by iterating dates, not by reading the maximum
      day-of-month.
  - Not a finding:
    - Single-region, modern-date products computing month length through
      the library.
  - Escalate (NEEDS-HUMAN): multi-region monthly billing or proration
    where the defining zone or region for "the month" is not stated.
  - Proposed severity (for the user to decide): HIGH when monthly
    billing, proration, or payroll on a core path uses a global month
    length for regions where it differs. MEDIUM for historical display
    and reports. LOW for test-only code.
- PA-46: Pure-seconds Unix time assumption. Code assumes Unix time is a
  plain count of elapsed seconds since 1970, independent of calendars,
  UTC, and leap seconds.
  - Overlap: PA-13 covers time-scale offsets (TAI, GPS). PA-20 covers
    leap seconds, smearing, and second 60. PA-23 and PA-18 cover units
    and range. PA-46 covers what Unix time actually is, and the errors
    that follow from treating it as pure elapsed seconds. Merged per the class ledgers.
  - Why it is false:
    - Unix time is defined from the UTC calendar. POSIX defines "seconds
      since the Epoch" by a formula over UTC year, day of year, hour,
      minute, and second, with every day exactly 86400 seconds. It is a
      calendar encoding, not a stopwatch.
    - Leap seconds are not counted. 27 leap seconds have been inserted
      since 1972 (TAI minus UTC went from 10 to 37 seconds). The
      difference of two Unix times across them undercounts elapsed SI
      seconds by that number.
    - A leap second has no Unix time of its own. Python
      `calendar.timegm` maps 2016-12-31 23:59:60 and 2017-01-01 00:00:00
      to the same value, 1483228800 (verified). The day containing that
      leap second still measures 86400 in Unix time (verified).
    - During a leap second, systems differ: the kernel may repeat a
      second, step the clock, or smear it (PA-20). Unix time can repeat
      or run at a different rate.
    - Before 1972, UTC used variable-length "rubber" seconds and steps,
      so Unix time before then does not map cleanly to elapsed seconds.
    - Unix time is UTC-based. Converting it to a local time needs a zone
      (PA-8).
    - Representations of a leap second fail: Python `datetime` rejects
      second 60, and JS `Date.parse("2016-12-31T23:59:60Z")` returns
      `NaN` (verified).
  - How it appears in code:
    - Exact elapsed SI seconds computed by subtracting Unix times across
      leap seconds, in scientific, navigation, or long-span metering
      code.
    - Unix time assumed strictly increasing, so IDs, ordering, or
      durations break during a leap second (PA-11).
    - Conversions between Unix time and TAI or GPS time by a constant
      (PA-13).
    - Inputs containing second 60 rejected or crashing (PA-20).
    - Smeared and strict Unix time from different sources compared
      directly (PA-20).
  - What to check:
    - Calculations that need exact physical durations over long spans.
    - Code that relies on Unix time never repeating.
    - Time-scale conversions, and handling of second 60 at input.
  - Fix:
    - Treat Unix time as an encoding of UTC civil time, not as elapsed
      physical seconds.
    - For exact SI intervals across leap seconds, convert to TAI or GPS
      time with a maintained leap-second table (for example Astropy
      `Time`, SOFA/ERFA), or read Linux `CLOCK_TAI` where it is
      configured (BP-1).
    - Measure durations with a monotonic clock (PA-11).
    - Accept second 60 at input and normalize it by a documented rule.
    - Use one smear policy across compared sources (PA-20).
  - Not a finding:
    - Ordinary business code where errors of up to one second per leap
      second do not matter.
  - Escalate (NEEDS-HUMAN): scientific, navigation, or regulated
    timestamping (for example EU MiFID II, which requires high-frequency
    trading clocks within 100 microseconds of UTC) where the required
    time scale and accuracy are not stated.
  - Proposed severity (for the user to decide): HIGH when exact
    durations, ordering, or regulated timestamps on a core path assume
    Unix time counts every second. MEDIUM for leap-second input handling.
    LOW for test-only code.
- PA-47: Loose Unix epoch definition. Code treats Unix time as simply
  the number of seconds since January 1, 1970, without the qualifiers
  that make the definition correct.
  - Overlap: PA-46 covers leap seconds. PA-19 covers other epochs.
    PA-23 covers units. PA-47 covers the epoch's zone, sign, and the
    places where "since January 1, 1970" is computed wrongly. Merged per the class ledgers.
  - Why it is false:
    - The epoch is 1970-01-01T00:00:00 UTC, not local midnight. In
      London, local midnight on 1970-01-01 was 1969-12-31T23:00Z, because
      the UK ran British Standard Time (UTC+1) all year from 1968 to 1971
      (verified: `mktime` there gives -3600).
    - Leap seconds are excluded (PA-46).
    - Values before 1970 are negative and valid (PA-18).
    - The unit varies: seconds, milliseconds, or finer (PA-23).
    - The C standard does not define `time_t` as seconds since 1970.
      POSIX does. Other platforms use other epochs (PA-19).
    - Databases differ: Postgres `EXTRACT(EPOCH FROM ...)` on a
      `timestamp without time zone` gives nominal seconds since
      1970-01-01 00:00 with no zone applied, while on `timestamptz` it
      gives true Unix time. MySQL `UNIX_TIMESTAMP(datetime)` interprets
      the argument in the session time zone.
  - How it appears in code:
    - Epoch computed from a local date: Python `time.mktime((1970,1,1,
      ...))` or naive `datetime(1970,1,1).timestamp()`, JS `new Date(1970,
      0, 1)`. In London these give -3600 seconds instead of 0 (verified).
    - "Epoch seconds" computed as naive local now minus naive
      `datetime(1970,1,1)`. The result is off by the current offset:
      +3600 in London and -14400 in New York on 2026-10-03 (verified).
    - Java `LocalDateTime.toEpochSecond(offset)` given the wrong offset.
    - SQL epoch extraction on zone-less columns, or through a session
      zone, mixed with true Unix times.
    - Validators rejecting negative epoch values.
  - What to check:
    - Hand-built epoch constants and epoch arithmetic.
    - Epoch conversions from naive or local values.
    - Database epoch functions and the column types and session zones
      they run against.
  - Fix:
    - Get Unix time from the library's instant APIs (Python
      `datetime.now(timezone.utc).timestamp()` or `time.time()`, Java
      `Instant.getEpochSecond()`, JS `Date.now()`) (BP-1).
    - Convert local values to instants with an explicit zone before
      taking epoch values.
    - Use `timestamptz` and set the session zone before extracting epoch
      values in SQL (PA-10).
    - Allow negative values where the domain includes pre-1970 dates.
  - Not a finding:
    - Epoch values taken from instant APIs and documented with their
      unit.
  - Escalate (NEEDS-HUMAN): stored epoch values whose producing code and
    zone handling cannot be established.
  - Proposed severity (for the user to decide): HIGH when locally
    computed epochs shift stored or transmitted times on a core path.
    MEDIUM for reports. LOW for test-only code.
- PA-48: Fixed weekday sequence assumption. Code assumes weekdays always
  follow in order, so the day before a Saturday is always a Friday.
  - Overlap: PA-40 covers skipped and repeated dates. PA-48 covers the
    weekday side: skipped and repeated weekdays, weekday numbering, zone
    dependence, and weekday arithmetic. Merged per the class ledgers.
  - Why it is false (weekdays verified with Python `date`):
    - Date-line moves skip or repeat weekdays:
      - Samoa: Thursday 2011-12-29 was followed by Saturday 2011-12-31.
        The day before that Saturday was a Thursday.
      - Kwajalein: Friday 1993-08-20 was followed by Sunday 1993-08-22.
      - Philippines: Monday 1844-12-30 was followed by Wednesday
        1845-01-01.
      - Alaska 1867: the change from Russian to American dating repeated
        a day (PA-40).
    - Calendar reform kept the weekday sequence but jumped the date:
      Thursday 1582-10-04 (Julian) was followed by Friday 1582-10-15
      (Gregorian). Proleptic Gregorian libraries call 1582-10-04 a Monday
      (verified), so weekdays computed for Julian-dated records are wrong.
    - Other week systems existed: the Soviet Union used 5-day and 6-day
      weeks from 1929 to 1940, and the French Republican calendar used
      10-day weeks.
    - Weekday depends on zone. One instant is Friday in one zone and
      Saturday in another, so a weekday taken from a UTC date is wrong for
      many users (PA-17).
    - Weekday numbering differs by platform:
      - ISO 8601 and Java `DayOfWeek`: Monday = 1 to Sunday = 7.
      - Python `weekday()`: Monday = 0. `isoweekday()`: Monday = 1.
      - JS `getDay()`, .NET `DayOfWeek`, Postgres `EXTRACT(DOW)`:
        Sunday = 0.
      - MySQL `DAYOFWEEK`: Sunday = 1. MySQL `WEEKDAY`: Monday = 0.
      - SQL Server `DATEPART(weekday)` depends on `SET DATEFIRST`.
      - cron: Sunday is 0 or 7.
    - Weekend days vary by country: Friday and Saturday in several
      Middle Eastern countries, Saturday and Sunday in most others, and a
      single day in some. The UAE moved from Friday-Saturday to
      Saturday-Sunday in 2022.
  - How it appears in code:
    - Weekday arithmetic by modulo: `(day - 1) % 7` gives -1 for
      Sunday = 0 in JS, Java, and C, but 6 in Python (verified).
    - "Previous business day" coded as "if Saturday, use Friday".
    - Weekday numbers passed between systems with different numbering.
    - Weekday taken from a UTC date or the server's date instead of the
      user's local date.
    - Weekdays computed for historical dates with proleptic Gregorian
      rules.
    - Weekends hardcoded as Saturday and Sunday.
  - What to check:
    - Arithmetic on weekday numbers.
    - Weekday enums at system boundaries, including SQL and cron.
    - The zone and calendar used to derive each weekday.
    - Business-day and weekend logic.
  - Fix:
    - Do date arithmetic first, then ask the library for the weekday of
      the resulting local date in the relevant zone and calendar (BP-1).
    - Map weekday conventions explicitly at every boundary, or exchange
      weekday names or ISO numbers.
    - Use a business-day calendar per region, with its weekend and
      holidays.
    - Keep historical dates in their original calendar (PA-41).
  - Not a finding:
    - Library-derived weekdays for modern local dates.
  - Escalate (NEEDS-HUMAN): business-day rules for multi-country
    products where the weekend and holiday calendars are not stated.
  - Proposed severity (for the user to decide): HIGH when settlement,
    payroll, delivery, or deadline dates on a core path use the wrong
    weekday or business day. MEDIUM for display and reports. LOW for
    test-only code.
- PA-49: Adjacent-zone assumption. Code assumes neighboring time zones
  are at most one hour apart.
  - Overlap: PA-33 covers differences between zones changing through the
    year. PA-49 covers the size of differences between neighbors, the
    range of offsets, and deriving zones from geography. Merged per the class ledgers.
  - Why it is false (offsets verified with tzdata 2026b):
    - China uses UTC+8 across its whole territory. Its neighbors include
      Afghanistan (+04:30, a 3.5-hour difference at the border), Pakistan
      (+05:00, 3 hours), Kazakhstan (+05:00, 3 hours), India (+05:30,
      2.5 hours), and Nepal (+05:45, 2 hours 15 minutes).
    - Across the date line, neighbors are about a day apart. Samoa
      (+13:00) and American Samoa (-11:00) are 24 hours apart. Kiribati's
      Line Islands (+14:00) and Hawaii (-10:00) are 24 hours apart.
    - Norway (+01:00 winter) and Russia's Murmansk region (Moscow time,
      +03:00) differ by 2 hours in winter and 1 in summer.
    - Neighbors can share an offset, and offsets do not follow longitude:
      Spain uses Central European Time although it lies mostly west of
      Greenwich, while Portugal uses UTC+0.
    - Zones nest: the Hopi Reservation (no DST) sits inside the Navajo
      Nation (DST), which sits inside Arizona (no DST).
    - Offsets are not 24 one-hour bands. They range from -12:00 to +14:00
      (a 26-hour span) and include half-hour and 45-minute values
      (PA-33).
  - How it appears in code:
    - Offset validation limited to -12 to +12, or to whole hours.
    - A fixed list of 24 zones, or zone pickers in one-hour steps.
    - Zone guessed from longitude (`round(longitude / 15)`).
    - Travel, logistics, or ETA logic assuming a border crossing changes
      the clock by at most one hour.
    - Fallback to a "nearby" offset when a user's zone is unknown.
  - What to check:
    - Offset ranges and step sizes in validators and pickers.
    - Any derivation of zone from coordinates or region names.
    - Border-crossing or multi-region time logic.
  - Fix:
    - Accept the full offset range and minute-level offsets. Store IANA
      zone IDs (PA-9).
    - Derive zones from coordinates with a maintained time-zone boundary
      dataset (for example the timezone-boundary-builder data) through a
      library, never from longitude. Adding such a library needs user
      approval under the dependency rules.
    - Convert per zone through instants for every crossing (PA-33).
    - Ask for the user's zone when it is unknown instead of guessing.
  - Not a finding:
    - Zone handling through IANA IDs and library conversions.
  - Escalate (NEEDS-HUMAN): location-based zone assignment where the
    source of zone boundaries is not stated.
  - Proposed severity (for the user to decide): HIGH when logistics,
    scheduling, or deadlines on a core path assume small neighbor
    differences or derive zones from longitude. MEDIUM for pickers and
    display. LOW for test-only code.
- PA-50: Untested date-line crossing assumption. Teams assume nothing
  needs testing for systems or devices that cross the International Date
  Line in flight or at sea.
  - Overlap: PA-9 covers a user's zone changing. PA-40 and PA-48 cover
    skipped and repeated dates for places. PA-49 covers neighbors a day
    apart. PA-50 covers moving devices and travel data that cross the
    date line, and the testing gap. Merged per the class ledgers.
  - Why it is false:
    - Phones, laptops, and in-flight or shipboard systems change zone on
      arrival or in transit. Across the date line the local date jumps
      forward or backward by a day.
    - Travelling east across the line, the local date goes backward. A
      flight leaving Tokyo at 21:00 on 2026-01-10 and flying 7 hours
      lands in Honolulu at 09:00 on 2026-01-10, twelve local hours
      "before" it left (verified).
    - The date line is not straight. It bends around Kiribati, Samoa,
      and other island groups, so only zone data can say which side a
      place is on (PA-49).
    - Aviation and shipping use UTC operationally, but passengers, crew
      apps, and consumer devices use local time.
  - How it appears in code:
    - "Arrival must be after departure" validated on local times. Valid
      eastbound flights fail.
    - Durations computed from local times, giving negative or 24-hour-off
      results.
    - Booking logic assuming arrival date equals departure date or the
      next day.
    - "Today", streaks, and daily limits recomputed after a zone change,
      so a day is lost, repeated, or counted twice (PA-40).
    - Reminders, alarms, and medication schedules set in device wall
      time that fire twice, never, or a day off after crossing.
    - Local-date-keyed caches, files, or records colliding or splitting
      after the date moves backward.
    - Tests that never change the zone during a run.
  - What to check:
    - Comparisons and durations computed on local times from different
      zones.
    - Behavior when the device zone changes mid-session.
    - Wall-clock versus interval semantics for reminders and dosing.
    - Test coverage for zone changes across the date line in both
      directions.
  - Fix:
    - Compare and subtract instants, never local times from different
      zones.
    - Store the zone with each event (departure zone, arrival zone,
      recorded zone).
    - Define reminder and dosing semantics explicitly: fixed interval
      (elapsed) or local wall-clock time (PA-44).
    - Listen for zone-change events and recompute "today" and pending
      schedules by a documented rule.
    - Test with simulated zone jumps across the line in both directions,
      for example `Asia/Tokyo` to `Pacific/Honolulu`, and
      `Pacific/Kiritimati` (+14:00) to `Pacific/Pago_Pago` (-11:00).
  - Not a finding:
    - Server-side systems that work only in UTC instants and never derive
      local dates.
  - Escalate (NEEDS-HUMAN): daily entitlements, streaks, or medication
    schedules whose spec does not define behavior when the user's local
    date jumps.
  - Proposed severity (for the user to decide): HIGH for medication or
    dosing schedules, travel bookings, and financial daily limits that
    break on a crossing. MEDIUM for streaks, reminders, and display. LOW
    for test-only code.
- PA-51: Offset granularity assumption. Code assumes any two zones differ
  by a whole number of half hours, quarter hours, or seconds.
  - Overlap: PA-33 and PA-49 cover 30- and 45-minute offsets. PA-19
    covers LMT. PA-51 covers offsets at second and sub-second
    granularity, and representations that cannot hold them. Merged per the class ledgers.
  - Why it is false (tzdata values verified with Python `zoneinfo`):
    - Historical offsets have seconds: New York LMT -04:56:02, Dublin Mean
      Time -00:25:21 (until 1916), Monrovia -00:44:30 (until 1972).
    - Some official offsets had fractions of a second. Amsterdam time was
      UTC+00:19:32.13 until 1937. tzdata cannot store the fraction and
      records +00:19:32.
    - UTC itself differs from UT1 (Earth-rotation time) by a fraction of
      a second (DUT1, kept under 0.9 s). Smeared clocks differ from
      strict UTC by fractions during a smear (PA-20).
  - Representations that cannot hold these offsets:
    - ISO 8601 / RFC 3339 offsets in common use carry hours and minutes
      only. Python's `isoformat()` emits `-04:56:02`, which many parsers
      reject (verified).
    - JS `getTimezoneOffset()` returns 296 minutes for New York in 1880,
      and `toString()` shows `GMT-0456`. The 2 seconds are lost
      (verified).
    - .NET `DateTimeOffset` requires whole-minute offsets within +/-14
      hours, and throws otherwise.
    - SQL Server `datetimeoffset` stores the offset in minutes.
    - Python before 3.7 required whole-minute UTC offsets.
  - How it appears in code:
    - Offsets stored as integer hours, half hours, quarter hours, or
      minutes.
    - Offsets formatted as `+HH:MM`, so historical values lose seconds and
      do not round-trip.
    - Parsers that accept only `+HH:MM` rejecting `+HH:MM:SS`.
    - Historical-date conversions crashing in .NET or truncating in JS.
  - What to check:
    - Offset types, column types, and formats.
    - Handling of pre-1970 local times (PA-19).
  - Fix:
    - Store IANA zone IDs and UTC instants. Recompute offsets from the
      zone instead of storing them (PA-9).
    - Where offsets must be stored, use seconds (Java `ZoneOffset`
      supports seconds up to +/-18 hours).
    - Accept `+HH:MM:SS` offsets at input where historical data is in
      scope.
    - Document truncation where a platform cannot represent the offset.
  - Not a finding:
    - Modern-date systems whose zones all have whole-minute offsets, with
      a documented date range.
  - Escalate (NEEDS-HUMAN): historical, genealogical, or archival products
    on platforms limited to whole-minute offsets.
  - Proposed severity (for the user to decide): HIGH when historical
    conversions crash or corrupt stored values on a core path. MEDIUM for
    display and round-trip loss. LOW for test-only code.
- PA-52: Constant standard-offset assumption. Code assumes that, setting
  DST aside, the difference between two zones never changes.
  - Overlap: PA-9 lists rule changes, mostly DST-related. PA-33 covers
    DST-driven differences. PA-52 covers changes to standard (non-DST)
    offsets, the ambiguity of what counts as DST, and zone identifiers
    that change. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b):
    - Standard offsets change:
      - North Korea (`Asia/Pyongyang`): +09:00, then +08:30 from 2015,
        then +09:00 again from 2018.
      - Venezuela (`America/Caracas`): -04:00, then -04:30 from 2007,
        then -04:00 again from 2016.
      - Russia (`Europe/Moscow`): +03:00, then +04:00 all year from 2011,
        then +03:00 again from 2014.
      - Turkey (`Europe/Istanbul`): winter +02:00 until 2016, then +03:00
        all year.
      - Yukon (`America/Whitehorse`): winter -08:00 until 2020, then
        -07:00 all year.
      - Samoa moved from -11:00 to +13:00 in 2011. Kazakhstan and
        Greenland changed in 2023 and 2024 (PA-9).
    - "Ignoring DST" is ambiguous. tzdata's main format models Ireland's
      winter time and Morocco's Ramadan time as negative DST. Other builds
      model them the other way. On this host, Morocco's standard offset
      (offset minus DST) reads +00:00 in both February and July
      (verified). The "standard" difference depends on the data format.
    - Zone identifiers change. Zones split when part of a region changes
      rules (`America/Ciudad_Juarez` was created in 2022). Zones are
      renamed (`Europe/Kiev` became `Europe/Kyiv` in 2022, and
      `Asia/Calcutta` became `Asia/Kolkata` earlier). Old names survive
      only as backward-compatibility links, and not every installation
      ships them. This host cannot load `Europe/Kiev` or `Asia/Calcutta`
      (verified).
  - How it appears in code:
    - Standard offsets stored per zone, or hardcoded, and reused for all
      dates.
    - "Standard offset" computed as offset minus DST and treated as fixed.
    - Historical conversions using today's standard offset.
    - Stored legacy zone names that fail to load after an upgrade or on a
      minimal image.
    - Zone lists that miss newly split zones.
  - What to check:
    - Stored or hardcoded standard offsets.
    - Logic that depends on separating DST from standard time.
    - Stored zone IDs: canonical names, and handling of names that fail to
      load.
  - Fix:
    - Ask the library for the full offset at each instant. Do not split it
      into standard and DST parts for business logic (BP-1).
    - Canonicalize zone IDs on input and migrate stored legacy names.
      Ship the backward-compatibility links where legacy data exists.
    - Refresh zone lists from current tz data (PA-35).
  - Not a finding:
    - Full-offset handling through the library with canonical zone IDs.
  - Escalate (NEEDS-HUMAN): stored zone IDs or offsets whose meaning for
    past dates cannot be established.
  - Proposed severity (for the user to decide): HIGH when fixed standard
    offsets or unloadable zone IDs corrupt or reject stored times on a
    core path. MEDIUM for historical display. LOW for test-only code.
- PA-53: Consecutive-read equality assumption. Code assumes two date
  objects created one right after the other represent the same time.
  - Overlap: PA-25 covers several reads of "now" in one operation as a
    testability issue. PA-53 covers why back-to-back reads differ and the
    boundary bugs that follow. Merged per the class ledgers.
  - Why it is false:
    - The clock advances between reads. In a tight loop on this host,
      about 49 of 1,000,000 back-to-back JS `Date.now()` pairs differed,
      and about 21% of 100,000 back-to-back Python `datetime.now()` pairs
      differed (microsecond resolution) (verified, host-dependent).
    - Preemption, garbage collection, or I/O between the reads can make
      the gap arbitrarily large (PA-21).
    - The clock can step between the reads, so the second can be earlier
      than the first (PA-11).
    - Different clock sources read "now" differently: application versus
      database `NOW()`, wall clock versus monotonic clock (PA-14, PA-25).
    - Object identity is not value equality. In JS, `new Date(0) == new
      Date(0)` is `false` because objects compare by reference (verified).
  - How it appears in code:
    - Date and time components taken from separate reads. At 23:59:59.999
      the date comes from one day and the time from the next, giving a
      result a day off. The same happens with year and month at New Year.
      For example, `date = today()` followed by `time = now().time()`.
    - "Start" and "end" of one operation read separately where they should
      be equal.
    - Tests asserting equality between two `now()` calls. They fail
      intermittently.
    - Cache keys, IDs, or partition names derived from separate reads in
      one request.
    - JS date comparisons with `==` or `===` on Date objects.
  - What to check:
    - Multiple reads of the clock within one operation whose results are
      combined or compared.
    - Equality comparisons on date objects.
  - Fix:
    - Read the clock once per operation and derive every component from
      that one value (PA-25).
    - Compare values, not objects (JS `getTime()`, or library equality
      methods).
    - Where two reads are intended, compare with an explicit tolerance and
      handle the second being earlier.
    - Use a fixed or fake clock in tests (PA-25).
  - Not a finding:
    - Separate reads used only to measure elapsed time with a monotonic
      clock.
  - Escalate (NEEDS-HUMAN): none specific.
  - Proposed severity (for the user to decide): HIGH when separate reads
    produce off-by-one-day or off-by-one-period values that are stored or
    acted on in a core path. MEDIUM for flaky tests and logs. LOW for
    test-only code.
- PA-54: Exact-time polling assumption. Code assumes it can catch the
  clock reading exactly `HH:MM:SS` by checking once a second.
  - Overlap: PA-21 and PA-22 cover delayed, throttled, and paused timers.
    PA-11 covers clock jumps. PA-1 and PA-36 cover DST gaps and overlaps.
    PA-54 covers equality-based polling for a target time, and scheduling
    in general. Merged per the class ledgers.
  - Why it is false:
    - Samples drift and jitter. `sleep(1)` plus the work in each loop takes
      more than a second, so samples slide and eventually skip a second
      (for example :59.999, then :01.001).
    - Timers are delayed, throttled, or paused by load, garbage collection,
      background tabs, and suspension (PA-21, PA-22).
    - The clock can step forward past the target or backward to repeat it
      (PA-11).
    - Local target times may not exist or may happen twice: 02:30 is
      skipped on a spring-forward day and repeated on a fall-back day in
      many zones (PA-1, PA-36). In Santiago, midnight is skipped on the
      spring-forward day (PA-36).
    - Leap seconds and smearing affect the target second (PA-20).
  - How it appears in code:
    - Loops such as `while now().strftime("%H:%M:%S") != "09:00:00":
      sleep(1)`.
    - Triggers like `if now.minute == 0 and now.second == 0`.
    - Hand-written schedulers using `setInterval(check, 1000)` with an
      equality check.
    - No record of whether an occurrence already fired, so a repeated time
      fires twice.
    - No policy for missed occurrences.
  - What to check:
    - Equality comparisons between "now" and a target time.
    - Hand-written polling schedulers.
    - Handling of skipped, repeated, and missed occurrences.
  - Fix:
    - Compute the target instant for each occurrence in its zone, with a
      stated rule for gaps and overlaps (BP-1).
    - Fire when `now >= target` and the occurrence has not fired yet.
      Record each fired occurrence so it runs exactly once.
    - Sleep until the target (`target - now`), then re-check on wake and
      re-arm if early (PA-22).
    - Define a missed-run policy: run once late, skip, or coalesce
      (PA-12).
    - Prefer an established scheduler with an explicit zone and missed-run
      handling over hand-written loops. Schedulers differ on DST: Vixie and
      ISC cron document special handling for clock changes under 3 hours
      (skipped jobs run right after the change, repeated jobs run once).
      Verify the chosen scheduler's behavior. Adding a scheduling library
      needs user approval under the dependency rules.
  - Not a finding:
    - Polling with `>=` comparisons and a recorded fired state.
  - Escalate (NEEDS-HUMAN): jobs scheduled at local times inside DST
    gaps or overlaps where the spec does not say whether to skip, run
    once, or run twice.
  - Proposed severity (for the user to decide): HIGH when financial,
    legal, or safety jobs can be skipped or run twice. MEDIUM for
    reminders and maintenance tasks. LOW for test-only code.
- PA-55: Runtime equals elapsed time assumption. Code assumes that if a
  process runs for `n` seconds, about `n` seconds pass on the system
  clock by the time it ends.
  - Overlap: PA-11 covers wall-clock jumps. PA-20 to PA-22 cover rate
    differences, stopped clocks, and long gaps. PA-55 covers the
    confusion between CPU time, elapsed time, and wall-clock difference
    for a process's runtime. Merged per the class ledgers.
  - Why it is false:
    - CPU time and elapsed time differ. A process waiting on I/O, sleeping,
      or descheduled uses little CPU time while elapsed time grows: a
      `sleep(1)` used 0.0 s of CPU over 1.0 s of elapsed time (verified).
    - Parallel work uses more CPU time than elapsed time: three busy
      processes for 1 second of elapsed time used about 3 seconds of user
      CPU time (verified on a 4-core host).
    - Container CPU limits and CPU starvation stretch elapsed time for the
      same CPU work (PA-21).
    - The wall clock can step, slew, or smear during the run, so the
      wall-clock difference between start and end is not the elapsed time
      (PA-11, PA-20). It can even be negative.
    - Suspension, VM pause, or a stopped process add wall-clock time that a
      sleep-excluding monotonic clock does not count (PA-20, PA-22).
  - How it appears in code:
    - Runtime measured as the difference of two wall-clock readings
      (`time.time()`, `Date.now()`, `System.currentTimeMillis()`).
    - CPU time and elapsed time used interchangeably in throughput,
      billing, quotas, or performance reports.
    - Timeouts based on CPU time (`RLIMIT_CPU`) for I/O-bound work, which
      never trigger, or elapsed-time limits used where CPU budgets were
      intended.
    - ETA or progress estimates mixing the two.
  - What to check:
    - Which clock each runtime measurement uses, and which kind of time
      the requirement needs.
    - Timeouts and resource limits: CPU or elapsed.
    - Billing and quota calculations based on runtime.
  - Fix:
    - Decide whether the requirement is elapsed time or CPU time.
    - Measure elapsed time with a monotonic clock, choosing whether
      suspension counts (Python `time.perf_counter()` or
      `time.monotonic()`, Java `System.nanoTime()`, Go `time.Since`)
      (PA-11, PA-20).
    - Measure CPU time with CPU-time APIs (Python `time.process_time()`,
      `getrusage`, `clock_gettime(CLOCK_PROCESS_CPUTIME_ID)`).
    - Record wall-clock start and end separately for audit, not for
      duration.
  - Not a finding:
    - Elapsed-time measurements with a monotonic clock where elapsed time
      is the requirement.
  - Escalate (NEEDS-HUMAN): billing or quota rules stated as "runtime"
    without saying CPU time or elapsed time.
  - Proposed severity (for the user to decide): HIGH when billing,
    quotas, or safety timeouts on a core path use the wrong kind of time
    or wall-clock differences. MEDIUM for performance reports and ETAs.
    LOW for test-only code.
- PA-56: Monday week-start assumption. Code assumes every week starts on
  Monday.
  - Overlap: PA-5 and PA-6 mention locale week starts. PA-3 and PA-7
    cover ISO week-years. PA-48 covers weekday numbering. PA-56 covers
    week-start conventions in full, and inconsistent week definitions
    across layers of one system. Merged per the class ledgers.
  - Why it is false:
    - Week start varies by locale. Node `Intl.Locale` week info
      (CLDR data) gives (verified):
      - Monday: `en-GB`, `de-DE` (with ISO's minimum of 4 days in week 1).
      - Sunday: `en-US`, `he-IL`, `ja-JP`, `pt-BR`, `en-IN` (minimum 1
        day in week 1).
      - Saturday: `ar-EG`, `fa-IR`.
      - Friday: `dv-MV` (Maldives).
    - Week numbering differs with the start day and the minimum days in
      week 1. Sunday 2026-01-04 is week 01 under Python `%U` (Sunday
      start), week 00 under `%W` (Monday start), and ISO week 01 under
      `%V` (verified).
    - Tools default differently:
      - Postgres `date_trunc('week', ...)`: ISO, Monday.
      - MySQL `WEEK()`: mode from `default_week_format`, default 0
        (Sunday start).
      - SQL Server: depends on `SET DATEFIRST` (7, Sunday, for
        `us_english`).
      - BigQuery `DATE_TRUNC(..., WEEK)`: Sunday. `WEEK(MONDAY)` and
        `ISOWEEK` are separate parts.
      - Excel `WEEKNUM`: Sunday by default. `ISOWEEKNUM`: ISO.
      - Luxon `startOf('week')`: Monday (ISO) unless `useLocaleWeeks`.
      - date-fns `startOfWeek`: Sunday by default (`weekStartsOn: 0`).
      - moment `startOf('week')`: locale-dependent.
    - Users may set their own week start in their OS or the product.
  - How it appears in code:
    - Week start hardcoded to Monday (or Sunday) for all users.
    - Database weekly buckets and application weekly buckets using
      different starts, so weekly totals disagree between layers.
    - Week numbers from one convention labeled or joined with another.
    - "This week" filters using a different start from the calendar UI.
  - What to check:
    - Every layer that computes week starts or week numbers: database,
      backend, frontend, spreadsheets, BI tools.
    - Defaults relied on implicitly.
    - Whether the user's or locale's week start is honored where the
      product promises it.
  - Fix:
    - Choose the week definition per feature: ISO, locale, or user
      preference. State it in the requirement.
    - Configure it explicitly in every layer (function arguments, modes,
      library options), never relying on defaults (BP-1).
    - Use the same definition for bucketing and labeling across the
      stack.
    - Test boundaries on Friday, Saturday, Sunday, and Monday, and at year
      boundaries (PA-7).
  - Not a finding:
    - A documented, explicitly configured week definition used
      consistently across layers.
  - Escalate (NEEDS-HUMAN): weekly reports, payroll weeks, or calendar
    views in multi-locale products where the week definition is not
    stated.
  - Proposed severity (for the user to decide): HIGH when weekly payroll,
    billing, or regulated reports on a core path use inconsistent week
    definitions. MEDIUM for calendar UIs and analytics. LOW for test-only
    code.
- PA-57: Day-boundary assumption. Code assumes a day begins in the
  morning, or at local midnight, for every purpose.
  - Overlap: PA-36 covers a skipped local midnight. PA-17 covers whose
    zone defines "today". PA-57 covers day boundaries that are not
    midnight: religious, astronomical, operational, and cultural days.
    Merged per the class ledgers.
  - Why it is false:
    - Calendar days start at midnight, not in the morning, and some local
      midnights do not exist (PA-36).
    - Religious days start at sunset: the Hebrew and Islamic days, and
      observances such as the Sabbath from Friday sunset.
    - The astronomical day began at noon until 1925. Julian Day numbers
      still start at noon UTC. The Modified Julian Date starts at midnight
      (`MJD = JD - 2400000.5`).
    - Operational days use their own cutoffs:
      - Hotel nights run from afternoon check-in to next-day checkout.
      - Exchange trading days often open the previous evening (for
        example CME Globex sessions).
      - Casino "gaming days", bank cutoffs, and retail business dates
        close at set hours after midnight.
      - Broadcast days run, for example, from 06:00 to 05:59. Japanese TV
        listings write late-night slots as `25:30`.
      - Night shifts belong to the day they start.
    - Transit data counts past midnight. GTFS `stop_times` allow times
      above `24:00:00` for trips after midnight on the same service day,
      measured from "noon minus 12 hours", which differs from midnight on
      DST change days.
    - Some cultures count hours from dawn. Swahili time counts the first
      hour after about 06:00 as hour one.
    - Near the poles, "morning" does not happen daily during polar day and
      polar night.
    - Users think of late-night activity as part of the previous day.
      Sleep and fitness apps often treat 01:00 as "last night".
  - How it appears in code:
    - Business days, service days, or trading days cut at midnight.
    - Parsers that reject `24:00` or `25:30` from schedules and transit
      feeds, or wrap them to the wrong date.
    - GTFS times treated as clock times of day.
    - Religious-calendar features that switch dates at midnight.
    - Julian Day conversions off by half a day.
    - Daily user metrics reset at midnight against the product's promise.
  - What to check:
    - Every "day" concept in the domain, and where its boundary is
      defined.
    - Parsing of schedule times at or past 24:00.
    - Julian Day and MJD conversions.
  - Fix:
    - Model each domain day explicitly (business date, service day,
      gaming day, broadcast day) with a configured cutoff and zone.
    - Parse domain formats by their specs. For GTFS, compute times from
      noon minus 12 hours on the service date.
    - Compute sunset-based days with an astronomy library and the
      location.
    - Convert Julian Days with a library (BP-1).
    - Offer a configurable day boundary where the product promises
      "your day".
  - Not a finding:
    - Midnight-bounded calendar days where the domain uses calendar days.
  - Escalate (NEEDS-HUMAN): domain day concepts whose cutoff time and zone
    are not stated.
  - Proposed severity (for the user to decide): HIGH when settlements,
    hotel billing, trading, transit schedules, or religious observance
    dates on a core path use the wrong day boundary. MEDIUM for user
    metrics and display. LOW for test-only code.
- PA-58: Whole-day holiday assumption. Code assumes holidays always span
  a whole number of full days.
  - Overlap: PA-41 covers movable holidays from other calendars. PA-48
    covers regional weekends. PA-57 covers sunset-based days. PA-58
    covers holiday shape: partial days, sunset-to-sunset spans, regional
    scope, ad hoc declarations, and swapped workdays. Merged per the class ledgers.
  - Why it is false:
    - Half days: many employers and countries close at midday on
      December 24 and 31. US stock exchanges close early (13:00 Eastern)
      on some days, such as the day after Thanksgiving.
    - Sunset-to-sunset holidays: Jewish holidays and the Sabbath run from
      sunset to nightfall. Yom Kippur lasts about 25 hours. Islamic
      holidays begin at sunset after a sighting (PA-39, PA-57).
    - DST inside holidays: Easter Sunday 2024 (March 31) was also the EU
      DST start, so that holiday lasted 23 hours in Berlin (verified).
    - Regional scope: holidays differ by state, province, canton, or city
      (German states, Swiss cantons, US states).
    - Ad hoc holidays are declared with short notice, for example the UK
      bank holiday for the state funeral on 2022-09-19, announced about
      ten days ahead. Moon-sighted holidays are confirmed only the day
      before.
    - Substitute and swapped days: holidays on weekends move to observed
      weekdays. Some countries make weekend days into working days to
      bridge holidays (China's adjusted working days).
    - Different calendars for different purposes: bank holidays,
      exchange holidays, school holidays, and company holidays differ.
    - Floating or personal holidays apply only to some employees.
    - A company-wide holiday falls at different instants in each office's
      zone (PA-17).
  - How it appears in code:
    - Holiday tables as plain lists of dates, and `is_holiday(date)`
      returning a boolean.
    - Business-hours and SLA calculations that pause only for whole
      holiday dates.
    - Market calendars without early closes.
    - One global holiday list with no regional scope.
    - Static holiday lists with no update path for ad hoc holidays.
    - Weekend days always treated as non-working, missing swapped
      workdays.
    - Holiday pay computed as `days * 24` or by fixed hours per day.
  - What to check:
    - The holiday data model: dates only, or intervals with zone, region,
      and purpose.
    - Source and update process for holiday data.
    - Business-time, SLA, settlement, and payroll logic that consumes it.
  - Fix:
    - Model holidays as intervals in local time with a zone, region, and
      purpose, supporting partial days.
    - Keep separate calendars per purpose (bank, exchange, school,
      company).
    - Use a maintained holiday data source with an update process, and
      let operators add ad hoc holidays with audit.
    - Support observed dates and swapped working days.
    - Compute sunset-based starts with an astronomy library and location
      (PA-57).
    - Compute holiday durations from the interval's instants, not from
      day counts (PA-1).
  - Not a finding:
    - Interval-based, region-scoped holiday calendars from a maintained
      source.
  - Escalate (NEEDS-HUMAN): SLA, settlement, or payroll rules that depend
    on holidays where the holiday calendar, region, and partial-day rules
    are not stated.
  - Proposed severity (for the user to decide): HIGH when settlement,
    payroll, trading, or SLA deadlines on a core path use whole-day,
    global, or stale holiday data. MEDIUM for scheduling and display.
    LOW for test-only code.
- PA-59: Saturday-Sunday weekend assumption. Code assumes the weekend is
  Saturday and Sunday everywhere and for everyone.
  - Overlap: PA-48 mentions regional weekends briefly. PA-58 covers
    swapped working days. PA-59 covers weekend definitions in full:
    regional, historical, organizational, and data-source differences.
    Merged per the class ledgers.
  - Why it is false:
    - Regional weekends differ. Node `Intl.Locale` week info (CLDR)
      reports (verified):
      - Saturday-Sunday: `en-US`, `ar-AE`.
      - Friday-Saturday: `ar-SA`, `ar-EG`, `he-IL`.
      - Friday only: `fa-IR`.
      - Sunday only: `en-IN`.
    - Locale data is not authoritative. The same build reports
      Saturday-Sunday for `bn-BD` and `dv-MV`, while government offices in
      Bangladesh and the Maldives close Friday and Saturday (verified
      output, practice to be confirmed per deployment).
    - Weekends change over time. Saudi Arabia moved from Thursday-Friday
      to Friday-Saturday in 2013. The UAE moved from Friday-Saturday to
      Saturday-Sunday in 2022, with a Friday half day for government
      workers. Some Malaysian states use Friday-Saturday and others
      Saturday-Sunday, and states have switched.
    - Weekends differ within a country by sector and organization:
      government versus private sector, retail and hospitality, healthcare
      and shift work, four-day weeks, and Friday half days.
    - Markets keep their own trading weeks (for example, the Saudi
      exchange trades Sunday to Thursday).
    - Swapped working days turn some weekend days into workdays (PA-58).
  - How it appears in code:
    - `is_weekend = weekday in (SATURDAY, SUNDAY)`.
    - Business-day arithmetic (delivery estimates, settlement T+N, SLA
      timers) that skips Saturday and Sunday only.
    - Weekend surcharges, rates, or schedules fixed to Saturday and
      Sunday.
    - Historical business-day calculations using today's weekend
      definition.
    - Locale weekend data used as the legal or business source of truth.
  - What to check:
    - Weekend logic: literal weekdays, locale defaults, or a configured
      business calendar.
    - Whether the calendar is per region and per organization, and dated.
    - Consumers: settlement, SLA, payroll, delivery, pricing.
  - Fix:
    - Define weekends in a business calendar per region and organization,
      with effective dates so historical calculations use the rule in
      force at the time.
    - Use locale data only as a default for display, never as the
      business authority.
    - Combine weekend rules with holidays and swapped workdays in one
      business-day service (PA-58).
    - Support per-employee or per-site working patterns where shifts
      differ.
  - Not a finding:
    - Single-region products with a documented Saturday-Sunday business
      calendar applied through one service.
  - Escalate (NEEDS-HUMAN): business-day rules for multi-region products
    where the weekend for each region, sector, and period is not stated.
  - Proposed severity (for the user to decide): HIGH when settlement,
    payroll, delivery, or SLA deadlines on a core path use the wrong
    weekend. MEDIUM for pricing and display. LOW for test-only code.
- PA-60: Global timestamp ordering assumption. Code assumes timestamps
  can be put into one total order that stays meaningful outside the
  system that produced them.
  - Overlap: PA-14 to PA-16 cover client-server skew. PA-30 covers ties
    and uniqueness. PA-31 covers what a timestamp records. PA-60 covers
    ordering events across systems by timestamp, and the claim that such
    an order reflects what really happened. Merged per the class ledgers.
  - Why it is false:
    - Clocks on different systems disagree (PA-11 to PA-16). Ordering
      timestamps from several sources gives an order of clock readings,
      not of events.
    - Physical timestamps cannot capture causality without bounded skew.
      Lamport's "Time, Clocks, and the Ordering of Events in a Distributed
      System" (1978) shows that only a partial order (happened-before) is
      grounded in causality. Any total order adds arbitrary tie-breaking.
    - Systems that do order by physical time need explicit uncertainty
      bounds. Google Spanner's TrueTime returns an interval, and commits
      wait out the uncertainty to keep an external order. That order
      holds only inside Spanner.
    - Ties, mixed precision, time scales, leap-second repeats, and
      smearing all break ordering across sources (PA-20, PA-29, PA-30,
      PA-46).
    - Timestamps from different systems may record different moments:
      sent, received, processed (PA-31).
    - In physics, simultaneity is relative: distant events can have no
      frame-independent order. This matters only in space and precision
      domains (PA-20).
  - How it appears in code:
    - Logs, events, or audit trails from several services merged by
      timestamp to reconstruct cause and effect.
    - Last-write-wins conflict resolution across replicas or devices
      (PA-14).
    - Distributed traces whose child spans appear to start before their
      parents.
    - Event streams exported to partners with a claimed global order
      based on timestamps.
    - Cross-shard ordering by timestamp plus ID, presented as the true
      order.
  - What to check:
    - Any merge or comparison of timestamps from different systems that
      drives a decision.
    - Ordering guarantees promised to consumers, and what backs them.
    - Conflict resolution rules.
  - Fix:
    - Get a total order inside a system from one authority: a database
      sequence, a log offset in a single partition, or a consensus log.
    - Track causality across nodes with logical, vector, or hybrid
      logical clocks (HLC, as used by CockroachDB), or carry causal
      metadata such as trace parent IDs and version vectors.
    - Treat cross-system timestamps as approximate, with a stated
      uncertainty.
    - Publish order guarantees precisely (for example, per key or per
      partition) and give consumers sequence IDs, not timestamps, as the
      ordering key.
    - Resolve conflicts with version vectors or domain rules, not wall
      clocks.
  - Not a finding:
    - Timestamp ordering used only for approximate display, with no
      decisions resting on it.
  - Escalate (NEEDS-HUMAN): audit, financial, or legal processes that
    require a provable order of events across systems, where the ordering
    mechanism and tolerance are not stated (PA-46 cites the MiFID II
    accuracy rule as an example of a stated tolerance).
  - Proposed severity (for the user to decide): HIGH when conflict
    resolution, audit trails, or financial event order on a core path
    rely on cross-system timestamps. MEDIUM for traces, logs, and
    analytics. LOW for test-only code.
- PA-61: Office-hours offset stability assumption. Code assumes UTC
  offsets never change during office hours, so business-hours logic can
  ignore transitions.
  - Overlap: PA-36 and PA-37 cover transition times and instants. PA-59
    covers regional weekends. PA-50 covers moving devices. PA-35 covers
    tz data updates. PA-61 covers the belief that transitions fall
    outside working time, and caching offsets for a working day. Merged per the class ledgers.
  - Why it is false:
    - One zone's night is another zone's working day. The US change at
      07:00 UTC on Sunday 2026-03-08 (03:00 in New York after the jump)
      happens at 09:00 in Jerusalem, 10:00 in Riyadh, 11:00 in Dubai, and
      12:30 in Kolkata (verified). Sunday is a working day in Israel and
      Saudi Arabia (PA-59).
    - The EU change at 01:00 UTC on 2026-03-29 happens at 10:00 in Tokyo
      and 12:00 in Sydney (verified).
    - Many operations run around the clock: hospitals, factories, call
      centers, logistics, shift work, and markets such as crypto
      exchanges.
    - Governments can set transitions at any hour, including during the
      day, and change them at short notice (PA-35).
    - A traveling user's device offset changes whenever it lands (PA-50).
    - A tz data update deployed during the day changes the offsets a
      system computes for affected instants from that moment (PA-35).
  - How it appears in code:
    - DST handling skipped in features that "only run in business hours".
    - The offset computed once at the start of the business day and
      reused until close.
    - Meeting schedulers or calendars that assume the offset at 09:00
      holds until 17:00 for every participant's zone.
    - Multi-region jobs scheduled "during office hours" from one region's
      perspective.
  - What to check:
    - Offsets cached per day or per session.
    - Business-hours features that bypass zone handling.
    - Which zones a feature serves, and when their transitions fall in
      each other's working hours.
  - Fix:
    - Compute the offset for each instant, every time, with the library
      (BP-1). Do not cache offsets per business day.
    - Treat every zone the feature serves, not only the operator's.
    - Assume operations can be active at any hour unless the requirement
      limits them explicitly.
    - Recompute dependent values after tz data updates (PA-35).
  - Not a finding:
    - Per-instant offset computation in business-hours features.
  - Escalate (NEEDS-HUMAN): business-hours features in multi-region
    products where the set of zones and the working calendar for each are
    not stated.
  - Proposed severity (for the user to decide): HIGH when scheduling,
    billing, or SLAs on a core path use an offset cached across a
    transition. MEDIUM for display and internal tools. LOW for test-only
    code.
- PA-62: Exact sleep assumption. Code assumes a sleep call such as
  `Thread.sleep(1000)` pauses for exactly the requested time.
  - Overlap: PA-21 and PA-22 cover throttled, paused, and overflowing
    timers. PA-24 covers coarse timer resolution. PA-54 covers drift in
    polling loops. PA-62 covers the contract of sleep calls themselves:
    early return, late return, and which clock they follow. Merged per the class ledgers.
  - Why it is false:
    - Sleeps return late. The Java documentation states that
      `Thread.sleep` is "subject to the precision and accuracy of system
      timers and schedulers". On this host `Thread.sleep(1000)` took
      1000.6 ms, and the worst of 200 `Thread.sleep(1)` calls took 1.6 ms
      (verified, host-dependent). Load, garbage collection, CPU
      throttling, and VM steal time make it worse (PA-21).
    - Windows' default timer granularity is about 15.6 ms, so very short
      sleeps last much longer than asked (PA-24).
    - Sleeps return early:
      - Java `Thread.sleep` throws `InterruptedException` when the thread
        is interrupted. A 1000 ms sleep interrupted at 200 ms returned
        after 200.6 ms (verified).
      - POSIX `sleep()` and `nanosleep()` return early when a signal
        arrives, reporting the time remaining.
      - Python retries the sleep after a signal handler returns (PEP 475,
        Python 3.5+). A 1 s sleep with a signal at 0.2 s still took 1.0 s
        (verified). The handler raising an exception ends it early.
      - `Object.wait` and condition variables can wake spuriously.
    - Sleeps follow a particular clock. Linux relative sleeps use a
      monotonic clock that does not count suspend, so a sleeping process
      wakes late in wall-clock terms after the machine resumes (PA-20,
      PA-22). Absolute sleeps on `CLOCK_REALTIME` move when the wall clock
      is changed (PA-11).
    - Browsers clamp nested `setTimeout` delays to at least 4 ms after
      several levels (HTML specification) and throttle background tabs
      (PA-21). Delays of 2^31 ms or more overflow (PA-22).
  - How it appears in code:
    - Elapsed time assumed equal to the requested sleep, with no clock
      re-read after waking.
    - `InterruptedException` caught and ignored, so the loop continues as
      if the full sleep happened. The interrupt status is also lost.
    - Sleep loops used as clocks or schedulers (PA-54).
    - Rate limiters, retries, and backoff assuming exact sleep lengths.
    - Tests using sleeps for synchronization. They are slow and flaky.
  - What to check:
    - Code after a sleep that relies on how long it lasted.
    - Interrupt and signal handling around sleeps.
    - Sleeps used for coordination instead of synchronization primitives.
  - Fix:
    - Re-read a monotonic clock after every sleep and act on the measured
      elapsed time (PA-11).
    - Sleep until a deadline in a loop: compute the remaining time from
      the clock, sleep, and repeat until the deadline passes.
    - Handle interrupts deliberately. In Java, restore the interrupt
      status (`Thread.currentThread().interrupt()`) or stop the work.
    - Use synchronization primitives, futures, or schedulers instead of
      sleeps for coordination. Use fake clocks in tests (PA-25).
  - Not a finding:
    - Sleeps used only for coarse pacing where exact length does not
      matter, with no logic depending on the duration.
  - Escalate (NEEDS-HUMAN): real-time or safety-related control loops
    whose timing tolerances are not stated.
  - Proposed severity (for the user to decide): HIGH when control loops,
    rate limits, billing, or safety timeouts on a core path assume exact
    sleeps or swallow interrupts. MEDIUM for retries and backoff. LOW for
    test-only code.
- PA-63: Minimum-sleep assumption. Code assumes a sleep of 1000 ms always
  lasts at least 1000 ms.
  - Overlap: PA-62 covers interrupts, signals, and spurious wakeups ending
    sleeps early. PA-63 adds early wakeups without any interrupt, the
    clock used to measure the sleep, and code that depends on the minimum.
    Merged per the class ledgers.
  - Why it is false:
    - Timers can fire early by the measuring clock. In Node, 3 of 200
      `setTimeout(fn, 10)` calls fired after less than 10 ms by both
      `Date.now()` and `performance.now()`, the shortest after 9.165 ms
      (verified, host-dependent).
    - Interrupts, signals, and spurious wakeups end sleeps early (PA-62).
    - The sleep's clock and the measuring clock differ. A sleep that lasts
      1000 ms on a monotonic clock can measure less on the wall clock if
      the wall clock is slewing slow or steps backward (PA-11, PA-20).
    - Monotonic clocks are frequency-adjusted too. Linux `CLOCK_MONOTONIC`
      is slewed by time sync. `CLOCK_MONOTONIC_RAW` is not. 1000 ms on one
      is not exactly 1000 SI milliseconds (PA-20).
    - Fake timers in tests (for example Jest or Sinon) complete sleeps
      instantly unless the test advances time (PA-25).
    - Language guarantees differ. Go documents that `time.Sleep` pauses
      for at least the duration. Python documents at least the given time
      since 3.5, unless a signal handler raises. Java documents only that
      `Thread.sleep` is subject to timer and scheduler precision. JS
      `setTimeout` has no strict minimum guarantee.
  - How it appears in code:
    - Rate limiters or protocol timings that send the next request right
      after a sleep, assuming the minimum gap has passed.
    - Lock leases, debounce windows, or cooldowns enforced only by a
      sleep.
    - Tests asserting `elapsed >= requested` after a sleep. They fail
      intermittently.
    - Safety interlocks (wait at least N ms before re-energizing) relying
      on a sleep alone.
  - What to check:
    - Logic whose correctness depends on a minimum time having passed.
    - The clock used to measure sleeps.
  - Fix:
    - Enforce minimum gaps by checking a monotonic clock: loop until
      `now - start >= required`, sleeping for the remainder each time.
    - Measure with the same clock the requirement is stated in.
    - For safety-critical minimum delays, use hardware timers or a
      real-time facility with documented guarantees.
    - Allow a tolerance in timing tests, or use fake clocks (PA-25).
  - Not a finding:
    - Sleeps used for coarse pacing with no correctness depending on the
      minimum.
  - Escalate (NEEDS-HUMAN): safety or protocol timing requirements whose
    minimum-delay guarantees are not stated.
  - Proposed severity (for the user to decide): HIGH when safety
    interlocks, protocol timing, or rate limits on a core path depend on
    a sleep's minimum duration. MEDIUM for debounce and cooldowns. LOW for
    test-only code.
- PA-64: Sixty-second minute assumption. Code assumes every minute has
  exactly 60 seconds.
  - Overlap: PA-20 and PA-46 cover leap seconds, smearing, and Unix
    time. PA-64 covers minute length as such, the types and validators
    that encode 0 to 59, and the related decimal-minute confusion. Merged per the class ledgers.
  - Why it is false:
    - A UTC minute containing a positive leap second has 61 seconds
      (23:59:60). 27 have been inserted since 1972 (PA-46).
    - A negative leap second would give a 59-second minute. None has
      happened yet, but one has been discussed because Earth's rotation
      has sped up. Leap seconds are scheduled to be discontinued by 2035
      (PA-1).
    - Smeared minutes contain 60 slightly longer seconds (PA-20).
    - Before 1972, UTC used fractional steps and rate offsets, so minutes
      were not uniform (PA-46).
    - Standards encode the range differently. C89 allowed `tm_sec` from 0
      to 61 for a "double leap second" that never exists. C99 narrowed it
      to 0 to 60.
    - Libraries differ (verified):
      - Java `DateTimeFormatter.ISO_INSTANT` accepts `23:59:60Z`, maps it
        to `23:59:59Z`, and reports it through `parsedLeapSecond()`.
      - Java `LocalTime.of(23, 59, 60)` throws.
      - Python `datetime` rejects second 60, and JS `Date.parse` returns
        `NaN` (PA-46).
    - Decimal time is not minutes and seconds. Timesheets and payroll
      often record decimal hours: 1.30 hours is 1 hour 18 minutes, not 1
      hour 30 minutes.
  - How it appears in code:
    - Validators, regexes, or types limiting seconds to 0 to 59.
    - Per-second arrays or buckets with exactly 60 slots per minute.
    - Duration parsers for `mm:ss` that reject or mishandle `:60`.
    - Decimal hours and `h:mm` values mixed in calculations or displays.
  - What to check:
    - Range checks on the seconds field at input boundaries.
    - Fixed-size per-second structures.
    - Units of duration fields in timesheets, billing, and payroll.
  - Fix:
    - Accept second 60 where UTC input can contain leap seconds, and
      normalize it by a documented rule (PA-46).
    - Size per-second structures from the actual interval, or tolerate
      61 entries.
    - Store durations in one unit (seconds or minutes) and convert decimal
      hours explicitly at the edges, with labels.
  - Not a finding:
    - Systems that receive only smeared or POSIX time and never see second
      60, documented as such.
  - Escalate (NEEDS-HUMAN): payroll or billing inputs whose duration
    format (decimal hours or `h:mm`) is not stated.
  - Proposed severity (for the user to decide): HIGH when leap-second
    input crashes or corrupts a core path, or decimal-hour confusion
    changes pay or charges. MEDIUM for per-second metrics. LOW for
    test-only code.
- PA-65: Monotonic timestamp assumption. Code assumes timestamps always
  increase in the order records are written or events arrive.
  - Overlap: PA-11 and PA-12 cover clocks jumping backward. PA-30, PA-53,
    and PA-60 cover ties, consecutive reads, and cross-system order.
    PA-65 covers sequences of stored timestamps that go backward, and
    "monotonic" clocks that are only monotonic in a narrow scope. Merged per the class ledgers.
  - Why it is false:
    - Clocks step backward, VMs restore, and leap seconds repeat
      (PA-11, PA-12, PA-46).
    - Local wall-clock timestamps repeat an hour at every DST fall-back
      (PA-1).
    - Transactions commit out of timestamp order. Postgres `now()` is the
      transaction start time (PA-30), so a long transaction that started
      earlier commits later with an earlier `created_at` or `updated_at`
      than rows already visible.
    - Multiple writers, hosts, clients, and replicas each stamp with their
      own clock, and replication lag reorders arrival (PA-14, PA-60).
    - Offline devices and queues deliver old events late (PA-31).
    - Monotonic clocks are monotonic only within one process or one boot.
      Linux `CLOCK_MONOTONIC` restarts at boot. Java `System.nanoTime()`
      has an arbitrary origin per JVM. Python `time.monotonic()` has an
      undefined reference point. Browser `performance.now()` counts from
      each page's `timeOrigin`. Only differences within one scope mean
      anything.
  - How it appears in code:
    - `ORDER BY created_at` treated as insertion order.
    - Incremental sync or ETL with `WHERE updated_at > :watermark`. Rows
      from transactions that commit late, with earlier timestamps, are
      skipped forever.
    - Assertions or validations requiring each new timestamp to exceed the
      last.
    - Monotonic clock readings stored in databases, sent between hosts, or
      compared across restarts.
    - Time-series stores rejecting out-of-order samples. Prometheus
      rejects out-of-order samples within a series by default. An
      out-of-order window was added in version 2.39.
    - Local naive timestamps in logs, which go backward each autumn.
  - What to check:
    - Watermark and cursor logic on timestamps.
    - Ordering assumptions on timestamp columns.
    - Persistence or comparison of monotonic clock values.
    - Handling of late and out-of-order events in pipelines.
  - Fix:
    - Use sequences, log offsets, or commit-order positions (logical
      replication LSN, change data capture) for order and cursors
      (PA-60).
    - If timestamp watermarks remain, re-read with an overlap window
      (`>= watermark - margin`) and deduplicate, with the margin longer
      than the longest transaction.
    - Use monotonic clocks only for in-process durations. Never store or
      compare them across processes, hosts, or boots (PA-11).
    - Store UTC instants, not local wall-clock times (PA-10).
    - Design pipelines for late data: buffering, event-time windows with
      allowed lateness, or out-of-order ingestion settings.
  - Not a finding:
    - Ordering by timestamp for display only, with sequence-based cursors
      behind it.
  - Escalate (NEEDS-HUMAN): incremental sync or audit processes whose
    completeness depends on timestamp ordering, where the maximum
    transaction length or lateness is not stated.
  - Proposed severity (for the user to decide): HIGH when timestamp
    watermarks or monotonicity checks skip, drop, or reject records on a
    core path. MEDIUM for log ordering and metrics. LOW for test-only
    code.
- PA-66: GMT-equals-UTC assumption. Code assumes `GMT` and `UTC` are the
  same time zone.
  - Overlap: PA-8 notes that "GMT" in common use means London time.
    PA-66 covers the distinction in full: time standards, zone names,
    sign conventions, protocol literals, and silent fallbacks. Merged per the class ledgers.
  - Why it is false:
    - Different standards: UTC is an atomic time scale kept within 0.9 s
      of Earth-rotation time by leap seconds. GMT historically meant mean
      solar time at Greenwich (close to UT1). Today "GMT" is used loosely
      for UTC+00:00, but the two are not defined the same way (PA-46).
    - People use "GMT" for UK civil time. `Europe/London` is GMT
      (+00:00) in winter and BST (+01:00) in summer (verified). "15:00
      GMT" in July is ambiguous between UTC 15:00 and London 15:00.
    - Inverted signs in zone names: `Etc/GMT+5` means UTC-05:00
      (verified), following POSIX `TZ` sign rules. `TZ=UTC+3` and
      `TZ=Etc/GMT+3` both give UTC-03:00 (verified with `date`).
    - Platforms disagree on the same label. Java's legacy
      `TimeZone.getTimeZone("GMT+5")` gives UTC+05:00, while
      `ZoneId.of("Etc/GMT+5")` gives -05:00 (verified).
    - Silent fallback: Java's legacy `TimeZone.getTimeZone` returns GMT
      for an unknown or misspelled ID such as `Europe/Lodnon`, while
      `ZoneId.of` throws `ZoneRulesException` (verified).
    - Protocols require the literal "GMT". HTTP dates (RFC 9110) and
      cookie `Expires` values must use `GMT` to mean UTC. Python
      `formatdate(usegmt=True)` produces `... 00:00:00 GMT` (verified).
      Writing `UTC` there breaks strict parsers.
    - JS `Date.toString()` labels offsets as `GMT-0400`, which means
      UTC-04:00.
  - How it appears in code:
    - UK users assigned a fixed `GMT` zone, wrong by an hour all summer.
    - UI labels like "GMT+3" mapped to `Etc/GMT+3`, giving UTC-03:00.
    - POSIX `TZ` strings written with the intuitive sign.
    - Legacy Java `TimeZone.getTimeZone` with user or config input,
      silently falling back to GMT on typos.
    - HTTP date headers or cookies written with `UTC` or numeric offsets.
    - Requirements or UI text using "GMT" without saying whether UTC or
      London time is meant.
  - What to check:
    - Zone assignments named `GMT`, `Etc/GMT+/-N`, or POSIX `TZ` strings.
    - Zone ID validation and fallback behavior.
    - HTTP and email date generation.
    - Labels and documentation using "GMT".
  - Fix:
    - Use `UTC` (or `Etc/UTC`) for UTC, and `Europe/London` for UK time
      (BP-1).
    - Avoid `Etc/GMT+/-N` and POSIX offset strings. Where unavoidable,
      document the inverted sign beside them.
    - Validate zone IDs with APIs that reject unknown IDs (Java `ZoneId.of`),
      never with silent-fallback APIs.
    - Generate HTTP and email dates with library formatters that emit the
      required `GMT` literal.
    - Label user-facing times as "UTC" or with the named zone, never bare
      "GMT".
  - Not a finding:
    - The literal `GMT` in HTTP or email date formats, where the
      protocol requires it.
  - Escalate (NEEDS-HUMAN): requirements, contracts, or schedules stated
    in "GMT" where UTC versus UK civil time cannot be established.
  - Proposed severity (for the user to decide): HIGH when UK users or
    deadlines on a core path are an hour off in summer, or typos silently
    fall back to GMT. MEDIUM for labels and HTTP header formatting. LOW
    for test-only code.
- PA-67: Britain-on-GMT assumption. Code assumes Britain, or the UK, is
  always on GMT.
  - Overlap: PA-66 covers GMT versus UTC and London's summer time. PA-38
    and PA-47 cover wartime double summer time and the 1968 to 1971
    experiment. PA-67 adds how much of the year the UK is not on GMT,
    British places in other zones, and abbreviation collisions. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b and Java):
    - The UK is on BST (+01:00) for most of the year: 210 days in 2026.
    - History: +01:00 all year from 1968 to 1971 (PA-47), and +01:00 in
      winter with +02:00 in summer during the Second World War (PA-38).
    - British jurisdictions span many zones. In July 2026: Jersey
      (`Europe/Jersey`) +01:00 BST, Gibraltar (`Europe/Gibraltar`)
      +02:00 CEST, the Falklands (`Atlantic/Stanley`) -03:00, Bermuda
      (`Atlantic/Bermuda`) -03:00 ADT, and the Chagos Archipelago
      (`Indian/Chagos`) +06:00.
    - Ireland, often lumped with Britain, uses `Europe/Dublin`: IST
      (+01:00) in summer and GMT in winter, modeled as negative DST in
      tzdata's main format (PA-36).
    - Abbreviations collide. "BST" means British Summer Time, and also
      Bangladesh Standard Time. Java's `ZoneId.SHORT_IDS` maps `BST` to
      `Asia/Dhaka`, and legacy `TimeZone.getTimeZone("BST")` gives
      +06:00 (verified). "IST" means Irish, Israel, or India Standard
      Time. `SHORT_IDS` maps `IST` to `Asia/Kolkata` (verified). tzdata
      itself now labels Dhaka as `+06`, not "BST" (verified).
    - The UK has debated permanent summer time and other changes, so
      rules may change (PA-9).
  - How it appears in code:
    - UK users or offices assigned `GMT`, UTC, or a fixed +00:00 offset.
    - Country code `GB` mapped to one zone, missing territories and
      Crown dependencies.
    - Parsing zone abbreviations ("BST", "IST") from input or logs into
      offsets.
    - Java legacy short IDs used for zone lookup.
  - What to check:
    - Zone assignment for UK and related locations.
    - Any parsing or mapping of zone abbreviations.
    - Country-to-zone mappings.
  - Fix:
    - Use `Europe/London` for Great Britain and Northern Ireland, and the
      specific IANA ID for each territory or dependency (BP-1).
    - Never parse zone abbreviations as identifiers. Require IANA IDs or
      numeric offsets at input (PA-27).
    - Do not use Java `SHORT_IDS` or legacy three-letter IDs.
    - Map countries to zones with the tzdata `zone1970.tab` /
      `zone.tab` data or a library, and expect several zones per country.
  - Not a finding:
    - Abbreviations used only for display, generated from the zone data.
  - Escalate (NEEDS-HUMAN): inputs or partner feeds that supply only zone
    abbreviations.
  - Proposed severity (for the user to decide): HIGH when UK or
    abbreviation-parsed times on a core path are off by an hour or more.
    MEDIUM for display and territory coverage. LOW for test-only code.
- PA-68: Forward-only time assumption. Code assumes the time it observes
  only ever moves forward.
  - Overlap: PA-11, PA-12, PA-46, PA-50, and PA-65 cover the individual
    causes of backward time. PA-68 collects the code-level consequences:
    negative elapsed values, counter wraparound, and stale reads that look
    like time going backward. Merged per the class ledgers.
  - Why it is false:
    - Wall clocks step back (PA-11), VMs restore (PA-12), and leap seconds
      repeat (PA-46).
    - Local wall time goes back an hour at every DST fall-back (PA-1),
      and a day when crossing the date line eastward (PA-50).
    - Operators, tests, and replays set "now" to the past on purpose
      (PA-25, PA-26).
    - Fixed-width tick counters wrap: a 32-bit millisecond counter wraps
      after 49.7 days (PA-22), and a naive comparison then sees time go
      backward.
    - Reads from lagging replicas or caches show older state after newer
      state, so to a user the data moves back in time.
  - How the language runtimes react to a negative duration (verified):
    - Python `time.sleep(-1)` raises `ValueError`.
    - Java `Thread.sleep(-1)` throws `IllegalArgumentException`.
    - JS `setTimeout(fn, -1000)` fires almost immediately.
    - Go `time.Sleep(-time.Second)` returns immediately.
    - Unsigned subtraction wraps: in Go, `uint32(5) - uint32(10)` is
      4294967291 (verified).
  - How it appears in code:
    - Elapsed time computed as `now - last` with no handling for negative
      results: crashes, immediate firing, or huge unsigned values.
    - Token-bucket rate limiters that refill by a negative amount, or by a
      huge amount after unsigned underflow.
    - Session and cache expiry extended when the clock moves back.
    - Tick-counter comparisons such as `now > deadline` that fail after a
      wrap. With signed 32-bit values just past a wrap, the naive
      comparison is false while the wrap-safe `(now - deadline) > 0` is
      true (verified in Java).
    - Guards that throw or drop data when `now < last_seen`.
    - Moving averages and physics steps using a negative `dt`.
    - Reads routed to replicas right after a write, showing the user an
      older state.
  - What to check:
    - Every subtraction of two time readings, and what happens when the
      result is negative.
    - Unsigned or fixed-width time arithmetic.
    - Behavior when "now" is earlier than a stored value.
    - Read-after-write paths and their consistency guarantees.
  - Fix:
    - Measure durations with a monotonic clock (PA-11).
    - Clamp negative elapsed values to zero and log them as clock events.
    - Compare wrapping counters with wrap-safe arithmetic (subtract, then
      test the signed result, as the Linux kernel's `time_after` macros
      do).
    - Define a policy for `now < last_seen`: accept and log, hold, or
      reject, never crash silently.
    - Provide read-your-writes consistency where users expect it (read
      from the primary, or use session tokens or versions).
  - Not a finding:
    - Code that measures durations only with monotonic clocks and handles
      negative results explicitly.
  - Escalate (NEEDS-HUMAN): user-facing flows where stale replica reads
    after a write are possible and the required consistency is not stated.
  - Proposed severity (for the user to decide): HIGH when backward time
    crashes, disables rate limits, or extends expiry on a core path.
    MEDIUM for metrics, display, and stale reads. LOW for test-only
    code.
- PA-69: Fixed week length assumption. Code assumes one week from now is
  always exactly `7 * 86400` (604,800) seconds away.
  - Overlap: PA-1 covers day length and the elapsed-versus-calendar
    distinction. PA-44 covers adding hours. PA-69 covers week arithmetic
    and weekly recurrence. Merged per the class ledgers.
  - Why it is false (elapsed seconds from noon to noon one local calendar
    week later, verified with tzdata 2026b):
    - New York, week containing spring-forward (2026-03-05 to 03-12):
      601,200 seconds.
    - New York, week containing fall-back (2026-10-29 to 11-05): 608,400
      seconds.
    - Lord Howe Island, week containing its 30-minute change (2026-04-01
      to 04-08): 606,600 seconds.
    - Samoa, week containing the skipped 2011-12-30 (2011-12-26 to
      2012-01-02): 518,400 seconds, six days.
    - A week containing a leap second has 604,801 SI seconds (PA-46).
  - How it appears in code:
    - "Next week" or weekly expiry computed as `now + 604800` (or
      `604800000` ms) and then shown or used in local time. It lands an
      hour off after a DST change.
    - Weekly recurring events (every Monday 09:00) stored as a series of
      instants 604,800 seconds apart. They drift by an hour after a
      transition (PA-36).
    - Week counts computed as `(b - a) / 604800` with truncation.
    - Mixed library semantics: Luxon `plus({ weeks: 1 })` and Java
      `ZonedDateTime.plusWeeks(1)` keep local wall time. Python
      `aware + timedelta(weeks=1)` also keeps wall time (PA-1). JS
      `t + 7 * 86400000` is elapsed time.
  - What to check:
    - Literals 604800, 604800000, 10080 (minutes), or 168 (hours) near
      date code.
    - Weekly recurrence storage and generation.
    - Week-count calculations.
  - Fix:
    - Decide the meaning first: 168 elapsed hours, or the same local time
      on the same weekday next week (PA-1).
    - For calendar weeks, use the library's week addition in the relevant
      zone (BP-1). For elapsed weeks, add to UTC instants.
    - Generate weekly occurrences from the anchor in local time plus zone,
      each computed separately (PA-2, PA-9).
    - Count weeks on local dates, not on timestamp differences.
  - Not a finding:
    - A 604,800-second TTL where the requirement is 168 elapsed hours.
  - Escalate (NEEDS-HUMAN): "weekly" billing, access, or retention rules
    whose spec does not say elapsed hours or calendar weeks.
  - Proposed severity (for the user to decide): HIGH when weekly billing,
    recurring meetings, or deadlines on a core path drift or misfire.
    MEDIUM for reports and display. LOW for test-only code.
- PA-70: Timestamp-difference accuracy assumption. Code assumes
  subtracting two timestamps gives the time that actually elapsed between
  them.
  - Overlap: many items cover individual causes (PA-11, PA-14, PA-20,
    PA-22, PA-29, PA-31, PA-46, PA-55). PA-70 states the conditions under
    which a difference is valid, and adds subtraction semantics that
    ignore DST.
  - A difference measures elapsed time only when all of these hold:
    - Both readings come from the same clock, with no step, slew, or
      smear between them (PA-11, PA-13, PA-20).
    - Both are in the same time scale, and the interval has no leap
      seconds, or they are accounted for (PA-46).
    - Both are instants (UTC or with offsets), not local wall-clock values
      (PA-1).
    - Both have adequate precision (PA-23, PA-29).
    - Both record the events in question, not ingestion or processing
      times (PA-31).
    - The clock kept running through any suspension that should count
      (PA-20, PA-22).
  - Subtraction that ignores DST (verified):
    - Python: subtracting two aware datetimes with the same `tzinfo`
      ignores the offsets. New York 2026-03-07 12:00 to 2026-03-08 12:00
      gives `1 day, 0:00:00`, though only 23 hours elapsed. Converting to
      UTC first, or using different `tzinfo` objects, gives `23:00:00`.
    - Java: `Duration.between` on two `LocalDateTime` values gives
      `PT24H`. On `ZonedDateTime` values it gives `PT23H`.
    - SQL: subtracting Postgres `timestamp without time zone` values, or
      MySQL `TIMESTAMPDIFF` on `DATETIME` values, works on wall-clock
      values and ignores DST. Postgres `timestamptz` subtraction uses
      instants.
    - JS `Date` subtraction uses epoch milliseconds, so it measures
      instants.
  - How it appears in code:
    - Durations from local or same-zone aware values in Python, local
      types in Java, or zone-less SQL columns.
    - Durations across machines, across time scales, or across a clock
      step.
    - Durations reported with no uncertainty where the inputs carry
      uncertainty (PA-13).
  - What to check:
    - The types being subtracted and the language's subtraction rules.
    - Where each timestamp came from.
    - Whether the result feeds billing, SLAs, payroll, or safety.
  - Fix:
    - Subtract instants: convert to UTC first, or use instant types
      (`Instant`, `timestamptz`, epoch values from one clock) (BP-1).
    - Measure in-process durations with a monotonic clock (PA-11).
    - For cross-system durations, state the uncertainty, or measure on a
      single authoritative clock (PA-14, PA-60).
    - Record what each timestamp means before subtracting (PA-31).
  - Not a finding:
    - Differences of UTC instants from one clock, used where small errors
      do not matter.
  - Escalate (NEEDS-HUMAN): billing, payroll, SLA, or regulatory
    durations computed from timestamps whose source and type are not
    established.
  - Proposed severity (for the user to decide): HIGH when billed,
    paid, or SLA durations on a core path come from local-time
    subtraction or mixed sources. MEDIUM for reports and metrics. LOW
    for test-only code.
- PA-71: Hour-range assumption. Code assumes any time with an hour of 24
  or more, such as `24:12:34`, is invalid.
  - Overlap: PA-57 covers GTFS service days and Japanese late-night
    listings as day-boundary issues. PA-64 covers second 60. PA-71
    covers values with hour 24 or more at input: where they are valid,
    and how parsers disagree. Merged per the class ledgers.
  - Why it is false:
    - Transit schedules: GTFS `stop_times` allow `24:12:34` and later for
      trips after midnight on the same service day (PA-57).
    - Extended-hour notation: Japanese and other East Asian business
      hours and TV listings use times such as `25:30` or `26:00` (a
      30-hour clock) for late night.
    - End of day: ISO 8601 editions have differed on `24:00` as the end
      of a day (allowed in the 2004 edition, dropped in 2019, and
      revisited since). RFC 3339 allows hours 00 to 23 only.
    - Durations are not times of day: elapsed values such as `24:12:34`,
      `100:00:00`, race times, video lengths, and timesheet totals are
      valid. Spreadsheets show them with `[h]:mm:ss` formats. MySQL's
      `TIME` type holds -838:59:59 to 838:59:59 because it doubles as a
      duration. Postgres `time` accepts `24:00:00`.
    - Parsers disagree (verified):
      - JS `Date` accepts `2026-07-01T24:00:00Z` as the next midnight
        (`2026-07-02T00:00:00.000Z`) but rejects `T24:12:34Z`.
      - Python `strptime` with `%H` rejects both `24:00:00` and
        `24:12:34`.
      - Java `LocalDateTime.parse` rejects both `T24:00` and
        `T24:12:34`.
  - How it appears in code:
    - Validators and regexes limiting hours to 00 to 23 on fields that
      carry service-day times or durations.
    - GTFS or schedule imports that reject or wrap `24:xx` times onto
      the same date.
    - Durations stored in time-of-day types, losing anything over 24 hours
      or wrapping it.
    - `24:00` accepted by one layer (JS, Postgres) and rejected by another
      (Python, Java), so data passes one tier and fails the next.
  - What to check:
    - Whether each field is a time of day, a service-day time, or a
      duration.
    - Validation rules for the hour field.
    - Type choice for duration columns.
    - Handling of `24:00` across every layer that parses it.
  - Fix:
    - Model durations as duration types (ISO 8601 durations such as
      `PT24H12M34S`, Java `Duration`, integer seconds), never as times of
      day.
    - Parse domain formats by their specs: GTFS from noon minus 12 hours
      on the service date (PA-57), extended-hour listings by their
      cutoff.
    - Decide whether `24:00` is accepted, normalize it at the boundary to
      `00:00` on the next day, and apply the same rule in every layer.
  - Not a finding:
    - Strict 00 to 23 validation on fields that are documented times of
      day in RFC 3339 form.
  - Escalate (NEEDS-HUMAN): imported time fields whose meaning (time of
    day, service-day time, or duration) is not documented.
  - Proposed severity (for the user to decide): HIGH when valid
    schedule, transit, or timesheet data is rejected or shifted on a core
    path. MEDIUM for display and cross-layer inconsistency. LOW for
    test-only code.
- PA-72: Any-integer-year assumption. Code assumes every integer is a
  possible year.
  - Overlap: PA-18 lists type ranges for instants. PA-19 covers year 0
    and BC numbering. PA-72 covers which year numbers are valid in which
    scheme, calendar, type, and format, and where each layer stops.
    Merged per the class ledgers.
  - Why it is false:
    - Year 0 does not exist in historical AD/BC numbering. It exists in
      astronomical numbering as 1 BC (PA-19). Python `date(0, 1, 1)`
      raises "year 0 is out of range" (verified).
    - Era calendars start at year 1 and have bounds. Japanese era years
      restart with each era (PA-41). Java `JapaneseDate` rejects dates
      before Meiji 6 (1873), and `HijrahChronology` (Umm al-Qura data)
      supports only years 1300 to 1600 AH (both verified).
    - The Gregorian calendar began in 1582. Earlier Gregorian years are
      a proleptic extension (PA-19).
    - Types bound years:
      - Python `date`: 1 to 9999. .NET `DateTime`: 1 to 9999.
      - MySQL `DATE` and `DATETIME`: 1000 to 9999. SQL Server `date`:
        0001 to 9999, `datetime`: 1753 to 9999.
      - Postgres: 4713 BC to 294276 AD (`timestamp`).
      - JS `Date`: about -271821 to 275760.
      - Java `Year`: -999,999,999 to 999,999,999 (verified).
    - Formats bound years. RFC 3339 allows 0000 to 9999. ISO 8601
      allows years outside that only as "expanded" representations by
      mutual agreement (`+12026`, `-0044`). Java `LocalDate.parse`
      accepts `-0044-03-15` and `+12026-01-01`. Python `fromisoformat`
      rejects `+12026-01-01` (both verified).
    - Two-digit years are not years until a pivot rule expands them
      (PA-27).
  - How it appears in code:
    - Year fields typed as unconstrained integers, then passed to a type
      or calendar that rejects them deep in the stack.
    - Year values accepted by one layer (Java, Postgres, JS) and rejected
      by another (Python, MySQL, .NET).
    - Expanded or negative ISO years emitted by one service and rejected
      by its consumers.
    - Era or Hijri conversions crashing for dates outside library ranges.
    - Year 0 stored from astronomical data and read as historical
      numbering, or the reverse.
  - What to check:
    - Validation of year fields at input against every downstream type
      and format.
    - Calendar conversions and their supported ranges.
    - Year numbering scheme for BC and year 0.
  - Fix:
    - Define the valid year range per field from the domain and the
      narrowest layer it passes through, and validate at input.
    - State the year numbering scheme and convert explicitly (PA-19).
    - Check calendar-library ranges before converting, and handle out-of-
      range values deliberately.
    - Agree on expanded-year formats with every consumer, or avoid them.
  - Not a finding:
    - Modern-date fields validated to a documented range that every layer
      supports.
  - Escalate (NEEDS-HUMAN): historical, astronomical, or long-horizon data
    whose year range and numbering scheme are not stated.
  - Proposed severity (for the user to decide): HIGH when out-of-range or
    misnumbered years crash or corrupt data on a core path. MEDIUM for
    display and historical conversions. LOW for test-only code.
- PA-73: Display fidelity assumption. Code assumes a displayed datetime
  shows the same seconds as the stored value, so the display can stand in
  for the value.
  - Overlap: PA-23, PA-24, and PA-29 cover precision loss in storage and
    transport. PA-51 covers offsets with seconds. PA-64 covers second 60.
    PA-73 covers what display formatting changes, and code that treats
    displayed text as data. Merged per the class ledgers.
  - Why it is false:
    - Formatters drop fractions. Python `strftime('%H:%M:%S')` and
      `isoformat(timespec='seconds')` show 09:00:59.6 as `09:00:59`
      (verified). Formatters that round instead show `09:01:00`, changing
      the minute too.
    - Storage may already have rounded the value: MySQL rounds fractional
      seconds by default (PA-23).
    - Offset labels drop seconds. In New York in 1880 (LMT -04:56:02),
      UTC 12:00:00 displays as `07:03:58 GMT-0456` in JS. Parsing that
      displayed string back gives `11:59:58Z`, two seconds off (both
      verified). Python parsing `07:03:58-04:56` gives the same 11:59:58.
    - Leap seconds display as 23:59:59 or 00:00:00 depending on the
      library (PA-64).
    - Other time scales: devices showing GPS time differ from UTC by 18
      seconds (PA-13).
    - Client-side offset correction or smearing shifts displayed seconds
      (PA-13, PA-20).
    - Many displays omit seconds entirely, or show relative times ("about
      a minute ago").
  - How it appears in code:
    - Edit forms that display a timestamp without seconds or fractions
      and save the displayed value back. A save with no user changes
      rewrites the stored timestamp, and optimistic-concurrency checks on
      the timestamp fail (PA-24).
    - Tests, reconciliations, or exports comparing displayed strings with
      stored values.
    - Displayed strings parsed back into instants (screen scraping,
      copy-paste, CSV round trips).
    - Users acting on a displayed time that differs from the enforced one,
      for example a deadline shown as 17:00 but enforced at 16:59:59.5.
  - What to check:
    - Round trips through display formats: forms, exports, imports.
    - Comparisons of formatted strings with stored values.
    - Rounding versus truncation in every formatter used.
  - Fix:
    - Keep the stored value separate from its display. Submit unchanged
      fields with their original values or omit them, never the formatted
      text.
    - Compare typed values, never display strings.
    - Use machine formats with full precision and offsets (RFC 3339 with
      fractions, or epoch values with units) for exports meant to be
      re-imported (PA-27, PA-32).
    - Choose truncation or rounding deliberately and consistently, and
      enforce deadlines at the displayed boundary or display the enforced
      one.
  - Not a finding:
    - Display-only formatting that never flows back into data.
  - Escalate (NEEDS-HUMAN): deadline displays whose precision differs from
    the enforced deadline where the intended boundary is not stated.
  - Proposed severity (for the user to decide): HIGH when display round
    trips rewrite stored timestamps or break concurrency checks on a core
    path. MEDIUM for reconciliation and exports. LOW for test-only code.
- PA-74: Displayed-year fidelity assumption. Code assumes a displayed
  datetime shows the same year as the stored value.
  - Overlap: PA-3 covers Java `YYYY`. PA-7 covers year boundaries in
    UTC versus local time. PA-19 covers BC numbering. PA-32 and PA-41
    cover locale calendars. PA-73 covers display round trips. PA-74
    collects the ways a displayed year differs from the stored one, and
    adds legacy year APIs and spreadsheet epochs. Merged per the class ledgers.
  - Why it is false:
    - Zone conversion near New Year. `2026-12-31T22:00Z` displays as
      `01/01/2027, 01:00:00` in Moscow (verified) (PA-7).
    - Week-based year patterns. Java `YYYY` shows 2026-12-31 as 2027 in
      a US locale (PA-3, verified).
    - Locale calendars. `th-TH` shows 2568, `fa-IR` shows 1404, and the
      Japanese calendar shows `R7` for 2025 (PA-32, verified).
    - Legacy year APIs: JS `getYear()` returns the year minus 1900, so
      2026 displays as `126` (verified). Java `java.util.Date.getYear()`
      behaves the same. Code that prefixes "19" shows `19126`.
    - Two-digit years (`yy`, `%y`) show `26`, ambiguous by century
      (PA-27).
    - Date-only values sent as instants shift across January 1 in
      negative or positive offsets (PA-17).
    - BC years: `uuuu` and `yyyy G` print different numbers (PA-19).
    - Spreadsheet epochs. Opening a workbook built on Excel's 1904 date
      system as the 1900 system shifts every date by 1,462 days, about
      four years (verified as the day count between the epochs).
    - Labels: fiscal years ("FY2027" for October 2026 in the US federal
      calendar), academic years ("2026/27"), and tax years are not the
      calendar year (PA-7).
  - How it appears in code:
    - Year shown from a UTC value for a local event, or the reverse.
    - `YYYY`, `getYear()`, or `yy` in format strings and display code.
    - Locale formatters without a pinned calendar in machine-facing or
      cross-locale output.
    - Reports grouped by displayed year that disagree with stored-year
      queries.
    - Spreadsheet imports and exports without a declared date system.
  - What to check:
    - Format patterns and year accessors.
    - The zone and calendar used for each displayed year.
    - Spreadsheet date-system settings.
  - Fix:
    - Display the year from the local date in the defining zone (PA-7).
    - Use `yyyy` or `uuuu` (Java), `getFullYear()` (JS), and four-digit
      years.
    - Pin the calendar and numbering system where Gregorian years are
      required (PA-32, PA-41).
    - Read the workbook's date system and convert with the spreadsheet
      library (PA-4).
    - Label fiscal, academic, and tax years explicitly.
  - Not a finding:
    - Deliberate non-Gregorian or fiscal displays that are labeled and
      never parsed back.
  - Escalate (NEEDS-HUMAN): reports or documents where the year shown has
    legal or financial meaning and the defining zone or calendar is not
    stated.
  - Proposed severity (for the user to decide): HIGH when displayed years
    feed legal documents, invoices, or data entry on a core path. MEDIUM
    for reports and labels. LOW for test-only code.
- PA-75: Bounded displayed-year difference assumption. Code assumes a
  displayed year differs from the stored year by less than 2.
  - Overlap: PA-74 lists causes of a displayed year differing at all.
    PA-75 covers the size of the difference, and checks or tests that
    tolerate only off-by-one. Merged per the class ledgers.
  - Why it is false. For 2025-10-03, `Intl.DateTimeFormat` shows these
    years (verified with Node):
    - Buddhist: 2568 BE (+543).
    - Persian (Solar Hijri): 1404 AP (-621).
    - Islamic (Umm al-Qura): 1447 AH (-578).
    - Hebrew: 5786 AM (+3761).
    - Japanese: Reiwa 7 (-2018).
    - Republic of China (Minguo): 114 (-1911).
    - Ethiopic: 2018 (-7).
    - Coptic: 1742 (-283).
    - Indian national (Saka): 1947 (-78).
  - Other large differences:
    - Legacy year APIs: JS `getYear()` gives 126 for 2026 (-1900), and
      "19" + `getYear()` gives 19126 (PA-74).
    - Two-digit years and wrong century pivots: off by 100 or 2000
      (PA-27).
    - Spreadsheet date systems: about 4 years (PA-74).
    - Wrong epoch: Apple reference dates read as Unix time are 31 years
      early (PA-19). Windows FILETIME misread as Unix is off by
      centuries.
    - Wrong unit: milliseconds read as seconds give year 58467 (PA-23).
    - Overflow: 32-bit time wraps from 2038 to 1901 (PA-18).
    - Sentinels shown as dates: 0001-01-01, 1970-01-01, 9999-12-31
      (PA-18).
  - How it appears in code:
    - Validation or reconciliation that accepts a displayed or converted
      year within plus or minus 1 of the expected year as "close enough".
    - Tests that check only the boundaries near New Year and miss
      calendar, epoch, and unit errors.
    - No plausibility bounds on stored or displayed years.
  - What to check:
    - Year comparisons with tolerances.
    - Tests covering each supported calendar, epoch, and unit.
    - Plausibility bounds on year values at input and output.
  - Fix:
    - Assert exact expected years per calendar and conversion in tests.
    - Apply plausibility bounds on years at input, storage, and display,
      and flag violations (PA-12, PA-18).
    - Pin calendar, epoch, and unit explicitly at every boundary (PA-19,
      PA-23, PA-41).
  - Not a finding:
    - Labeled non-Gregorian displays computed by a calendar library.
  - Escalate (NEEDS-HUMAN): none specific beyond PA-74.
  - Proposed severity (for the user to decide): HIGH when unchecked year
    errors reach stored data, legal documents, or invoices on a core path.
    MEDIUM for display. LOW for test-only code.
- PA-76: Four-character year assumption. Code assumes the year in a valid
  `YYYY-MM-DD` date is always exactly four characters.
  - Overlap: PA-72 covers valid year ranges and expanded ISO years at
    parse time. PA-28 covers text sorting. PA-32 covers native digits.
    PA-76 covers the width and characters of the year field as produced
    by formatters, and string handling that depends on it. Merged per the class ledgers.
  - Why it is false (verified where marked):
    - Years past 9999 and before 0000 use expanded forms. Java prints
      `+10000-01-01` and `-0044-03-15`. JS `toISOString()` always uses a
      sign and six digits outside 0000 to 9999: `+010000-01-01T...Z` and
      `-000044-03-15T...Z` (both verified).
    - Some formatters do not zero-pad small years. Python
      `date(5, 1, 1).strftime('%Y-%m-%d')` gives `5-01-01` on Linux
      (glibc), while `isoformat()` gives `0005-01-01` (verified).
    - Postgres shows BC dates with a suffix (`0044-03-15 BC`) and years
      past 9999 with five digits.
    - Four characters need not be four ASCII digits. Python's `\d`
      matches Arabic-Indic digits by default for `str` patterns, so
      `\d{4}-\d{2}-\d{2}` accepts a date written in those digits, while
      `re.ASCII` rejects it. JS `\d` matches ASCII digits only (both
      verified).
    - The format string may not mean what it looks like: `YYYY` is the
      week-based year in Java and some other libraries (PA-3).
  - How it appears in code:
    - Regexes such as `^\d{4}-\d{2}-\d{2}$` that reject valid expanded
      years, or accept non-ASCII digits in Python.
    - Slicing by position (`s[0:4]` for year, `s[5:7]` for month), which
      breaks on signs, expanded years, or unpadded years.
    - Fixed-width columns (`CHAR(10)`) and fixed-width file layouts.
    - `strftime('%Y')` used to build machine-readable dates.
    - Text sorting of dates with signs or different widths (PA-28).
  - What to check:
    - Regexes, slicing, and fixed widths applied to date strings.
    - Formatters used to produce machine-readable dates.
    - Regex flags for digit classes.
  - Fix:
    - Parse dates with a library parser into typed values, then read
      fields from the value, never from string positions (BP-1).
    - Produce machine dates with ISO formatters (`isoformat()`,
      `toISOString()`, `java.time` `toString()`), not `strftime('%Y')`.
    - Use ASCII-only digit classes in validation (`[0-9]`, or Python
      `re.ASCII`), and normalize native digits deliberately (PA-32).
    - Decide whether expanded years are allowed, and validate the range
      explicitly (PA-72).
  - Not a finding:
    - Fixed four-digit patterns on fields whose documented range is 1000
      to 9999 and that are produced by an ISO formatter.
  - Escalate (NEEDS-HUMAN): file formats or partner interfaces with
    fixed-width date fields where out-of-range years may occur.
  - Proposed severity (for the user to decide): HIGH when string handling
    of years corrupts or rejects stored dates on a core path. MEDIUM for
    validation gaps and exports. LOW for test-only code.
- PA-77: Component-merge validity assumption. Code assumes that combining
  fields from two valid dates (for example the month from one and the day
  and year from another) produces a valid date.
  - Overlap: PA-2 covers impossible dates and month-addition overflow.
    PA-3 covers Feb 29 anniversaries. PA-53 covers components taken from
    separate clock reads. PA-77 covers building dates field by field, the
    order-dependence of setters, and date-plus-time merges in a zone.
    Merged per the class ledgers.
  - Why it is false:
    - Month lengths differ, so day 29, 30, or 31 from one date does not
      exist in every month and year of another (PA-2). Feb 29 from a leap
      year does not exist in a common year (PA-3).
    - Setters behave differently and depend on order (verified):
      - JS: `new Date(2026, 0, 31)` then `setMonth(3)` gives May 1.
        Setting day 30 then month February gives March 2, and setting
        month February then day 30 also gives March 2. The date silently
        rolls over.
      - Python `date(2026, 1, 31).replace(month=2)` raises "day is out of
        range for month".
      - Java `LocalDate.of(2026, 1, 31).withMonth(2)` clamps to
        2026-02-28, while `withDayOfMonth(30)` on February throws.
    - A date from one source and a time from another may not exist
      together in a zone. Java `ZonedDateTime.of(2026-03-08, 02:30,
      America/New_York)` silently becomes `03:30-04:00`, while
      `ZonedDateTime.ofStrict` throws (both verified). In the fall-back
      hour the merged local time is ambiguous (PA-1, PA-44).
    - Week fields do not combine freely: ISO week 53 exists only in some
      week-years (PA-7), and a week number from one year paired with
      another year can name a week that does not exist.
    - Fields from different calendars cannot be mixed (PA-41).
  - How it appears in code:
    - Separate day, month, and year inputs combined without validating the
      whole date.
    - "Birthday this year" built by copying month and day into the current
      year.
    - "Same day next month" built by setting the month field.
    - Date from one record combined with time from another, then given a
      zone.
    - Field setters applied one after another on a mutable date object.
  - What to check:
    - Construction of dates from parts, and the order of setter calls.
    - Validation after combining fields.
    - Date-plus-time-plus-zone construction: gap and overlap handling.
  - Fix:
    - Construct the whole date at once with a validating API, and handle
      the error (BP-1).
    - State the policy for impossible combinations: clamp, roll, or reject
      (PA-2).
    - Use library adjusters and arithmetic (Java
      `TemporalAdjusters.lastDayOfMonth`, `plusMonths`) instead of raw
      field setters.
    - When attaching a zone, choose gap and overlap handling explicitly
      (for example `ofStrict`, or an explicit earlier or later offset)
      (PA-44).
    - Use immutable date types so setter order cannot change results.
  - Not a finding:
    - Library construction with a documented, tested invalid-combination
      policy.
  - Escalate (NEEDS-HUMAN): anniversaries, renewals, or recurring dates
    built from parts where the policy for missing days is not stated.
  - Proposed severity (for the user to decide): HIGH when merged dates
    silently roll over or shift on a core path (billing, renewals,
    appointments). MEDIUM for form validation and display. LOW for
    test-only code.
- PA-78: Leap-year merge assumption. Code assumes that if both source
  years are leap years, combining the month from one date with the day and
  year from another always gives a valid date.
  - Overlap: PA-77 covers component merges in general. PA-78 covers the
    belief that matching leap-year status makes merges safe. Merged per the class ledgers.
  - Why it is false:
    - Leap-year status only governs February. Months still have 30 or 31
      days: April from 2024-04-15 with day 31 and year 2028 from
      2028-01-31 gives April 31, 2028, which does not exist.
    - Day 30 or 31 merged into February fails in any year.
    - Historical gaps: 1752 was a leap year in Britain, yet
      1752-09-03 to 1752-09-13 did not exist there (PA-40, PA-45). Taking
      September from another leap year with day 10 and year 1752 gives a
      date that never existed in British records.
    - Leap status depends on the calendar. A year can be leap in the
      Julian calendar and common in the Gregorian (1700, 1800, 1900)
      (PA-42, PA-43). In the Hebrew calendar a leap year adds a month
      (Adar I), so month identity changes with leap status (PA-42).
    - Combining with a time of day in a zone can still land in a DST gap
      or overlap, whatever the year (PA-77).
  - How it appears in code:
    - Merge or "same day in another year" logic that checks only
      `is_leap(year)` before building the date.
    - Tests that cover Feb 29 between leap years but not 30th and 31st
      days across months.
  - What to check:
    - Validation that relies on leap-year tests instead of constructing
      the date.
  - Fix:
    - Construct and validate the full date with the library, whatever the
      leap-year status (PA-77, BP-1).
    - Apply the stated policy for impossible combinations (PA-2).
    - For historical dates, validate in the source calendar and region
      (PA-41, PA-45).
  - Not a finding:
    - Merges validated by constructing the full date.
  - Escalate (NEEDS-HUMAN): none specific beyond PA-77.
  - Proposed severity (for the user to decide): same as PA-77.
- PA-79: Published-algorithm completeness assumption. Code assumes a
  standards body's published algorithm for adding durations to dates
  (for example the W3C XML Schema algorithm) works correctly in every
  case.
  - Overlap: PA-2 covers month-end policies. PA-44 covers elapsed versus
    wall-clock addition. PA-48 covers modulo of negative numbers. PA-79
    covers the hidden assumptions, version changes, and porting errors in
    published date algorithms. Merged per the class ledgers.
  - Why it is false:
    - Algorithms carry assumptions that may not match the requirement.
      The XML Schema algorithm (Part 2, appendix "Adding durations to
      dateTimes") works on fixed UTC offsets with no zone rules, so it
      knows nothing about DST or rule changes (PA-9, PA-36). It pins the
      day to the end of a shorter month, one month-end policy among
      several (PA-2).
    - Duration addition is order-dependent. Adding one day then one month
      to 2000-03-30 gives 2000-04-30, but adding one month then one day
      gives 2000-05-01 (verified with Java's equivalent clamping
      arithmetic). The XML Schema specification notes this.
    - Durations are only partially ordered. XML Schema treats P1M and P30D
      as incomparable, because a month has no fixed length.
    - Specifications change between versions. XML Schema 1.0 had no year
      0000. XML Schema 1.1 allows year 0000 as 1 BCE, matching ISO 8601
      astronomical numbering (PA-19). Code written to one version
      mishandles data from the other. Specifications also publish errata.
    - Porting pseudocode changes its meaning. Spec helper functions such
      as `fQuotient` and `modulo` use floor semantics. Integer division
      and `%` truncate toward zero in Java, C, and JS: Java `-7 / 2` is
      -3 and `-7 % 2` is -1, while `Math.floorDiv` gives -4 and
      `Math.floorMod` gives 1. Python `//` and `%` floor: -4 and 1 (all
      verified). A direct port breaks for negative values (BC years,
      negative durations).
    - No published algorithm covers leap seconds, historical calendars,
      or regional rules unless it says so.
  - How it appears in code:
    - Hand-ported specification pseudocode instead of a maintained
      library.
    - Truncating division or modulo in ported date arithmetic.
    - Business durations modeled as `xs:duration` and compared or summed
      as if months had fixed lengths.
    - Data exchanged between systems built on different specification
      versions.
  - What to check:
    - Any date algorithm implemented from a specification.
    - Division and modulo semantics in ported code.
    - Which specification version and errata the code follows.
    - Whether the algorithm's assumptions (fixed offsets, month-end
      policy, no leap seconds) match the requirement.
  - Fix:
    - Prefer a maintained library that implements the specification and
      has tests (BP-1).
    - When porting is unavoidable, use floor division and floor modulo
      explicitly, and port the specification's test cases too.
    - Record the specification version and errata followed.
    - Check the algorithm's assumptions against the requirement, and use
      zone-aware arithmetic where local time matters (PA-44).
    - Test negative values, month-ends, leap years, year 0, and DST
      transitions.
  - Not a finding:
    - Library-provided implementations used within their documented
      assumptions.
  - Escalate (NEEDS-HUMAN): interfaces whose duration semantics follow a
    specification version that the requirement does not name.
  - Proposed severity (for the user to decide): HIGH when ported or
    misapplied algorithms produce wrong dates on a core path. MEDIUM for
    reporting and data exchange. LOW for test-only code.
- PA-80: Standard-library year range assumption. Code assumes the
  language's standard library handles negative years and years above
  10000.
  - Overlap: PA-18 lists type ranges. PA-72 covers valid years and
    expanded ISO forms. PA-76 covers year width. PA-80 covers library and
    serialization support for extreme years, and the narrowest layer in a
    pipeline. Merged per the class ledgers.
  - Why it is false:
    - Support varies by language:
      - Python `datetime`: years 1 to 9999 only (PA-18, PA-72).
      - .NET `DateTime`: years 1 to 9999.
      - JS `Date`: about -271821 to 275760, with six-digit signed years
        in `toISOString()` (PA-76).
      - Java `java.time`: about +/-1 billion years (PA-72).
      - Go `time`: formats -0044 and 12026, but `MarshalJSON` fails with
        "year outside of range [0,9999]" (verified).
      - C `struct tm` stores the year as an offset from 1900, and
        `strftime` output for negative years is implementation-defined.
    - Common data libraries are narrower than the language: pandas
      nanosecond timestamps cover only 1677-09-21 to 2262-04-11
      (documented; not verified here because pandas is not installed).
    - Serialization formats limit years: RFC 3339 and JSON Schema
      `date-time` allow 0000 to 9999. Protobuf `Timestamp` documents
      0001-01-01 to 9999-12-31. BigQuery `DATE` covers 0001 to 9999.
    - One component accepting a year says nothing about the next one in
      the pipeline.
  - How it appears in code:
    - Historical, astronomical, geological, or far-future data passed
      through standard date types that cannot hold it.
    - Serialization failing only for out-of-range values in production
      (Go JSON, protobuf, BigQuery loads).
    - Data frames silently converting or failing on dates outside pandas'
      nanosecond range.
  - What to check:
    - Every layer a date passes through, and each one's supported range.
    - Domain ranges for historical or scientific data.
  - Fix:
    - Establish the domain's year range and verify every layer supports
      it, or reject out-of-range values at input (PA-72).
    - Use wide-range types where needed (Java `java.time`, Astropy `Time`
      for astronomy), or store deep-time values as numeric years or
      offsets with a named reference (for example millions of years ago)
      rather than calendar dates.
    - Choose coarser units in data libraries when range matters more than
      nanosecond precision.
    - Test serialization of the extreme values the domain allows.
  - Not a finding:
    - Modern-date systems that validate to a range every layer supports.
  - Escalate (NEEDS-HUMAN): scientific, archival, or long-horizon systems
    whose required year range is not stated.
  - Proposed severity (for the user to decide): HIGH when extreme years
    crash or corrupt a core path or serialization boundary. MEDIUM for
    analytics. LOW for test-only code.
- PA-81: Safe truncation assumption. Code assumes that converting a
  millisecond timestamp to second precision can simply drop the
  milliseconds without consequence.
  - Overlap: PA-23, PA-24, and PA-29 cover precision loss and mixed
    precision. PA-73 covers display truncation. PA-79 covers floor versus
    truncating division. PA-81 covers the conversion step itself:
    direction of rounding, negative values, boundaries, and accumulated
    error. Merged per the class ledgers.
  - Why it is false:
    - Truncation is wrong for negative timestamps. -1500 ms is
      1969-12-31T23:59:58.500Z. Truncating toward zero gives
      23:59:59 (JS `Math.trunc`, Java `-1500 / 1000` = -1, Python
      `int(-1.5)` = -1), a second later than the true second. Flooring
      gives 23:59:58 (JS `Math.floor`, Java `Instant.getEpochSecond()`
      = -2, Python `math.floor`) (all verified).
    - Rounding instead of truncating can move a value into the next
      second, minute, day, month, or year: 23:59:59.6 becomes the next
      day (PA-23).
    - Boundaries change outcomes. A submission at 17:00:00.900 truncated
      to 17:00:00 passes a `<= 17:00:00` deadline it actually missed.
      Rounded, a value at 16:59:59.600 fails a deadline it met.
    - Distinct events collide and lose their order (PA-30).
    - Durations computed from truncated endpoints can be off by up to a
      second each way, and can be negative (PA-29). Truncating each of
      many durations biases totals downward. Rounding each one up biases
      them upward.
  - How it appears in code:
    - `ms / 1000` with integer division, `Math.trunc`, or `int()` on epoch
      values that can be negative.
    - Deadline, expiry, or cutoff checks done after reducing precision.
    - Per-item duration truncation or rounding before summing for billing
      or usage.
    - Second-precision values used as keys or for ordering.
  - What to check:
    - Every precision-reducing conversion: method, direction, and sign
      handling.
    - Whether comparisons happen before or after reduction.
    - Whether rounding rules for billing are specified.
  - Fix:
    - Use floor for epoch conversions (`Math.floorDiv`, `Math.floor`,
      `Instant.getEpochSecond()`, library truncation methods such as Java
      `truncatedTo(ChronoUnit.SECONDS)`) (PA-79, BP-1).
    - Compare against deadlines and cutoffs at full precision, then reduce
      precision only for storage or display.
    - Sum durations at full precision and round once, by the specified
      rule.
    - Keep a tie-breaker when reduced values order or key records (PA-30).
  - Not a finding:
    - Truncation of non-negative values for display or logging, with no
      comparison or arithmetic depending on it.
  - Escalate (NEEDS-HUMAN): billing or usage metering where the rounding
    rule (per item or total, up, down, or nearest) is not stated.
  - Proposed severity (for the user to decide): HIGH when reduced
    precision changes deadline outcomes, billing totals, or pre-1970
    values on a core path. MEDIUM for ordering and reports. LOW for
    test-only code.
- PA-82: Safe rounding assumption. Code assumes that when reducing a
  millisecond timestamp to seconds, dropping the fraction is safe as long
  as it is below 0.5 (rounding to nearest).
  - Overlap: PA-81 covers truncation. PA-82 covers rounding to nearest:
    boundary effects that remain, negative values, half-way cases, and
    accumulated error. Merged per the class ledgers.
  - Why it is false:
    - Rounding still moves values by up to half a second, so any boundary
      within that range flips. 17:00:00.400 rounds to 17:00:00 and passes
      a `<= 17:00:00` deadline it missed. Values of .5 and above round up,
      so 23:59:59.500 becomes the next day, month, or year (PA-23).
    - The fraction of a negative value is easy to get wrong. -1600 ms is
      1969-12-31T23:59:58.400Z, whose nearest second is 23:59:58. In JS,
      `-1600 % 1000` is -600, which is "less than 500", so naive code
      truncates toward zero and gets 23:59:59 (verified).
    - Half-way cases round differently by language (verified):
      - JS `Math.round(-1.5)` is -1, and `Math.round(2.5)` is 3.
      - Java `Math.round(-1.5)` is -1, `Math.round(2.5)` is 3, and
        `Math.rint(2.5)` is 2.0.
      - Python `round(-1.5)` is -2, `round(2.5)` is 2, and `round(0.5)` is
        0 (round half to even).
    - Floating-point conversions can land just below or above .5, so the
      same millisecond value rounds differently depending on how it was
      computed.
    - Rounding each item and then summing differs from summing and then
      rounding, by up to half a second per item.
  - How it appears in code:
    - Fraction computed with `%` on possibly negative values.
    - Language-default `round()` used without knowing its half-way rule.
    - Deadline or cutoff checks after rounding.
    - Per-item rounding before totals.
    - Epoch values converted through floating point before rounding.
  - What to check:
    - Rounding mode, sign handling, and arithmetic type at every
      precision reduction.
    - Whether comparisons happen before or after rounding.
  - Fix:
    - Choose the rounding mode deliberately (floor, half-up, half-even)
      from the requirement, and apply it with exact integer or decimal
      arithmetic (Java `BigDecimal` with `RoundingMode`, Python `decimal`)
      instead of language defaults.
    - Compute fractions with floor modulo (PA-79, PA-81).
    - Compare against deadlines at full precision.
    - Sum at full precision and round once.
  - Not a finding:
    - Rounding for display only, with comparisons done at full precision.
  - Escalate (NEEDS-HUMAN): billing, metering, or deadline rules where the
    rounding mode is not stated (PA-81).
  - Proposed severity (for the user to decide): same as PA-81.
- PA-83: Two-digit year range assumption. Code assumes a two-digit year
  always means a year from 1900 to 2099, and that every tool expands it the
  same way.
  - Overlap: PA-27 covers two-digit years and the X.509 pivot as an input
    format issue. PA-83 covers pivot rules across tools and domains where
    the 1900 to 2099 window is wrong. Merged per the class ledgers.
  - Why it is false:
    - Tools use different pivots (verified where marked):
      - Python `strptime('%y')`: 69 to 99 become 1969 to 1999, 00 to 68
        become 2000 to 2068 (verified).
      - JS `new Date("01/02/yy")` in V8: 49 becomes 2049, 50 becomes 1950
        (verified).
      - Java `DateTimeFormatter` with `yy`: always 2000 to 2099, so 99
        becomes 2099 (verified).
      - Java `SimpleDateFormat`: a sliding window from 80 years before now
        to 20 years after. In October 2026, 46 becomes 2046 and 47 becomes
        1947 (verified). The result changes as time passes.
      - .NET: `Calendar.TwoDigitYearMax`, commonly 2049, and Windows
        regional settings can change it.
      - MySQL: 70 to 99 become 1970 to 1999, 00 to 69 become 2000 to 2069.
      - X.509 `UTCTime`: 50 to 99 become 19xx, 00 to 49 become 20xx
        (PA-27).
    - Domains need different windows:
      - Birth years for people over 100 fall before the window, and a
        POSIX-style pivot turns a person born in 1925 into a 2025 birth
        (Python gives 2025 for "25", verified).
      - Card expiry years are always in the near future.
      - Historical records reach back to the 1800s and earlier.
      - Long leases, bonds, and retention dates reach past 2099.
    - The same string becomes different years in different layers, so a
      value can change as it moves through a system.
  - How it appears in code:
    - `%y`, `yy`, or default parsing of two-digit years with no explicit
      pivot.
    - Different tools in one pipeline expanding the same field.
    - Birth dates or historical dates entered or imported with two-digit
      years.
    - Pivot results that change over time with sliding windows.
  - What to check:
    - Every place a two-digit year is parsed, and the pivot each tool
      applies.
    - The plausible range of each field's domain.
  - Fix:
    - Require four-digit years at input and in every stored or exchanged
      format.
    - Where two-digit years cannot be avoided, apply one explicit,
      domain-specific rule (for example "birth years are in the past",
      "expiry years are within the next 20 years") in one place, and
      validate the result's plausibility.
    - Never rely on library default pivots.
  - Not a finding:
    - Two-digit years displayed for convenience where four-digit values
      are stored and never re-parsed.
  - Escalate (NEEDS-HUMAN): legacy data or partner feeds with two-digit
    years whose intended century cannot be established.
  - Proposed severity (for the user to decide): HIGH when two-digit years
    are expanded into stored birth dates, expiries, or legal dates on a
    core path. MEDIUM for reports and display. LOW for test-only code.
- PA-84: Single-pass parsing assumption. Code assumes a date-time string
  can be parsed by reading digits one character at a time, never needing
  to look ahead or backtrack.
  - Overlap: PA-27 and PA-28 cover format variety. PA-76 covers year
    width and slicing. PA-32 covers native digits and direction marks.
    PA-84 covers parsing mechanics: variable-width and adjacent fields,
    and later tokens that change the meaning of earlier ones. Merged per the class ledgers.
  - Why it is false:
    - Variable-width fields without separators are ambiguous. Python
      `strptime('2026111', '%Y%m%d')` returns 2026-11-01, although
      2026-01-11 fits equally. `strptime('202611', '%Y%m%d')` returns
      2026-01-01 (both verified). The parser picked one split silently.
    - Unpadded numbers in separated formats (`1/2/2026`, `12/1/2026`)
      have variable width, so a field's end is known only at the next
      separator.
    - ISO 8601 has forms that look alike until the end of the field:
      `2026-11` (month), `2026-307` (ordinal day), and week dates
      (`2026-W45-3`, `2026W453`). Python 3.11 `date.fromisoformat`
      accepts both week forms (2026-11-04) but rejects the ordinal form
      `2026-307` (verified).
    - Optional and variable parts: fractional seconds of any length,
      offsets as `Z`, `+05`, `+0530`, or `+05:30`, and `T` or a space as
      the separator (PA-28).
    - Two-digit and four-digit years (PA-83).
    - Month names of different lengths and shared prefixes (`Jun`,
      `June`, `Jul`), which depend on locale (PA-27).
    - Later tokens change earlier fields. `AM`/`PM` changes the hour:
      Python parses `12:30 AM` as 00:30 (verified). Trailing zone names
      or offsets change the instant.
    - Java's `DateTimeFormatter` needs special "adjacent value parsing"
      rules for patterns such as `yyyyMMddHHmm`, because `yyyy` alone has
      no fixed width.
  - How it appears in code:
    - Hand-written character-by-character parsers or regexes with greedy
      quantifiers such as `(\d{1,2})(\d{1,2})`.
    - Compact formats without separators accepted with variable-width
      fields.
    - Parsing that ignores trailing tokens (`AM`/`PM`, offsets, zone
      names), or partial matches that leave text unread.
    - 12-hour clock values handled without the 12 AM and 12 PM rules.
  - What to check:
    - Custom parsers and regexes for dates and times.
    - Whether parses must consume the whole string.
    - Compact and unpadded inputs.
  - Fix:
    - Parse with library parsers and explicit formats in strict mode
      (BP-1, PA-27).
    - Require separators or fixed-width, zero-padded fields. Reject
      compact variable-width input.
    - Match the whole string, and fail on leftover characters.
    - Let the library handle `AM`/`PM`, offsets, and zone tokens, and test
      12:00 AM, 12:00 PM, and offsets in every form the format allows.
  - Not a finding:
    - Library parsing of a strict, fixed-width, documented format.
  - Escalate (NEEDS-HUMAN): partner or legacy inputs in compact or
    unpadded formats whose field widths are not documented.
  - Proposed severity (for the user to decide): HIGH when ambiguous parses
    store wrong dates on a core path. MEDIUM for imports and logs. LOW for
    test-only code.
- PA-85: Single-pass formatting assumption. Code assumes a date-time can
  be printed field by field, left to right, never revisiting what was
  already written.
  - Overlap: PA-73 and PA-74 cover display fidelity. PA-76 covers year
    width. PA-82 covers rounding. PA-32 covers locale order, digits, and
    direction marks. PA-85 covers formatting mechanics: carries from
    later fields into earlier ones, and words whose form depends on the
    rest of the value. Merged per the class ledgers.
  - Why it is false:
    - Rounding a fraction carries into earlier fields. Printing
      23:59:59.9996 with milliseconds needs a carry. Naive code
      `'%02d.%03d' % (59, round(0.9996 * 1000))` prints `59.1000`
      (verified). Correct output for 2026-12-31T23:59:59.9996 is
      `2027-01-01T00:00:00.000`, changing every field back to the year
      (verified by rounding the value first, then formatting).
    - The local fields depend on the zone offset for the whole instant,
      so the hour cannot be printed before the offset is resolved (PA-9).
    - Grammatical forms depend on context. Russian uses the genitive month
      name in a full date ("1 yanvarya") and the nominative alone
      ("yanvar"). Java exposes these as `MMMM` (format form) and `LLLL`
      (stand-alone form) (verified, transliterated here).
    - Era years have special forms. The first year of a Japanese era is
      written "gannen" (first year), not 1: Node `Intl` prints Reiwa
      gannen for 2019 with the Japanese calendar (verified).
    - Ordinals and plurals depend on the number: 1st, 2nd, 3rd, but 11th,
      12th, and 13th in English. Relative times ("in 1 minute", "2 minutes
      ago") need plural rules per language.
    - 12-hour clocks print hour 0 as 12 and add a marker after the time.
    - Field order, digits, and direction marks vary by locale (PA-32).
      Sign and width vary for extreme years (PA-76). Aligned columns need
      the full width before printing.
  - How it appears in code:
    - Hand-written formatters that build strings field by field with
      separate rounding of the fraction.
    - Month names from a fixed array, ignoring grammatical case.
    - Ordinal suffixes by last digit only.
    - Fixed field order and separators for every locale.
    - 12-hour output computed as `hour % 12` without the 12 rule.
  - What to check:
    - Custom formatting code and string concatenation of date fields.
    - Where rounding happens relative to formatting.
    - Locale-specific forms: month names, ordinals, plurals, eras.
  - Fix:
    - Round or truncate the value first, with its full carry, then format
      the result (PA-82).
    - Use library formatters: ISO formatters for machine output, ICU or
      `Intl` for human output, including stand-alone versus format forms
      (BP-1).
    - Use `Intl.PluralRules`, `Intl.RelativeTimeFormat`, or ICU message
      formats for plurals, ordinals, and relative times.
  - Not a finding:
    - Library formatting of values already rounded to the displayed
      precision.
  - Escalate (NEEDS-HUMAN): user-facing date text in languages the product
    supports where grammatical requirements are not specified.
  - Proposed severity (for the user to decide): HIGH when formatted output
    with broken carries is stored, exchanged, or used in legal documents
    on a core path. MEDIUM for user-facing text. LOW for test-only code.
- PA-86: Exotic-format assumption. Code assumes it will never need to
  parse less common standard forms such as `---12Z` or
  `P12Y34M56DT78H90M12.345S`.
  - Overlap: PA-27 covers format variety. PA-79 covers XML Schema
    duration semantics. PA-84 covers parsing mechanics. PA-86 covers
    partial-date and duration formats that real interfaces use, and
    library support for them. Merged per the class ledgers.
  - Why it is false:
    - XML Schema defines partial dates in daily use: `gDay` (`---12Z`, the
      12th of any month, in UTC), `gMonth` (`--12`), `gMonthDay`
      (`--12-25`), `gYearMonth` (`2026-10`), and `gYear` (`2026`). They
      describe recurring days, anniversaries, and expiry months.
    - ISO 8601 durations need not be normalized.
      `P12Y34M56DT78H90M12.345S` is valid: 34 months, 56 days, 78 hours,
      and 90 minutes do not have to be carried. Months normalize into
      years, but days do not normalize into months, and hours do not
      normalize into days without a zone (PA-1, PA-79).
    - Other ISO 8601 forms appear in practice: week durations (`P2W`),
      the alternative format (`P0003-06-04T12:30:05`), negative durations
      in XML Schema (`-P1D`), intervals (`2026-01-01/2026-02-01`,
      `2026-01-01/P1M`, `P1M/2026-02-01`), and repeating intervals
      (`R5/2026-01-01T00:00Z/P1D`).
    - Real interfaces use them: iCalendar `DURATION` values (RFC 5545,
      for example `P15DT5H0M20S` and `P7W`), HTML `<time datetime>`
      durations, JSON Schema `duration` (RFC 3339 Appendix A), OData
      `Edm.Duration`, XML and SOAP services, and many cloud and media
      APIs (for example `PT1H2M3S` video lengths).
    - Library support is partial (verified):
      - Java `Duration.parse` and `Period.parse` both reject
        `P12Y34M56DT78H90M12.345S`. `Duration` accepts only days and time
        parts, `Period` only date parts. Separately, `Duration` normalizes
        `PT78H90M12.345S` to `PT79H30M12.345S`, and `Period.normalized()`
        turns `P12Y34M56D` into `P14Y10M56D`.
      - Python's standard library has no ISO duration parser.
      - Node 22 has no built-in `Temporal`, so JS has no standard
        duration parser there.
    - Other ecosystems use their own duration syntaxes: Go
      (`1h30m`), Prometheus (`5m`), systemd (`1h 30min`).
  - How it appears in code:
    - Hand-written regexes for durations that accept only normalized or
      common forms, or only `PT...` time parts.
    - Durations converted to seconds with fixed month and day lengths.
    - Partial dates (`--12-25`) rejected, or forced into full dates with
      an invented year.
    - Different duration syntaxes mixed in configuration and APIs.
  - What to check:
    - Every interface that exchanges durations or partial dates, and the
      grammar it declares.
    - Duration parsing and conversion code.
  - Fix:
    - Identify the exact grammar each interface uses (XML Schema, ISO
      8601 profile, RFC 5545, RFC 3339 Appendix A) and parse with a
      library that supports it. Adding a parsing library needs user
      approval under the dependency rules.
    - Keep calendar parts (years, months, days) separate from exact time
      parts, and apply them with calendar arithmetic in a zone (PA-44,
      PA-79).
    - Model partial dates as their own types (month-day, year-month),
      not full dates.
    - Reject unsupported forms loudly instead of misreading them.
  - Not a finding:
    - Interfaces that document a narrow duration profile and validate
      against it.
  - Escalate (NEEDS-HUMAN): interfaces exchanging durations whose grammar
    and calendar semantics are not documented.
  - Proposed severity (for the user to decide): HIGH when misparsed
    durations or partial dates drive scheduling, billing, or expiry on a
    core path. MEDIUM for configuration and imports. LOW for test-only
    code.
- PA-87: Twenty-four-zone assumption. Code assumes there are only 24
  time zones.
  - Overlap: PA-49 covers the offset range, non-hour offsets, and
    longitude bands. PA-52 covers zone renames and splits. PA-67 covers
    abbreviations. PA-87 covers how many zones and offsets exist, the
    difference between a zone and an offset, and competing zone
    identifier systems. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b where marked):
    - This host's tz data lists 498 zone names (verified; installations
      differ, and this one lacks some backward-compatibility links,
      PA-52).
    - 40 distinct UTC offsets were in use across January and July 2026,
      from -12:00 to +14:00, including -09:30, -03:30, -02:30, +03:30,
      +04:30, +05:30, +05:45, +06:30, +08:45, +09:30, +10:30, +12:45, and
      +13:45 (verified).
    - A zone is not an offset. A zone is a region with a shared history
      of offsets and rules. Zones that share an offset today can differ in
      DST and in history: Phoenix and Denver share -07:00 in winter but
      not in summer (PA-33).
    - Other identifier systems exist. Windows has its own time zone IDs
      (about 140), with names such as "Pacific Standard Time" that also
      cover summer time. Mapping them to IANA IDs needs the CLDR
      `windowsZones` data or a library (for example .NET 6 and later
      `TimeZoneInfo.TryConvertWindowsIdToIanaId`).
    - The idealized 24 one-hour bands exist only in nautical time at sea
      (15-degree bands, with the 12-hour band split at the date line) and
      in military letter zones (`Z` and `A` to `Y`, skipping `J`). Civil
      zones follow borders, not longitude (PA-49).
  - How it appears in code:
    - Enums, lookup tables, or pickers with 24 zones or whole-hour
      offsets.
    - Offsets stored as integers from -12 to +12 (PA-49, PA-51).
    - Offsets used as zone identity, losing DST and history (PA-9).
    - Ad hoc mappings between Windows and IANA IDs.
  - What to check:
    - Zone enumerations and pickers.
    - Types used to store zones.
    - Conversions between zone identifier systems.
  - Fix:
    - Store IANA zone IDs and generate zone lists from the tz data at
      runtime (BP-1, PA-35).
    - Offer pickers by region and city, and show the current offset as a
      computed label.
    - Map Windows IDs to IANA IDs with CLDR data or the platform's
      converter.
  - Not a finding:
    - Nautical or military systems that use their own documented zone
      schemes by design.
  - Escalate (NEEDS-HUMAN): integrations that exchange zones in a
    non-IANA scheme without a documented mapping.
  - Proposed severity (for the user to decide): HIGH when zone models
    based on 24 offsets assign wrong times to users on a core path.
    MEDIUM for pickers and display. LOW for test-only code.
- PA-88: Whole-hour offset assumption. Code assumes every zone is a whole
  number of hours from UTC.
  - Overlap: PA-33, PA-49, PA-51, and PA-87 list non-hour offsets and
    second-level historical offsets. PA-88 covers who is affected today
    and the hour-based code patterns that break. Merged per the class ledgers.
  - Why it is false (offsets for January and July 2026, verified):
    - India (`Asia/Kolkata`) and Sri Lanka (`Asia/Colombo`): +05:30. India
      alone has well over a billion people.
    - Iran (`Asia/Tehran`): +03:30. Afghanistan (`Asia/Kabul`): +04:30.
      Myanmar (`Asia/Yangon`): +06:30. Nepal (`Asia/Kathmandu`): +05:45.
    - Newfoundland (`America/St_Johns`): -03:30 in winter, -02:30 in
      summer.
    - South Australia (`Australia/Adelaide`): +10:30 in January, +09:30 in
      July. Northern Territory (`Australia/Darwin`): +09:30 all year.
    - Eucla (`Australia/Eucla`): +08:45. Marquesas (`Pacific/Marquesas`):
      -09:30. Chatham Islands (`Pacific/Chatham`): +13:45 in January,
      +12:45 in July.
    - Historical offsets include seconds (PA-51).
  - How it appears in code:
    - Offsets stored or passed as integer hours. JS
      `getTimezoneOffset() / 60` with integer truncation drops the
      minutes.
    - Time conversion by adding the offset to the hour field only, leaving
      minutes unchanged.
    - Hourly jobs, reports, partitions, rate limits, or billing aligned to
      UTC hours and labeled as local hours. In Kolkata, UTC 09:00 is
      14:30 local (verified), so every local hour boundary falls at UTC
      half past.
    - Pickers and validators offering only whole-hour offsets.
    - DST logic that adds one hour to an integer-hour offset (PA-38).
  - What to check:
    - Offset types and units.
    - Hour-aligned schedules and buckets: aligned to which zone.
    - Conversions that touch only the hour field.
  - Fix:
    - Store zone IDs, or offsets in minutes or seconds (PA-51), and convert
      with the library (BP-1).
    - Align hourly buckets and schedules to local hour boundaries computed
      per zone where local hours matter, or label them as UTC hours.
    - Test with +05:30, +05:45, -03:30, and +12:45 zones.
  - Not a finding:
    - UTC-only hourly processing that is labeled as UTC.
  - Escalate (NEEDS-HUMAN): hourly billing, quotas, or reports for users
    in non-hour zones where the intended hour boundary (UTC or local) is
    not stated.
  - Proposed severity (for the user to decide): HIGH when times for users
    in non-hour zones are wrong on a core path, or hourly billing uses the
    wrong boundary. MEDIUM for reports and pickers. LOW for test-only
    code.
- PA-89: Zone-from-clock inference assumption. Code assumes reading the
  client's clock and comparing it with UTC reliably reveals the client's
  time zone.
  - Overlap: PA-14 and PA-15 cover client clock error and skew. PA-17
    covers capturing the user's zone. PA-87 covers zones versus offsets.
    PA-89 covers inferring a zone from an offset, and the
    `getTimezoneOffset` traps. Merged per the class ledgers.
  - Why it is false:
    - An offset does not identify a zone. On this host, 19 zones were at
      -07:00 in January 2026 (including Denver, Edmonton, Hermosillo, and
      Phoenix) and 16 in July (including Los Angeles, Vancouver,
      Hermosillo, and Phoenix) (verified). The offset says nothing about
      DST rules or future offsets (PA-9, PA-33).
    - The client's clock may be wrong by any amount (PA-11, PA-12,
      PA-15). A user with the right wall time but the wrong zone setting
      produces an offset off by whole hours (PA-15).
    - Comparing client time with server time includes network delay and
      skew, so the result must be rounded, and rounding to 15 or 30
      minutes can pick the wrong offset (PA-14, PA-88).
    - JS `getTimezoneOffset()` has an inverted sign and depends on the
      date: in New York it returns 240 (minutes west of UTC) in July and
      300 in January (verified). Code that uses today's value for other
      dates, or forgets the sign, is wrong.
    - Privacy settings report UTC regardless of location (Firefox with
      `privacy.resistFingerprinting`, Tor Browser) (PA-17). IP
      geolocation and VPNs mislead too.
    - Users may want a zone other than their device's: travelers, remote
      staff working to headquarters time (PA-17, PA-50).
  - How it appears in code:
    - `clientNow - serverNow` rounded to an offset and stored as the
      user's zone.
    - `new Date().getTimezoneOffset()` sent to the server and used for
      every date, or mapped to an arbitrary zone with that offset.
    - Sign errors with `getTimezoneOffset()`.
    - Offsets stored instead of zone IDs (PA-9).
  - What to check:
    - How the user's zone is determined, stored, and confirmed.
    - Uses of `getTimezoneOffset()` and clock-difference calculations.
  - Fix:
    - Read the IANA zone from the platform
      (`Intl.DateTimeFormat().resolvedOptions().timeZone`, OS settings)
      as a default, confirm it with the user, and store the IANA ID
      (PA-17).
    - Let users override it, and handle `UTC` reports from privacy modes
      by asking.
    - Compute offsets per date from the zone ID, never from today's
      offset.
    - Never infer the zone from clock differences.
  - Not a finding:
    - Offsets taken for a specific instant to display that instant, with
      the zone ID stored separately.
  - Escalate (NEEDS-HUMAN): products where the zone that governs a user's
    deadlines (device, profile, or business location) is not stated.
  - Proposed severity (for the user to decide): HIGH when inferred zones
    or offsets drive deadlines, scheduling, or billing on a core path.
    MEDIUM for display defaults. LOW for test-only code.
- PA-90: Uniform auto-adjustment assumption. Code assumes it knows whether
  the software stack converts times for zones and DST automatically, and
  that every layer behaves the same way.
  - Overlap: PA-8, PA-10, and PA-17 cover host, database, and client
    zones. PA-90 covers implicit conversions at each hop of a stack, and
    the double-conversion and no-conversion bugs between them. Merged per the class ledgers.
  - Why it is false: layers differ, and their behavior depends on type,
    configuration, and version.
    - Databases: MySQL `TIMESTAMP` converts between the session zone and
      UTC, while `DATETIME` does not convert. Postgres `timestamptz`
      interprets offset-less input in the session `TimeZone` and renders
      output in it, `timestamp` does not convert, and casts between the
      two use the session zone (PA-10).
    - Drivers: JDBC `getTimestamp` on zone-less columns applies the JVM
      default zone. MySQL Connector/J behavior depends on settings such as
      `connectionTimeZone` and `preserveInstants`, whose defaults changed
      across 8.0 releases.
    - ORMs: Django stores UTC and converts to the current zone when
      `USE_TZ` is on (the default since Django 5.0), and uses naive local
      times when it is off. Rails converts with `config.time_zone` and
      `ActiveRecord.default_timezone`. Hibernate uses
      `hibernate.jdbc.time_zone` when set.
    - Serializers: JS `JSON.stringify` writes a `Date` as UTC with `Z`, so
      `2026-07-01T12:00:00-04:00` becomes `2026-07-01T16:00:00.000Z`
      and the original offset is gone (verified). Jackson's
      `ADJUST_DATES_TO_CONTEXT_TIME_ZONE` (on by default) converts
      deserialized `OffsetDateTime` and `ZonedDateTime` values to the
      context zone.
    - Languages: Python `astimezone()` with no argument converts to the
      host zone: UTC 12:00 becomes `21:00+09:00` on a Tokyo host
      (verified). JS `Date` getters use the host zone (PA-8).
    - Clients: HTML `<input type="date">` `valueAsDate` returns UTC
      midnight. Mobile date pickers return instants in the device zone.
    - Tools: BI dashboards and monitoring tools often render in the
      viewer's browser zone. Logging frameworks default to the host zone.
      Cloud schedulers differ: some cron services run only in UTC, others
      accept a zone.
  - How it appears in code:
    - Double conversion: one layer converts to UTC, the next assumes local
      time and converts again, so the offset is applied twice.
    - No conversion: each layer assumes another converted, so values are
      off by the offset.
    - Original offsets lost in serialization, then needed later.
    - Behavior changing after a driver, ORM, or framework upgrade.
    - Tests run only in UTC, where every one of these bugs is invisible
      (PA-8).
  - What to check:
    - Every hop a time value crosses: client, API, serializer, ORM,
      driver, database, reports. Note each hop's conversion behavior and
      configuration.
    - Version-dependent defaults in drivers and frameworks.
  - Fix:
    - Map the stack's conversions and configure each one explicitly:
      session zone, driver settings, ORM settings, serializer features
      (BP-1).
    - Use types that carry offsets or zones end to end where the original
      offset matters (PA-9).
    - Write round-trip tests that run under a non-UTC host zone and cross
      DST dates, and pin them to the configured versions.
  - Not a finding:
    - Stacks with documented, explicitly configured conversion at each hop
      and round-trip tests in non-UTC zones.
  - Escalate (NEEDS-HUMAN): systems where the conversion behavior of a
    layer outside the review unit (vendor service, BI tool, partner API)
    cannot be established.
  - Proposed severity (for the user to decide): HIGH when double or
    missing conversion shifts stored or acted-on times on a core path.
    MEDIUM for reports, dashboards, and logs. LOW for test-only code.
- PA-91: Internal-use exemption assumption. Teams assume software used
  only internally or in one location does not need to handle time zones.
  - Overlap: almost every earlier item applies within one zone. PA-91
    covers the belief that a single-site or internal deployment is exempt,
    and why that belief fails.
  - Why it is false:
    - One zone still has DST: 23- and 25-hour days, a skipped hour, and a
      repeated hour every year (PA-1, PA-36, PA-54). Zone-less local
      timestamps from the repeated hour are ambiguous forever (PA-10).
    - The local zone's rules change by government decision (PA-9,
      PA-35).
    - "Internal" grows: new offices, remote staff, contractors,
      acquisitions, and outsourced teams in other zones.
    - The infrastructure is not local. Cloud hosts, managed databases, CI
      runners, and SaaS integrations (chat, calendars, payroll, HR)
      commonly run or exchange data in UTC (PA-8, PA-10, PA-90).
    - Data leaves: exports to partners, regulators, auditors, and
      insurers, log aggregation, and backups restored elsewhere.
    - Staff travel, and their devices change zone (PA-50).
    - Records outlive their context: audits, litigation, and migrations
      years later need unambiguous timestamps (PA-46 cites a regulation
      requiring UTC traceability).
    - Local-only time still has every non-zone pitfall: day, month, and
      year lengths, leap days, clock errors, and precision (PA-1 to PA-4,
      PA-11, PA-23).
  - How it appears in code:
    - Naive local datetimes throughout, with no offsets in storage or
      logs.
    - The business zone implied by the host rather than configured.
    - Scheduled jobs in host local time with no DST handling.
    - Comments or decisions such as "timezones don't matter here".
    - No tests across DST transitions.
  - What to check:
    - Storage and log formats: do timestamps carry offsets or UTC?
    - Where the business zone is defined.
    - Integrations, exports, and infrastructure zones.
    - DST behavior of scheduled jobs.
  - Fix:
    - Store instants in UTC or with offsets, and log with offsets, even
      for single-site systems (PA-10).
    - Configure the business zone explicitly as an IANA ID, not by host
      setting (PA-8).
    - Handle DST in schedules and test the transitions (PA-36, PA-54).
    - Treat this as cheap insurance: the cost of adding zone handling
      later grows with every zone-less record stored.
  - Not a finding:
    - Throwaway scripts that persist no times and drive no decisions.
  - Escalate (NEEDS-HUMAN): systems whose expected growth, integrations,
    or retention period are not stated, when the code stores zone-less
    times.
  - Proposed severity (for the user to decide): HIGH for payroll,
    scheduling, or audit records stored without offsets, or schedules that
    break at DST. MEDIUM for other zone-less storage and logs. LOW for
    test-only code.
- PA-92: Automatic-handling assumption. Teams assume the software stack
  handles time zones and DST correctly with no deliberate decisions or
  configuration.
  - Overlap: BP-1 says to prefer trusted libraries. PA-90 covers implicit
    conversions between layers. PA-92 covers what libraries cannot decide
    for the team, and the silent defaults they apply instead.
  - Why it is false:
    - Libraries apply silent defaults for impossible and ambiguous local
      times (verified for New York):
      - Python: 02:30 on 2026-03-08 (a skipped time) is accepted with
        offset -05:00. Converting to UTC and back gives 03:30-04:00, a
        different local time. In the repeated hour on 2026-11-01, 01:30
        takes -04:00 with `fold=0` and -05:00 with `fold=1`.
      - JS: `new Date(2026, 2, 8, 2, 30)` becomes 03:30 EDT.
        `new Date(2026, 10, 1, 1, 30)` picks the first occurrence (EDT).
      - Java `ZonedDateTime.of` shifts skipped times forward (PA-77).
      Each default is a policy decision made for the team.
    - Semantics are the team's to decide: elapsed versus calendar
      arithmetic (PA-1, PA-44), which zone governs a feature (PA-17),
      month-end and Feb 29 policies (PA-2, PA-3), date-only versus instant
      (PA-17), how future local events are stored (PA-9), and which day,
      week, weekend, and holiday definitions apply (PA-56 to PA-59).
    - Configuration is required: session zones, driver and ORM settings,
      serializer features (PA-10, PA-90).
    - Defaults are often wrong for production: host-zone defaults (PA-8),
      lenient parsing (PA-27), and locale-dependent formatting (PA-32).
    - Stacks offer both correct and incorrect types (naive and aware,
      local and zoned, `timestamp` and `timestamptz`). Choosing is the
      team's job.
    - Data must be maintained: tz data updates in every layer (PA-35).
    - Libraries can be misused (BP-1 misuse finding).
  - How it appears in code:
    - No explicit handling or documented policy for skipped and repeated
      local times.
    - Defaults relied on for parsing, formatting, zone, and arithmetic.
    - Comments or decisions such as "the framework handles timezones".
    - No tests at DST transitions or in non-UTC zones.
  - What to check:
    - Where each policy decision above is made, explicitly or by default.
    - Configuration of every layer (PA-90).
    - Tests across transitions.
  - Fix:
    - Keep using trusted libraries (BP-1), and record the team's
      decisions: storage model, governing zone per feature, arithmetic
      meaning, gap and overlap policy, month-end policy, and day and week
      definitions.
    - Configure every layer explicitly (PA-90).
    - Keep tz data current (PA-35).
    - Test transitions, non-UTC hosts, leap days, and month-ends.
  - Not a finding:
    - Library defaults that the team has reviewed, documented, and tested
      as the intended policy.
  - Escalate (NEEDS-HUMAN): features whose time semantics (elapsed or
    calendar, governing zone, gap policy) are not stated anywhere.
  - Proposed severity (for the user to decide): HIGH when an unexamined
    default changes stored or acted-on times on a core path. MEDIUM for
    missing documentation and tests. LOW for test-only code.
- PA-93: Self-maintained zone list assumption. Teams assume they can
  easily maintain their own list of time zones, offsets, or rules.
  - Overlap: PA-9 and PA-35 cover rule changes and update latency. PA-52
    covers renames and splits. PA-87 covers zone counts and Windows IDs.
    PA-93 covers hand-maintained zone tables in application code or data,
    and the volume and kinds of change they miss. Merged per the class ledgers.
  - Why it is false:
    - Change is frequent. The tzdata versions named in this host's Debian
      changelog give approximate releases per year: 2020: 6, 2021: 5,
      2022: 7, 2023: 4, 2024: 2, 2025: 3, and 2026 so far: 2 (counted from
      the changelog, approximate).
    - Each zone carries a full history of transitions, not one offset and
      one DST rule (PA-9, PA-19, PA-52).
    - The structure changes: zones split (`America/Ciudad_Juarez`, 2022),
      are renamed (`Europe/Kyiv`, 2022), and become links. In 2022, tzdata
      merged several zones whose data matched since 1970 into links,
      moving older history to an optional "backzone" file.
    - Builds differ. Whether historical backzone data is included depends
      on how the tz data was built. This host still returns Amsterdam's
      own 1930 offset (+00:19:32) (PA-51), so it includes that history.
      Other builds return a neighbor's.
    - Display names and translations come from CLDR, including "metazone"
      names such as "Pacific Time" in each language.
    - Mappings to other systems (Windows IDs, countries) change too
      (PA-67, PA-87).
  - How it appears in code:
    - Hardcoded arrays such as `{"(GMT-05:00) Eastern Time", -5}`.
    - Database tables of zones with a fixed offset and a DST flag.
    - Custom DST rule tables (PA-36).
    - Hand-maintained country-to-zone or Windows-to-IANA maps.
    - Lists missing new zones or keeping old offsets (Kazakhstan at +06:00
      after 2024) (PA-9).
  - What to check:
    - Any zone, offset, or rule data defined in the codebase or database.
    - How picker lists are produced and updated.
  - Fix:
    - Generate zone lists, offsets, rules, and display names from tzdata
      and CLDR through the platform or a library, at build or run time
      (BP-1).
    - Where a curated subset is needed for usability, store only IANA IDs
      in it and derive everything else at run time.
    - Add a check (for example in CI) that every listed ID loads and is
      canonical in the deployed tz data.
    - Track tz data releases (PA-35).
  - Not a finding:
    - Curated lists of IANA IDs whose offsets and names are computed by the
      library.
  - Escalate (NEEDS-HUMAN): products whose zone list is contractual or
    regulatory, where the update process is not stated.
  - Proposed severity (for the user to decide): HIGH when stale
    hand-maintained offsets or rules assign wrong times on a core path.
    MEDIUM for missing zones and display names. LOW for test-only code.
- PA-94: Single-frame assumption. Code assumes every measurement taken
  from one clock shares the same frame of reference, so readings from that
  clock are always directly comparable.
  - Overlap: PA-20 covers relativity between different clocks. PA-60
    covers ordering across systems. PA-94 covers one clock whose frame
    changes during a series of measurements, physically or by context.
    Merged per the class ledgers.
  - Why it is false:
    - Physical frames change for clocks that move. An aircraft clock runs
      at a different rate on the ground, climbing, and at cruise (PA-20).
      A satellite clock's rate varies around an elliptical orbit: GPS
      receivers apply an eccentricity correction (`F * e * sqrt(a) *
      sin(E)`) whose amplitude is about 23 ns at e = 0.01 and 46 ns at
      e = 0.02 for a GPS orbit (computed from the published constant
      F = -4.442807633e-10 s per root meter).
    - Synchronizing clocks on a rotating Earth needs a Sagnac correction,
      which depends on the signal path, not just the clocks.
    - Context frames change for any clock:
      - The device's zone changes, so displayed local times in one series
        use different offsets (PA-50).
      - The sync source or policy changes, for example smeared to
        unsmeared (PA-20), or a step correction happens (PA-11).
      - Monotonic clocks restart at reboot, so readings before and after
        are not comparable (PA-65).
      - A VM migrates to another host, changing the underlying counter
        (PA-21).
      - A GPS receiver switches time scale when it gets a fix or receives
        the leap-second count (PA-13, PA-46).
  - How it appears in code:
    - Time series from one device treated as one homogeneous sequence.
    - No per-sample record of zone, offset, sync state, boot ID, or time
      scale.
    - Durations or rates computed across a context change.
    - Onboard timestamps from moving platforms used without correction
      (PA-20).
  - What to check:
    - What context is recorded with each timestamp.
    - Whether series are split at context changes.
    - Relativistic handling in space, navigation, and precision-timing
      code.
  - Fix:
    - Record each sample's context: zone or offset, sync source and state,
      boot or session ID for monotonic readings, and time scale.
    - Split series at context changes, or convert every sample to one
      reference (UTC instants, or a named scale such as TAI) before
      comparing.
    - In space and navigation code, apply relativistic corrections from
      validated libraries and published interface specifications, not
      hand-written approximations (PA-20, PA-79).
  - Not a finding:
    - Ground-based business software where relativistic effects are
      negligible, provided context changes (zone, sync, reboot) are
      handled.
  - Escalate (NEEDS-HUMAN): telemetry, navigation, or measurement systems
    where the reference frame and required accuracy are not stated.
  - Proposed severity (for the user to decide): HIGH when navigation,
    telemetry, or measurement results on a core path mix frames. MEDIUM
    for device time series without context. LOW for test-only code.
- PA-95: Works-today assumption. Teams assume that if date-based code
  works now, it works on every date.
  - Overlap: nearly every earlier item names a date that breaks code.
    PA-25 covers clock injection. PA-95 covers testing: code verified only
    on the dates it happened to run, and tests that themselves depend on
    today's date.
  - Why it is false:
    - Many defects surface only on particular dates:
      - DST transitions, in each hemisphere and zone (PA-1, PA-36, PA-37).
      - Leap days and day 366 (PA-3, PA-4).
      - Month-ends on the 29th to 31st (PA-2).
      - Year-ends, ISO week 53, and week-year boundaries (PA-7).
      - Range limits: 2036-02-07 (NTP), 2038-01-19 (32-bit Unix time),
        and 9999-12-31 (PA-18).
      - GPS week rollovers: 1999-08-22, 2019-04-07, and next 2038-11-21
        (computed as multiples of 1,024 weeks from 1980-01-06) (PA-12).
      - Zone rule changes and era changes (PA-9, PA-41).
      - Sliding two-digit-year windows moving (PA-83).
    - Real incidents: the Microsoft Zune freeze on 2008-12-31 and the
      Azure outage on 2012-02-29 (PA-3), fuel-payment failures in New
      Zealand on 2024-02-29 (PA-4), and Microsoft Exchange's malware
      scanning failing on 2022-01-01. Exchange stored dates as a signed
      32-bit `yymmddHHMM` number, and 2201010001 exceeds 2,147,483,647
      (verified arithmetic).
    - Tests can depend on the date they run:
      - Assertions like "expires in 30 days" or "age is 30" that pass only
        on some days.
      - Tests that fail at midnight, at month-end, or in the last week of
        the year (PA-53).
      - Tests that pass only under the CI host's zone (PA-8).
  - How it appears in code:
    - Business logic reading the real clock with no injection (PA-25).
    - Date-dependent logic with tests only for "today".
    - No parametrized or property-based tests over date ranges.
    - Packed or narrow date encodings (such as `yymmddHHMM` in 32 bits)
      that fit today and overflow later.
  - What to check:
    - Whether time can be controlled in tests.
    - The dates tests actually cover.
    - Encodings and types that will overflow at a future date.
  - Fix:
    - Inject a clock (PA-25) and test a fixed matrix of dates: DST start
      and end in several zones (including southern-hemisphere and
      non-hour zones), Feb 28, Feb 29, and Mar 1 in leap and common years,
      the 29th to 31st, Dec 31 and Jan 1, an ISO week-53 year, 1970,
      2036-02-07, 2038-01-19, and the domain's extremes.
    - Add property-based tests over wide date ranges where the language
      has a supported tool (adding one needs user approval under the
      dependency rules).
    - Run the suite under several host zones and with the clock set
      forward, for example in a scheduled CI job.
    - Check the overflow date of every encoding before shipping it.
  - Not a finding:
    - Date-dependent logic covered by an explicit boundary-date test
      matrix with an injected clock.
  - Escalate (NEEDS-HUMAN): long-lived systems or devices whose required
    service life is not stated, when the code has date-range limits.
  - Proposed severity (for the user to decide): HIGH when core-path date
    logic has no boundary-date tests, or an encoding overflows within the
    product's service life. MEDIUM for date-dependent tests that are
    flaky. LOW for test-only code.
- PA-96: Unique-moment assumption. Code assumes a given date, time, or
  date-time identifies exactly one moment.
  - Overlap: PA-1 covers repeated and skipped hours. PA-17 covers
    date-only values across zones. PA-29 covers precision. PA-30 covers
    uniqueness of timestamps as IDs. PA-96 states what is needed to
    identify a moment, and the type distinctions that follow. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b where marked):
    - A date without a zone is a range. 2026-07-01 begins at
      2026-06-30T10:00Z in Kiritimati (+14:00) and ends at
      2026-07-02T11:00Z in Pago Pago (-11:00): 49 hours of instants
      (verified). Counting the uninhabited -12:00 zone (`Etc/GMT+12`), 50
      hours.
    - A local date-time without a zone is also a range. 09:00 on
      2026-07-01 spans 25 hours of instants across inhabited zones
      (verified).
    - With a zone, a local time can still be ambiguous (the repeated hour)
      or nonexistent (the skipped hour) (PA-1, PA-92).
    - With a zone, a future local time is not fixed until it happens,
      because rules can change (PA-9).
    - An offset fixes the instant but not the zone, so later local
      calculations are wrong (PA-9, PA-89).
    - A time of day alone (`09:00`) identifies no moment until a date and
      zone are added.
    - Abbreviations are ambiguous (PA-67), calendars differ (PA-41), and
      some local dates repeat (PA-40).
    - The time scale matters: UTC, TAI, and GPS time label the same
      instant differently (PA-13, PA-46).
    - Every value has a precision. A second-precision value names a
      one-second interval, not a point (PA-29).
  - What identifies a moment: date, time, precision, a zone or offset
    (resolved by the rules in force at that time), the calendar, and the
    time scale.
  - How it appears in code:
    - Local date-times stored or compared as if they were instants.
    - Date strings used as keys for moments.
    - APIs accepting date-times without an offset for values that are
      instants.
    - Dates converted to a single instant (often midnight UTC) instead of
      a range in a specific zone (PA-17).
    - One type used for instants, local date-times, dates, and times.
  - What to check:
    - The type of each temporal value and whether it matches its meaning.
    - Conversions from dates and local date-times to instants.
    - API contracts for offsets.
  - Fix:
    - Use distinct types for distinct meanings (BP-1): instant, zoned or
      offset date-time, local date-time, local date, and local time. For
      example Java `java.time` (`Instant`, `ZonedDateTime`,
      `OffsetDateTime`, `LocalDateTime`, `LocalDate`, `LocalTime`), or
      Luxon `DateTime` with an explicit zone plus plain ISO date strings
      for date-only values.
    - Require an offset (or `Z`) in APIs for instants (PA-27).
    - Convert dates to half-open instant ranges in a stated zone
      (`[start of day, start of next day)`).
    - Apply a stated policy for ambiguous and skipped local times (PA-92).
  - Not a finding:
    - Local dates and times used deliberately as local values (birthdays,
      store opening hours) with their zone held elsewhere.
  - Escalate (NEEDS-HUMAN): values whose meaning (instant, local wall
    time, or date) is not stated in the requirement or schema.
  - Proposed severity (for the user to decide): HIGH when local values are
    treated as instants for deadlines, billing, or scheduling on a core
    path. MEDIUM for keys and reports. LOW for test-only code.
- PA-97: Zone-from-address assumption. Code assumes a time zone can be
  determined from a country, state, province, city, town, or postal code.
  - Overlap: PA-49 covers zones derived from longitude and nested zones.
    PA-67 covers British territories. PA-89 covers zones inferred from
    clocks. PA-97 covers deriving zones from administrative locations and
    addresses. Merged per the class ledgers.
  - Why it is false (tzdata `zone1970.tab` on this host, verified):
    - Countries: many have several zones. Counts of tz zones per country
      code: US 29, Russia 27, Canada 23, Brazil 16, Australia 13, Mexico
      12, Argentina 12, Kazakhstan 7, Indonesia 4, Greenland 4, Chile 4.
      Zones with identical offsets today still count separately because
      their histories differ (Kazakhstan now uses one offset, PA-9).
    - Countries with overseas or island regions span distant zones:
      France, the UK (PA-67), Denmark (Greenland, Faroe), Spain (Canary
      Islands), Portugal (Azores, Madeira), Chile (Easter Island), and
      Ecuador (Galapagos).
    - States and provinces split. Indiana alone has 8 tz zones because
      its counties changed rules at different times (verified). Other
      US states split between zones include Kentucky, Tennessee, Florida,
      Texas, Oregon, Idaho, Nebraska, Kansas, the Dakotas, and Michigan.
      In Canada, Ontario, British Columbia, Nunavut, and Saskatchewan
      split. In Australia, Broken Hill in New South Wales follows South
      Australian time (`Australia/Broken_Hill`, verified).
    - Towns differ from their province:
      - Creston, BC follows `America/Phoenix` (no DST) (verified).
      - Fort Nelson, BC has its own zone, `America/Fort_Nelson` (verified).
      - Atikokan, Ontario follows Eastern Standard Time all year, listed
        under `America/Panama` (verified).
      - Lloydminster straddles Alberta and Saskatchewan and uses one zone.
      - Ciudad Juarez left the rest of Chihuahua in 2022
        (`America/Ciudad_Juarez`, verified).
    - Cities: names repeat across states and countries (Springfield,
      Paris), and some communities keep unofficial local time (PA-35).
    - Postal codes are delivery routes, not areas. A US ZIP code can cross
      county, state, and zone lines. PO boxes sit in a different place
      from the residence. Military APO/FPO codes do not indicate a
      location. Codes are added and changed.
    - The person may not keep the zone of their address (travel, remote
      work, preference) (PA-17, PA-89).
  - How it appears in code:
    - Country-to-zone or state-to-zone lookup tables with one zone per
      entry.
    - ZIP-code-to-zone tables.
    - Zone derived from a billing or mailing address and used for
      deadlines.
  - What to check:
    - Any lookup from administrative or postal location to zone.
    - Which location the requirement says governs each deadline.
  - Fix:
    - Use the user's or site's stored IANA zone ID, confirmed by the user
      (PA-17).
    - When a zone must be derived from a location, use coordinates with a
      maintained boundary dataset (PA-49), and treat the result as a
      default to confirm, not a fact.
    - Expect several zones per country and per state. Use tzdata's
      `zone1970.tab` for country lists, never as one-to-one mappings.
  - Not a finding:
    - Defaults derived from location that the user confirms or can
      change.
  - Escalate (NEEDS-HUMAN): deadlines or legal time limits tied to an
    address where the governing zone rule is not stated.
  - Proposed severity (for the user to decide): HIGH when address-derived
    zones drive deadlines, delivery windows, or billing on a core path.
    MEDIUM for display defaults. LOW for test-only code.
- PA-98: Zone-from-network assumption. Code assumes a time zone can be
  determined from a client's IP address or internet service provider.
  - Overlap: PA-17 notes that VPNs change apparent location. PA-89 and
    PA-97 cover zones inferred from clocks and addresses. PA-98 covers IP
    and ISP inference. Merged per the class ledgers.
  - Why it is false:
    - IP geolocation is an estimate. Databases are usually more accurate
      at country level than city level, and they go stale as addresses
      are reassigned. Commercial databases publish an accuracy radius per
      result for this reason.
    - Traffic often exits far from the user:
      - VPNs, proxies, and Tor.
      - Corporate networks that route traffic through a head office or a
        cloud security gateway.
      - Mobile carriers that share addresses behind carrier-grade NAT at
        regional gateways.
      - Satellite internet, whose exit point may be in another region or
        country.
      - In-flight and shipboard internet (PA-50).
      - Privacy relays that substitute a different address in the same
        general region.
      - Requests from cloud and data-center addresses (servers, bots,
        automated clients).
    - An ISP name says nothing about zone: providers span zones and
      countries.
    - Even a correct location gives only a default: the person may keep
      another zone (PA-17), and the location-to-zone step has its own
      errors (PA-97).
    - IP-derived location is personal data in many jurisdictions. Its
      lawful use is outside this audit's scope (see the data-privacy
      auditor, abuzucom/havel).
  - How it appears in code:
    - GeoIP lookup results used as the user's zone for deadlines,
      notifications, or billing.
    - Server-side rendering in a zone derived from the request IP.
    - IP-derived zones cached on the profile and never revisited.
    - ISP or network names mapped to zones.
  - What to check:
    - Any use of IP or ISP lookups to set a zone.
    - Whether the result is a default or authoritative, and whether the
      user can change it.
  - Fix:
    - Use the device's IANA zone and the user's confirmed setting as the
      authority (PA-17, PA-89).
    - Use IP-derived zones only as a fallback default, with the
      database's accuracy information, and never for legal or financial
      deadlines.
    - Let the user override, and re-check when the device zone changes.
  - Not a finding:
    - IP-derived zones used only as a pre-filled default that the user
      confirms.
  - Escalate (NEEDS-HUMAN): features that rely on IP location for time
    decisions where the accepted accuracy is not stated.
  - Proposed severity (for the user to decide): HIGH when IP-derived zones
    drive deadlines, billing, or notifications on a core path. MEDIUM for
    display defaults. LOW for test-only code.
- PA-99: Zone-from-phone-number assumption. Code assumes a time zone can
  be determined from a phone number, area code, or country calling code.
  - Overlap: PA-97 and PA-98 cover zones inferred from addresses and IP
    addresses. PA-99 covers telephone numbering. Merged per the class ledgers.
  - Why it is false:
    - Country calling codes span many zones (offsets for January 2026,
      verified with tzdata 2026b):
      - +1 (North American Numbering Plan) covers the US, Canada, and many
        Caribbean and Pacific territories: American Samoa (-11:00), Hawaii
        (-10:00), Puerto Rico (-04:00), and Guam and the Northern Mariana
        Islands (+10:00).
      - +7 covers Russia and Kazakhstan, from Kaliningrad (+02:00) to
        Kamchatka (+12:00), with Almaty at +05:00.
      - +61 covers mainland Australia and its external territories:
        Sydney (+11:00 in January), Christmas Island (+07:00), and the
        Cocos Islands (+06:30).
      - Several territories share codes across regions (for example +262
        for Reunion and Mayotte).
    - Area codes span zones. In the US, area code 850 covers both Eastern
      (Tallahassee) and Central (Pensacola) time, and 308 in Nebraska
      covers Central and Mountain time.
    - Numbers move with people. Mobile numbers are kept after moving and
      while roaming abroad.
    - Some numbers have no location: toll-free numbers, VoIP and virtual
      numbers that can carry any area code, and global satellite and
      network codes (for example +881 and +882).
    - Number-metadata libraries reflect this: libphonenumber's time-zone
      mapper returns a list of possible zones for a number, which can
      contain several or none.
    - Legal stakes: US telemarketing rules (TCPA, 47 CFR 64.1200) bar
      solicitation calls before 8:00 or after 21:00 at the called party's
      location, and some states set narrower windows. An area-code guess
      can put calls outside those hours.
  - How it appears in code:
    - Area-code or country-code lookup tables returning one zone.
    - Call or SMS quiet hours computed from the number's area code.
    - Notification scheduling keyed on phone prefixes.
  - What to check:
    - Any derivation of zone from phone numbers.
    - Contact-time compliance logic and its zone source.
  - Fix:
    - Use the user's confirmed IANA zone where available (PA-17).
    - Where only a number is known, treat every zone the number could be
      in as possible. For contact-time windows, send only when the time is
      allowed in all of them.
    - Use maintained numbering metadata through a library rather than
      hand-made tables. Adding one needs user approval under the
      dependency rules.
  - Not a finding:
    - Phone-derived zones used as pre-filled defaults the user confirms.
  - Escalate (NEEDS-HUMAN): contact-time compliance (calls, SMS) where the
    location source and the applicable rules are not stated.
  - Proposed severity (for the user to decide): HIGH when phone-derived
    zones decide regulated contact times, deadlines, or billing. MEDIUM
    for display defaults and reminders. LOW for test-only code.
- PA-100: One-zone-per-US-state assumption. Code assumes everyone in the
  same US state is in the same time zone.
  - Overlap: PA-97 lists split states in general, Indiana's 8 zones, and
    PA-49 covers Arizona's nested Navajo and Hopi zones. PA-100 gives the
    US detail, and zone changes at county level over time. Merged per the class ledgers.
  - Why it is false (tzdata `zone1970.tab` entries for US, verified):
    - Indiana: 6 Eastern-time zones (Indianapolis, Vincennes, Winamac,
      Marengo, Petersburg, Vevay) and 2 Central-time zones (Tell City,
      Knox), separated by county histories.
    - Kentucky: Eastern zones for the Louisville area and for Wayne
      County (`America/Kentucky/Monticello`), with the western part on
      Central time.
    - Michigan: Eastern (`America/Detroit`), with counties on the
      Wisconsin border on Central (`America/Menominee`).
    - North Dakota: three Central zones for specific counties (Oliver,
      rural Morton, Mercer), with the southwest on Mountain time.
    - Idaho and Oregon: southern Idaho and eastern Oregon on Mountain
      (`America/Boise`), the rest on Pacific.
    - Alaska: seven zones (Anchorage, Juneau, Sitka, Metlakatla, Yakutat,
      Nome, Adak). The western Aleutians (`America/Adak`) are an hour
      behind the rest of the state.
    - Arizona: most areas without DST, the Navajo Nation with DST, and
      the Hopi Reservation inside it without DST (PA-49).
    - Other split states: Florida (the western panhandle on Central),
      Tennessee (East on Eastern, the rest on Central), Texas (El Paso on
      Mountain), Kansas, Nebraska, and South Dakota (western parts on
      Mountain).
    - County assignments change. Indiana counties changed in 2006 and
      2007, and North Dakota counties moved from Mountain to Central in
      2003 and 2010, so a county's zone depends on the date (PA-9).
  - How it appears in code:
    - State-to-zone lookup tables, such as `{"IN": "America/Indiana/
      Indianapolis"}` or `{"FL": "America/New_York"}`.
    - Contact windows, delivery cut-offs, or deadlines computed from the
      state in an address (PA-97, PA-99).
    - Historical records assigned zones with today's county rules.
  - What to check:
    - Any state-to-zone mapping.
    - How historical records get their zone.
  - Fix:
    - Store and use an IANA zone per user or site, confirmed by the user
      (PA-17, PA-97).
    - Where location must decide, use coordinates with a maintained
      boundary dataset, at the date in question (PA-49).
    - For compliance windows with only a state known, treat all of the
      state's zones as possible (PA-99).
  - Not a finding:
    - State-derived defaults that the user confirms.
  - Escalate (NEEDS-HUMAN): deadlines or legal windows tied to a US state
    where the governing zone rule is not stated.
  - Proposed severity (for the user to decide): HIGH when state-derived
    zones drive deadlines, contact windows, or billing on a core path.
    MEDIUM for display defaults. LOW for test-only code.
- PA-101: Proximity assumption. Code assumes people or places within some
  distance of each other (10, 100, or 500 miles, for example) share a time
  zone, or at least the same local date.
  - Overlap: PA-49 covers neighbors far apart in offset. PA-97 and PA-100
    cover split regions. PA-101 covers distance-based logic: radius
    searches, geofences, and "nearby" features.
  - Why it is false (offsets and local times verified with tzdata 2026b):
    - Samoa (Apia) and American Samoa (Pago Pago) are about 78 miles
      apart (great-circle distance computed from approximate city
      coordinates) and 24 hours apart. At 12:00 UTC on 2026-01-15 it is
      01:00 on January 16 in Apia and 01:00 on January 15 in Pago Pago:
      the same clock time on different dates, every day.
    - The Diomede Islands in the Bering Strait are about 2.4 miles apart
      (commonly cited distance). Little Diomede follows Alaska time
      (`America/Nome`, -09:00 in winter) and Big Diomede follows Chukotka
      (`Asia/Anadyr`, +12:00): at 12:00 UTC on 2026-01-15 that is 03:00
      on January 15 versus 00:00 on January 16, 21 hours apart.
    - Across ordinary one-hour boundaries, nearby places are on different
      dates for one hour every day (for example 00:30 on one side, 23:30
      the previous day on the other).
    - Large differences across short borders: China (+08:00) and
      Afghanistan (+04:30), 3.5 hours (PA-49).
    - Places in the same zone can differ in DST observance (Arizona and
      the Navajo Nation) (PA-49).
    - Communities near boundaries sometimes keep a neighbor's time
      unofficially. Phenix City, Alabama, for example, commonly keeps
      Eastern time with Columbus, Georgia, though Alabama is on Central.
  - How it appears in code:
    - Radius searches ("open now near you", "events today within 50
      miles") evaluated in the searcher's zone instead of each place's
      zone.
    - Same-day delivery or pickup cutoffs applied to a whole service
      radius with one zone.
    - Geofenced notifications timed in one zone for everyone in the fence.
    - Grouping by distance for scheduling, assuming one zone per cluster.
  - What to check:
    - Any feature combining location radius with times, dates, or opening
      hours.
    - Whether each place carries its own zone.
  - Fix:
    - Store an IANA zone with each place, venue, or user (PA-97).
    - Evaluate "open now", "today", and cutoffs in each place's own zone.
    - Show the place's local time, and the viewer's where they differ.
  - Not a finding:
    - Radius features whose service area is documented as a single zone
      and validated as such.
  - Escalate (NEEDS-HUMAN): service areas that cross zone boundaries or
    the date line where the rule for "today" is not stated.
  - Proposed severity (for the user to decide): HIGH when nearby places'
    hours, cutoffs, or bookings are evaluated in the wrong zone on a core
    path. MEDIUM for display and search results. LOW for test-only code.
- PA-102: Uniform hour assumption. Code assumes every hour has the same
  length in every time system.
  - Overlap: PA-1 covers 23- and 25-hour days. PA-20 and PA-21 cover clock
    rates. PA-64 covers 61-second minutes. PA-102 covers time systems whose
    hours are defined differently, and local-hour buckets. Merged per the class ledgers.
  - Why it is false:
    - Seasonal (unequal) hours: some systems divide daylight into 12 hours
      and night into 12, so an hour's length changes with season and
      latitude. Jewish religious law uses such proportional hours
      ("sha'ot zmaniyot") for prayer times. Traditional Japanese timekeeping
      in the Edo period and ancient Roman hours worked the same way.
    - Sun-position times: Islamic prayer times are set by the sun's
      position, so the gaps between them change daily and by place.
    - Leap seconds: a UTC hour containing one lasts 3601 seconds (PA-64).
    - Smearing: smeared hours contain slightly longer seconds (PA-20).
    - Local hours at DST changes: the local hour 01:00 to 02:00 happens
      twice on a fall-back day (two real hours), and 02:00 to 03:00 does
      not happen on a spring-forward day (PA-1).
    - Astronomical and planetary time (computed from standard constants):
      - A sidereal hour (1/24 of a sidereal day of 86,164.09 s) lasts about
        59.84 minutes.
      - A Mars hour (1/24 of a sol of 88,775.24 s), as used in Mars mission
        local time, lasts about 61.65 minutes.
    - Decimal and alternative systems: French Revolutionary decimal hours
      lasted 144 minutes (10 per day). Swatch Internet Time divides the day
      into 1,000 "beats" of 86.4 seconds.
    - Earth-rotation time (UT1) differs from atomic time as the length of
      the day varies by milliseconds (PA-46).
  - How it appears in code:
    - Religious-time features (prayer times, Sabbath and holiday start
      times) computed with fixed 60-minute hours or fixed offsets from
      sunrise.
    - Astronomy or space software mixing sidereal, solar, and planetary
      hours.
    - Hourly billing or metrics bucketed by local hour on DST days, so one
      bucket holds two hours of usage and another holds none.
    - Conversions between decimal or alternative time units and SI units
      with wrong constants.
  - What to check:
    - Which time system each hour-based calculation uses.
    - Hourly buckets in local time around DST changes.
  - Fix:
    - Name the time system for every hour-based calculation.
    - Use dedicated, maintained libraries for religious times, astronomy,
      and planetary time (for example Astropy for astronomy, and NASA's
      published Mars24 algorithm for Mars time). Adding a library needs
      user approval under the dependency rules (BP-1).
    - Bucket billing and metrics by UTC hour, or by instant ranges, and
      label local hours explicitly on DST days (PA-88).
  - Not a finding:
    - SI-based hourly calculations on UTC instants.
  - Escalate (NEEDS-HUMAN): religious, astronomical, or space features
    whose time system and accuracy are not stated.
  - Proposed severity (for the user to decide): HIGH when religious
    observance times, astronomical or mission timing, or hourly billing on
    a core path use the wrong hour definition. MEDIUM for display and
    metrics. LOW for test-only code.
- PA-103: Logical client time assumption. Code assumes clients' time
  always behaves plausibly. The user's intent (clarified): software must
  handle clients whose problems make their time handling look illogical,
  as if they were on a spacecraft orbiting a black hole. The black hole is
  the metaphor. The requirement is robustness to impossible-looking client
  time.
  - Overlap: PA-11 to PA-16 cover wrong, jumping, and skewed client
    clocks. PA-20 covers relativity for GPS, aircraft, and spacecraft.
    PA-21 and PA-22 cover stopped, throttled, and suspended clocks.
    PA-60 and PA-65 cover ordering and monotonicity. PA-103 states the
    general design rule that ties them together: the server must stay
    correct whatever a client's time does. Merged per the class ledgers.
  - What illogical client time looks like:
    - Frozen: the client's clock or process stops while the server's time
      moves on (suspension, freezing, throttling, long offline periods).
    - Racing or crawling: the client's elapsed time runs much faster or
      slower than the server's (speed hacks, simulations, broken
      hardware, extreme slewing) (PA-21).
    - Backward: client timestamps decrease between requests (PA-11,
      PA-68).
    - Impossible order: events stamped before the actions that caused
      them, replies stamped before requests, or "sent" after "received"
      (PA-14, PA-60).
    - Out of range: timestamps decades in the past or future, or at 1970
      (PA-12, PA-15, PA-18).
    - Flipping context: the client's zone or offset changes between
      consecutive requests (PA-50, PA-89).
    - Contradictory: the same request retried with different client
      times, or different client clocks for the same account on several
      devices.
  - Why it is false:
    - Physics allows it. Near a non-rotating black hole, a stationary
      clock runs at `sqrt(1 - rs/r)` of a distant clock's rate: about 0.95
      at ten times the Schwarzschild radius, 0.71 at twice it, 0.30 at
      1.1 times it, and 0.10 at 1.01 times it (computed). The extreme case
      is fiction for now. Milder versions are routine for satellites and
      spacecraft (PA-20).
    - Distance adds extreme latency. One-way light time between Earth and
      Mars ranges from about 3.0 to 22.3 minutes (computed from minimum and
      maximum distances of about 54.6 and 401 million km). Deep-space
      links use delay-tolerant networking (Bundle Protocol, RFC 9171)
      instead of request-response timeouts.
    - Everyday systems produce the same effect without relativity: a
      client whose process is suspended, frozen, throttled, or offline for
      weeks experiences almost no time while the server experiences a lot
      (PA-21, PA-22). A sped-up client (simulation, speed hack) experiences
      more (PA-21).
  - How it appears in code:
    - Protocols assuming a peer answers within a bounded time, or that its
      elapsed time matches the server's.
    - Sessions, leases, and tokens whose validity the client judges by its
      own elapsed time.
    - Clients resuming after a long freeze and acting on stale state:
      expired tokens, superseded data, past deadlines.
    - Sync protocols that assume clients were offline only briefly.
  - What to check:
    - Timeouts, leases, and expiry: who decides, and with which clock.
    - Resume and reconnect paths after long gaps.
    - Conflict handling for long-offline clients.
  - Fix:
    - Decide expiry, leases, and deadlines on the server's clock
      (PA-14).
    - On reconnect, revalidate tokens, versions, and deadlines before
      acting (PA-22).
    - Use version vectors or logical clocks to merge state from long-absent
      peers (PA-60).
    - Make operations idempotent and resumable, and design for unbounded
      latency where the domain needs it (delay-tolerant protocols for
      space links).
    - In space domains, apply relativistic corrections with validated
      libraries (PA-20, PA-94).
    - Treat every client time as untrusted input: validate plausibility,
      record it beside the server's receive time, and never let it alone
      decide authorization, ordering, expiry, or billing (PA-11, PA-15,
      PA-31).
    - Detect illogical client time (backward steps, impossible order,
      out-of-range values, sudden rate changes) and handle it by a stated
      policy: accept and flag, correct from server time, or reject with an
      actionable message. Never crash or corrupt data.
    - Test with simulated clients whose clocks freeze, race, crawl, jump
      backward, jump years, and change zone mid-session.
  - Not a finding:
    - Server-authoritative designs that validate client times and
      revalidate on reconnect, even without any space-specific handling.
  - Escalate (NEEDS-HUMAN): products where the policy for illogical client
    time (accept, correct, or reject) is not stated.
  - Proposed severity (for the user to decide): CRITICAL when illogical
    client time can grant authorization, bypass expiry, or change payment
    (PA-11). HIGH when it can corrupt stored data, ordering, or deadlines
    on a core path, or crash a service. MEDIUM for sync conflicts and
    analytics. LOW for test-only code.
- PA-104: Predictable leap second assumption. Code assumes the dates of
  future leap seconds can be calculated.
  - Overlap: PA-13 covers time-scale offsets and leap-second tables.
    PA-20 covers smearing. PA-46 covers Unix time and leap seconds. PA-64
    covers 61- and 59-second minutes. PA-104 covers how leap seconds are
    decided and published, and table expiry. Merged per the class ledgers.
  - Why it is false:
    - Leap seconds follow observed Earth rotation, which varies
      irregularly (tides, the core, the atmosphere, ice and ground
      movement, earthquakes). The IERS decides each one from measurements
      and announces it in Bulletin C, about six months ahead. No formula
      predicts them.
    - Placement rules allow several dates. The end of June or December is
      preferred, March or September is the second choice, and any month
      end is permitted.
    - The sign is not fixed. All 27 so far were positive. Earth's rotation
      has sped up, and a negative leap second has been discussed (PA-64).
    - The last was inserted at the end of 2016. The tzdata
      `leap-seconds.list` on this host ends with TAI-UTC of 37 seconds
      from 2017-01-01 (verified).
    - The future is undecided in detail. The CGPM resolved in 2022 to
      raise the tolerance between UT1 and UTC no later than 2035, which
      effectively ends leap seconds. The replacement scheme is still being
      worked out.
    - Leap-second lists expire. The `leap-seconds.list` on this host
      states "File expires on 28 December 2026" (verified). Software
      using an expired list cannot know whether a leap second was
      announced since.
    - GPS satellites broadcast upcoming leap seconds in their navigation
      message. Receivers that mishandle the announcement have failed at
      the event.
  - How it appears in code:
    - Hardcoded leap-second tables with no update or expiry check.
    - Formulas or schedules predicting leap seconds.
    - Code assuming leap seconds are always positive, always at June or
      December, or will never happen again.
    - TAI, GPS, or UTC conversions using a stale table (PA-13).
  - What to check:
    - The source of leap-second data and its expiry handling.
    - Assumptions about sign, month, and frequency.
  - Fix:
    - Read leap seconds from a maintained source (IERS Bulletin C via the
      OS, tzdata `leap-seconds.list`, or a time library), and check its
      expiry date. Alert when it expires (PA-35).
    - Handle positive and negative leap seconds, at any month end.
    - Treat future leap seconds as unknown. Use a consistent smear or step
      policy across the fleet (PA-20).
  - Not a finding:
    - Systems that use only smeared or POSIX time and document that they
      ignore leap seconds (PA-46).
  - Escalate (NEEDS-HUMAN): scientific, navigation, or regulated timing
    systems whose leap-second source and policy are not stated.
  - Proposed severity (for the user to decide): HIGH when navigation,
    regulated timestamping, or time-scale conversion on a core path uses
    predicted or stale leap-second data. MEDIUM for monitoring and logs.
    LOW for test-only code.
- PA-105: Type-equals-clock precision assumption. Code assumes the
  precision of the type a current-time function returns matches the
  precision of the clock behind it.
  - Overlap: PA-23 and PA-24 cover units and coarse clocks. PA-30 notes
    that precision is not resolution. PA-105 separates four properties
    (type precision, clock resolution, reported resolution, and accuracy)
    and shows each can differ. Merged per the class ledgers.
  - Why it is false (measured on this host, results are host-dependent):
    - The type can be coarser than the clock. Python reports the
      `time.time()` clock resolution as 1e-09 seconds, but it returns a
      float64, whose spacing near today's epoch value is about 2.4e-07
      seconds. Nanoseconds cannot be represented (verified).
      `time.time_ns()` returns an integer and keeps them.
    - The type can be finer than the clock. A type with nanosecond fields
      may be filled from a clock that ticks in microseconds, milliseconds,
      or 15.6 ms steps (Windows default timer), so the trailing digits are
      zeros or repeat (PA-24). On this host Java `Instant.now()` filled
      sub-microsecond digits in 997 of 1,000 readings, but the same code
      on other platforms or JDK versions returns microsecond or millisecond
      values.
    - Reads within one clock tick return the same value. 100,000 calls to
      JS `Date.now()` here returned only 23 distinct values (millisecond
      resolution), while 100,000 calls to Python `time.time()` returned
      99,993 (verified).
    - Reported resolution is a claim, not a guarantee.
      `clock_getres` and `time.get_clock_info` describe the clock, but
      virtualization and scheduling affect the effective granularity.
    - Accuracy is separate again: a nanosecond reading can be seconds wrong
      (PA-11 to PA-13).
    - Databases do the same: MySQL `NOW()` returns whole seconds unless
      called as `NOW(6)`, and Postgres timestamps hold microseconds whatever
      the clock delivers.
  - How it appears in code:
    - Treating nanosecond fields as nanosecond-accurate.
    - Storing current time as float seconds and expecting sub-microsecond
      detail.
    - Uniqueness or ordering relying on precise-looking values (PA-30).
    - Measuring events shorter than the clock's resolution, getting zero
      (PA-24).
  - What to check:
    - The return type of each current-time call and the clock behind it.
    - Float storage of timestamps (PA-23).
    - Claims of precision in logs, audits, or SLAs.
  - Fix:
    - Use integer nanosecond APIs where precision matters (Python
      `time.time_ns()`, `time.perf_counter_ns()`, Java `System.nanoTime()`
      for elapsed time) (BP-1).
    - Measure the effective resolution on the target platform and record
      it with the data.
    - Document precision, resolution, and accuracy separately for
      regulated timestamps (PA-46).
    - Never depend on trailing digits for uniqueness or order (PA-30).
  - Not a finding:
    - Values whose documented precision matches the measured clock and the
      storage type.
  - Escalate (NEEDS-HUMAN): audit or trading timestamps whose required
    precision and accuracy are not stated.
  - Proposed severity (for the user to decide): HIGH when precision
    assumptions break uniqueness, ordering, or regulated timestamps on a
    core path. MEDIUM for metrics. LOW for test-only code.
- PA-106: Distinct consecutive reads assumption. Code assumes two calls
  in a row to a current-time function always return different values.
  - Overlap: PA-53 covers the opposite mistake (assuming two reads are
    equal). PA-30 covers timestamps as unique IDs. PA-105 covers clock
    resolution. PA-106 covers logic that depends on time having visibly
    advanced, including change detection based on modification times.
    Merged per the class ledgers.
  - Why it is false:
    - Reads within one clock tick are equal. 100,000 calls to JS
      `Date.now()` on this host returned only 23 distinct values (PA-105,
      verified).
    - Clocks can stand still or go backward: steps, VM restores, leap
      seconds, and frozen test clocks (PA-11, PA-25, PA-65).
    - Database time is fixed within a transaction. Postgres `now()`
      returns the same value for the whole transaction (PA-30).
    - Change markers have coarse resolution:
      - HTTP `Last-Modified` and `If-Modified-Since` use HTTP dates, which
        carry whole seconds (Python `formatdate` output such as `Sat, 03
        Oct 2026 23:55:58 GMT`, verified). Two edits within one second look
        unchanged.
      - File modification times depend on the file system: FAT records 2-
        second steps, ext3 and HFS+ whole seconds, and ext4 and NTFS finer
        steps. Tools such as `make` and `rsync` that compare modification
        times can miss rapid changes.
  - How it appears in code:
    - IDs, file names, or cache-busting parameters from consecutive reads
      (PA-30).
    - Loops that wait until "now" changes, or progress checks requiring
      it to advance.
    - Assertions that elapsed time is greater than zero, or division by
      elapsed time (PA-22).
    - `updated_at = now()` used to signal a change, then compared to
      detect it.
    - Caching and sync based on `Last-Modified` or file modification
      times alone.
  - What to check:
    - Logic that needs two reads to differ.
    - Change detection based on timestamps.
  - Fix:
    - Use sequence numbers, counters, or version numbers where
      distinctness or change must be guaranteed.
    - Use ETags based on content hashes or versions for HTTP caching, and
      content hashes for build and sync change detection.
    - Handle zero elapsed time explicitly (PA-22, PA-68).
    - Generate unique IDs with ID generators, not clock reads (PA-30).
  - Not a finding:
    - Timestamps recorded for information only, with versions or hashes
      providing change detection.
  - Escalate (NEEDS-HUMAN): none specific.
  - Proposed severity (for the user to decide): HIGH when missed changes
    serve stale data, skip builds, or skip sync on a core path, or
    collisions overwrite records. MEDIUM for loops and metrics. LOW for
    test-only code.
- PA-107: Strictly increasing reads assumption. Code assumes the second
  of two consecutive calls to a current-time function always returns a
  larger value.
  - Overlap: PA-106 covers equal reads. PA-11, PA-65, and PA-68 cover time
    going backward. PA-107 covers code that needs strict increase, and the
    difference between "monotonic" and "strictly increasing". Merged per the class ledgers.
  - Why it is false:
    - Reads can be equal: wall clocks with millisecond resolution return
      the same value many times in a row (PA-105, PA-106).
    - Reads can be smaller: wall clocks step back, VMs restore, leap
      seconds repeat, and counters wrap (PA-11, PA-12, PA-46, PA-68).
    - "Monotonic" means non-decreasing, not strictly increasing. Python
      documents `time.monotonic()` as a clock that "cannot go backward",
      and Java documents `System.nanoTime()` only for elapsed-time
      differences. On this host 200,000 consecutive pairs of Python
      `time.monotonic_ns()` and of Node `performance.now()` were all
      strictly increasing (verified), but no platform guarantees that,
      and coarser clocks or other hosts can repeat values.
    - Reads in different threads, processes, or hosts are not ordered by
      their values: on some older multi-core systems, per-core counters
      disagreed (PA-21), and separate hosts have separate clocks (PA-60).
  - How it appears in code:
    - Assertions such as `assert t2 > t1`.
    - Version numbers, sequence numbers, or event-sourcing positions taken
      directly from the clock.
    - Last-write-wins or deduplication logic that uses `>` on timestamps
      (PA-14, PA-60).
    - Loops whose progress depends on each read being larger.
  - What to check:
    - Strict comparisons on clock reads.
    - Clock values used as versions or sequence positions.
  - Fix:
    - Measure durations with monotonic clocks and compare with `>=`,
      handling zero (PA-11, PA-68).
    - Where strictly increasing timestamps are needed, generate them as
      `next = max(now, last + 1 unit)`, keep `last` across restarts, and
      guard it with a lock in concurrent code.
    - Use database sequences or log offsets for ordering (PA-60, PA-65).
  - Not a finding:
    - Non-strict comparisons on monotonic clocks with explicit handling of
      equal values.
  - Escalate (NEEDS-HUMAN): none specific.
  - Proposed severity (for the user to decide): HIGH when versioning,
    ordering, or conflict resolution on a core path depends on strictly
    increasing clock reads. MEDIUM for assertions and loops. LOW for
    test-only code.
- PA-108: Looks-like-a-date assumption. Code assumes a string that looks
  like a timestamp is a timestamp, and a string that looks like a date is
  a date.
  - Overlap: PA-27 covers ambiguous formats and guessing parsers. PA-32
    covers display strings reused as data. PA-108 covers automatic type
    detection that turns non-date data into dates, or dates into other
    types.
  - Why it is false:
    - Identifiers look like dates. Spreadsheet software converted gene
      symbols such as `SEPT2` and `MARCH1` into dates often enough that the
      HUGO Gene Nomenclature Committee renamed those genes in 2020 (for
      example `SEPT1` to `SEPTIN1` and `MARCH1` to `MARCHF1`). Part
      numbers like `1-2`, fractions like `1/2`, and calendar-style
      versions like `2026.10` are converted too.
    - Numbers look like timestamps. A 10-digit order ID, account number,
      or phone number fits the epoch-seconds range (PA-27).
    - Configuration formats convert implicitly. PyYAML (YAML 1.1 rules)
      loads unquoted `2026-10-03` as a `date`, `22:22` as the integer
      1342, and `1:30:00` as 5400 (sexagesimal), while quoted
      `"2026-10-03"` stays a string (verified with PyYAML 6.0.1).
    - Data stores and libraries guess:
      - Elasticsearch dynamic mapping detects dates in strings by default,
        so the first value seen fixes a field as `date`, and later values
        that are not dates fail to index.
      - Json.NET (Newtonsoft) converts ISO-like strings to `DateTime` by
        default (`DateParseHandling.DateTime`), which can change the
        string's offset or text.
      - Data-frame readers and CSV importers can infer date columns.
    - Natural-language date parsers find dates in ordinary words: "may",
      "march", "second", "sun".
    - Even a real date string may follow another format, calendar, or
      zone than the one assumed (PA-27, PA-32, PA-41).
  - How it appears in code:
    - Automatic type inference on imports, configuration, logs, or search
      indexes.
    - Spreadsheets in data pipelines (exports opened and re-saved).
    - JSON or YAML loaded with default date conversion.
    - Regex or heuristic "is this a date?" checks on free text.
  - What to check:
    - Every place types are inferred from text.
    - Configuration and serialization settings for date detection.
    - Whether spreadsheets touch data in transit.
  - Fix:
    - Declare types by schema, not by appearance: explicit column types,
      search-index mappings, and serializer settings that keep strings as
      strings unless the schema says otherwise (BP-1).
    - Turn off date detection where values are not declared as dates (for
      example Elasticsearch `date_detection: false`, Json.NET
      `DateParseHandling.None`).
    - Quote dates and times in YAML, or use a YAML 1.2 loader without
      implicit timestamps.
    - Keep spreadsheets out of machine pipelines, or import columns as
      text explicitly.
  - Not a finding:
    - Schema-declared date fields parsed strictly.
  - Escalate (NEEDS-HUMAN): data sets whose field types are not
    documented and are inferred on import.
  - Proposed severity (for the user to decide): HIGH when inferred dates
    corrupt identifiers, configuration values, or indexed data on a core
    path. MEDIUM for analytics imports. LOW for test-only code.
- PA-109: Single official zone assumption. Code assumes every location on
  Earth has exactly one official time zone.
  - Overlap: PA-35 and PA-101 cover unofficial local time. PA-97 and
    PA-100 cover locations split between zones. PA-57 covers counting
    hours from dawn. PA-109 covers locations with competing official
    times, community-specific time, and places with no official zone.
    Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b where marked):
    - Disputed territories have competing official times. tzdata's
      `Europe/Simferopol` (Crimea) follows Moscow time (+03:00) since 2014,
      while Ukraine's `Europe/Kyiv` is +02:00 in January (verified). The
      tz database documents such choices as reflecting practice, not
      endorsing claims.
    - Communities on the same land keep different official times. In the
      West Bank, Palestinian communities follow the Palestinian Authority's
      DST rules (`Asia/Hebron`), while Israeli settlements follow Israel's
      (`Asia/Jerusalem`). In 2026 the two differ around the DST changes,
      for example on 2026-03-27 and 2026-10-24 (verified).
    - Official and practiced time differ: Xinjiang (PA-35), Phenix City
      (PA-101).
    - Some places have no official zone. On the high seas, ships keep
      nautical zones or ship's time by choice (PA-87). In Antarctica,
      stations choose a time, often their supply base's: McMurdo and the
      South Pole follow New Zealand time (`Antarctica/McMurdo`, +13:00 in
      January) (verified).
    - Craft keep conventions: the International Space Station uses UTC.
    - Clock reading can differ even under one official zone. Ethiopia's
      official zone is +03:00, but everyday time counts hours from about
      06:00 (PA-57).
    - A location's zone depends on the date (PA-9, PA-100).
  - How it appears in code:
    - Location-to-zone functions returning exactly one zone, with no
      ambiguity.
    - Zone choice for disputed regions fixed in code without a product
      decision.
    - Community-specific time (the West Bank) mapped by coordinates alone.
    - Ships, stations, and craft assigned a zone by position.
  - What to check:
    - Location-to-zone logic and how it handles disputed or overlapping
      areas.
    - Whether users can choose among valid zones for their location.
  - Fix:
    - Let users choose their zone, offering every valid option for the
      location (PA-17, PA-97).
    - Make zone choices for disputed regions an explicit, documented
      product decision, reviewed with legal or policy owners.
    - For ships, stations, and craft, store the zone they declare, not one
      derived from position.
  - Not a finding:
    - User-selected zones from the full IANA list.
  - Escalate (NEEDS-HUMAN): products serving disputed regions or
    communities with competing official times, where the zone policy is
    not stated.
  - Proposed severity (for the user to decide): HIGH when an imposed zone
    gives users wrong deadlines or appointments on a core path, or takes a
    political position the product did not decide. MEDIUM for display.
    LOW for test-only code.
- PA-110: Same-year DST period assumption. Code assumes each DST period
  starts and ends within one calendar year, once per year.
  - Overlap: PA-36 notes that southern-hemisphere DST spans New Year, and
    covers moving transition dates. PA-9 covers rule changes. PA-110
    covers DST periods modeled per calendar year: periods that cross the
    year, split within a year, or never end. Merged per the class ledgers.
  - Why it is false (transitions verified with tzdata 2026b):
    - Southern-hemisphere DST crosses New Year. Sydney switched to +11:00
      on 2026-10-04 and returns to +10:00 on 2027-04-04 (verified). New
      Zealand and Chile also run DST from September or October to April.
    - A year can contain two DST periods. Egypt suspended DST for Ramadan
      in 2014: +03:00 from 2014-05-16, back to +02:00 on 2014-06-26, +03:00
      again from 2014-08-01, and +02:00 from 2014-09-25 (verified).
      Morocco's Ramadan suspension also splits its year (PA-33).
    - A DST period can start and not end. Moscow moved to +04:00 on
      2011-03-27 and stayed there until 2014-10-26 (verified). Turkey kept
      summer time permanently from 2016, and Paraguay adopted permanent
      -03:00 in 2024 (PA-9).
    - A year can have an end and no start, or neither: Mexico ended DST
      in 2022 and did not restart it (PA-9).
    - Historical all-year summer time: the UK 1968 to 1971 (PA-47) and
      during the Second World War (PA-38).
  - How it appears in code:
    - DST modeled as one `(start, end)` pair per calendar year, with
      `start <= date < end`, which fails when the start comes after the
      end.
    - Tables keyed by year with exactly one start and one end.
    - Seasonal pricing, billing, or reports ("summer rates") defined per
      calendar year.
    - Year-by-year loops that compute "the" DST period.
  - What to check:
    - Any representation of DST periods.
    - Seasonal business rules tied to DST.
  - Fix:
    - Ask the library for the offset at each instant, or iterate
      transitions (for example Java `ZoneRules.nextTransition`), instead
      of modeling DST periods (BP-1, PA-36).
    - Define seasonal business rules by explicit date ranges that may
      cross the year, not by DST.
    - Test southern-hemisphere zones, Cairo 2014, and Moscow 2011 to 2014.
  - Not a finding:
    - Library offset lookups with no DST-period model in code.
  - Escalate (NEEDS-HUMAN): seasonal rules linked to "summer time" whose
    zone and period definition are not stated.
  - Proposed severity (for the user to decide): HIGH when DST-period
    models drive scheduling, billing, or deadlines on a core path. MEDIUM
    for seasonal reports. LOW for test-only code.
- PA-111: One DST period per year assumption. Code assumes any given year
  contains at most one period of DST.
  - Overlap: PA-110 covers DST periods that cross the year, split within a
    year (Egypt 2014), or never end. PA-111 adds how often split years
    occur, and calendar years containing parts of two periods. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b, sampling every 6 hours
    from 2000 to 2026):
    - Years with four offset changes, meaning two separate DST periods,
      occurred in `Africa/Cairo` (2010, 2014), `Africa/Casablanca` (2012,
      2013, 2015, 2016, 2017), and `Asia/Hebron` (2011), among 15
      zone-years found. Ramadan suspensions caused most of them.
    - In the southern hemisphere, every calendar year contains the end of
      one DST period and the start of the next. Sydney was on summer time
      until 2026-04-05 and again from 2026-10-04 (PA-110).
    - Morocco's current rules shift the clock twice around Ramadan each
      year, and which part counts as "DST" depends on the tz data format
      (PA-36, PA-52).
    - History adds more: the UK's wartime double summer time had two
      levels of summer time in one year (PA-38).
  - How it appears in code:
    - Data models holding one DST start and one DST end per year (PA-110).
    - Validation rejecting a year with more than two transitions.
    - "Is DST" computed from a single yearly window.
    - Reports or pricing with one "summer period" per year.
  - What to check:
    - Any per-year DST structure, and assumptions about transition counts.
  - Fix:
    - Iterate the zone's actual transitions, or ask for the offset at each
      instant, with no fixed count per year (BP-1, PA-110).
    - Test Cairo 2010 and 2014, Casablanca 2012 to 2017, Hebron 2011, and
      a southern-hemisphere zone.
  - Not a finding:
    - Library offset lookups with no per-year DST model.
  - Escalate (NEEDS-HUMAN): none beyond PA-110.
  - Proposed severity (for the user to decide): same as PA-110.
- PA-112: Midnight-is-12-AM assumption. Code assumes midnight in a
  12-hour time string always reads as 12 followed by "AM".
  - Overlap: PA-32 covers locale formats. PA-84 and PA-85 cover AM/PM in
    parsing and the `hour % 12` formatting trap. PA-112 covers how
    midnight and noon are written across locales and hour cycles, and the
    ambiguity of "midnight" as a deadline.
  - Why it is false (Node `Intl.DateTimeFormat` output for 00:00, verified,
    non-ASCII results described in words):
    - `en-US`: `12:00 AM`. `en-GB` and `en-AU` with a 12-hour clock:
      `12:00 am` (lower case).
    - Japanese (`ja-JP`, 12-hour): the morning marker comes first and the
      hour is 0 ("gozen 0:00"). Japanese 12-hour time runs 0 to 11, so
      noon is "gogo 0:00".
    - Chinese (`zh-CN`) and Korean (`ko-KR`): the marker comes before the
      time ("shangwu 12:00", "ojeon 12:00").
    - Hour cycles differ: `hourCycle: "h11"` gives `0:00 AM`, and
      `hourCycle: "h24"` gives `24:00` for midnight.
    - Day periods: with `dayPeriod: "long"`, midnight is `12 in the
      morning`. Other locales use words for "night" or "early morning".
    - Markers differ: `AM`, `am`, `a.m.`, and locale words, before or after
      the time. Some ICU versions placed a narrow no-break space (U+202F)
      before `AM`/`PM`, breaking parsers that expected a plain space. This
      Node build (ICU 77.1) emits a plain space (verified).
    - Style guides avoid "12 AM" and "12 PM" as ambiguous and recommend
      "12 midnight" and "12 noon".
    - "Midnight" as a deadline is ambiguous: "midnight on Friday" can mean
      the start or the end of Friday. Contracts often write 23:59 or
      12:01 AM instead.
  - How it appears in code:
    - Hand-built 12-hour formatting (`hour % 12 || 12` plus " AM") for
      every locale (PA-85).
    - Parsers expecting `AM`/`PM` as an ASCII suffix after a plain space.
    - Midnight and noon swapped by `12 AM`/`12 PM` handling bugs (PA-84).
    - Deadlines displayed or stored as "midnight" with no date boundary
      stated.
  - What to check:
    - Custom 12-hour formatting and parsing.
    - Tests for 00:00 and 12:00 in each supported locale.
    - How deadlines at midnight are stated and enforced.
  - Fix:
    - Format and parse with locale-aware libraries, never by hand (BP-1,
      PA-85).
    - Use 24-hour or ISO formats for machine data (PA-32).
    - State midnight deadlines as an unambiguous instant or half-open
      range ("before 2026-10-10T00:00 in America/New_York"), and display
      them as "end of Friday" or 23:59 where users read them.
  - Not a finding:
    - Library-formatted 12-hour times for display only.
  - Escalate (NEEDS-HUMAN): deadlines or schedules written as "midnight"
    or "12 AM" where start or end of day is not stated.
  - Proposed severity (for the user to decide): HIGH when midnight or noon
    handling shifts deadlines or appointments by 12 or 24 hours on a core
    path. MEDIUM for display. LOW for test-only code.
- PA-113: Four-year leap cycle assumption. Code assumes a leap year
  comes exactly every four years.
  - Overlap: PA-42 covers the divisible-by-four rule as a test. PA-113
    covers the gap between leap years: code that steps by four years, and
    schedules built on a four-year rhythm. Merged per the class ledgers.
  - Why it is false:
    - Gregorian gaps are usually 4 years but sometimes 8. Between 1880 and
      2420 the exceptions are 1896 to 1904, 2096 to 2104, 2196 to 2204, and
      2296 to 2304 (verified with Python `calendar.isleap`).
    - Other calendars have irregular gaps: Hebrew leap years fall 7 times
      in 19 years (gaps of 2 or 3 years), tabular Islamic leap years 11
      times in 30, and Solar Hijri leap years follow the equinox, with
      gaps of 4 or 5 years (PA-42).
  - How it appears in code:
    - "Next leap year" computed as `last_leap + 4`.
    - Leap-day events, billing, or maintenance scheduled every fourth
      year.
    - Recurring February 29 events. RFC 5545 recurrence rules skip
      February 29 in years that lack it, so the gap after 2096 is eight
      years. Hand-built recurrences differ.
    - Averages such as 365.25 days per year used as exact (PA-3).
  - What to check:
    - Stepping logic and schedules based on four-year intervals.
    - Handling of February 29 recurrences.
  - Fix:
    - Test each year with the library's leap test, never step by four
      (BP-1, PA-42).
    - Generate February 29 recurrences with a recurrence library and a
      stated rule for missing years (PA-3).
    - Test across 2096 to 2104.
  - Not a finding:
    - Four-year stepping in code whose documented range lies within 1901
      to 2099 and is enforced.
  - Escalate (NEEDS-HUMAN): long-horizon schedules (pensions, leases,
    leap-day contracts) where the leap-year rule used is not stated.
  - Proposed severity (for the user to decide): HIGH when long-horizon
    schedules or billing on a core path step by four years. MEDIUM for
    reports. LOW for test-only code.
- PA-114: Fixed duration unit assumption. Code assumes an integer
  duration is always in one known unit, such as seconds.
  - Overlap: PA-23 covers units of epoch timestamps. PA-86 covers ISO 8601
    duration strings. PA-114 covers bare integer durations in APIs and
    configuration.
  - Why it is false: units differ between APIs, often in the same stack.
    - Milliseconds: JS `setTimeout`, Java `Thread.sleep`, many socket and
      client timeouts, Redis `PEXPIRE`, Kafka settings ending in `.ms`,
      and Postgres `statement_timeout` when given without a unit.
    - Seconds: Python `time.sleep`, HTTP `Cache-Control: max-age`,
      `Retry-After` (seconds, or an HTTP date), cookie `Max-Age`, JWT
      claims, Redis `EXPIRE`, MySQL `wait_timeout`, and Kubernetes probe
      settings.
    - Microseconds: POSIX `usleep`.
    - Nanoseconds: Go `time.Duration`. Converting the integer 30 directly
      gives `30ns`. Multiplying by `time.Second` gives `30s` (verified).
      `time.Sleep(timeout)` with a bare integer sleeps nanoseconds.
    - 100-nanosecond ticks: .NET `new TimeSpan(10)` is one microsecond.
    - Minutes, hours, or days: cron schedules, certificate validity, and
      password-expiry settings.
    - Platform units: Linux jiffies, video frames, audio samples.
  - How it appears in code:
    - Unitless configuration keys (`timeout = 30`) read by code expecting a
      different unit.
    - Milliseconds passed to a seconds API (1,000 times too long) or
      seconds to a milliseconds API (1,000 times too short).
    - Go durations built from integers without unit constants.
    - JSON fields with numeric durations and no unit in the name or
      schema.
  - What to check:
    - Every duration crossing an API, configuration, or wire boundary:
      unit expected versus unit supplied.
    - Duration types in Go, .NET, Java, and Python code.
  - Fix:
    - Use typed durations (Go `time.Duration` with unit constants, Java
      `Duration`, Python `timedelta`, .NET `TimeSpan.FromSeconds`) inside
      code (BP-1).
    - Put the unit in names (`timeout_ms`) or use unit suffixes in
      configuration (`30s`), and validate plausible ranges so 1,000-fold
      errors fail fast.
    - Use ISO 8601 durations or documented units at interfaces (PA-86).
  - Not a finding:
    - Integer durations whose unit is in the name, the schema, or the type,
      and matches the consumer.
  - Escalate (NEEDS-HUMAN): interfaces exchanging numeric durations with no
    documented unit.
  - Proposed severity (for the user to decide): HIGH when unit errors set
    timeouts, expiries, rate limits, or retention on a core path off by
    factors of 1,000 or more. MEDIUM for metrics and logs. LOW for
    test-only code.
- PA-115: Consistent negative duration assumption. Code assumes a
  negative integer duration means the same thing everywhere.
  - Overlap: PA-68 covers runtimes' reactions to negative sleeps. PA-79
    covers floor versus truncating division. PA-86 covers negative ISO
    durations. PA-114 covers duration units. PA-115 covers the meanings
    APIs and formats assign to negative values, and how negative
    durations are represented.
  - Why it is false: negative values mean different things in different
    places.
    - "Wait forever": `poll()` and `epoll_wait()` treat a timeout of -1 as
      infinite. Kafka treats `retention.ms = -1` as unlimited retention.
      Windows' `INFINITE` is `0xFFFFFFFF`, which is -1 as a signed 32-bit
      value.
    - Status codes: Redis `TTL` returns -1 for a key without expiry and -2
      for a missing key.
    - "Already expired": a cookie `Max-Age` of zero or less expires the
      cookie immediately (RFC 6265). Go `context.WithTimeout` with a
      negative duration is already done.
    - "Do it now": JS `setTimeout(fn, -1000)` fires almost immediately, and
      Go `time.Sleep` with a negative duration returns at once (PA-68).
    - "Error": Python `time.sleep(-1)` raises `ValueError`, and Java
      `Thread.sleep(-1)` throws (PA-68).
    - "Invalid, so stale": HTTP caches treat an invalid `max-age` as
      stale.
    - "Before" or "earlier": a negative offset or delta in arithmetic.
    - Unsigned wrap: -1 stored in an unsigned 32-bit millisecond field
      becomes 4,294,967,295 ms, about 49.7 days (verified arithmetic)
      (PA-68).
  - Representations disagree (verified):
    - Python `timedelta(seconds=-1)` is stored as `days=-1, seconds=86399`
      and prints as `-1 day, 23:59:59`, though `total_seconds()` is -1.0.
    - Java `Duration.ofMillis(-1500)` prints `PT-1.5S` but stores
      `getSeconds() = -2` and `getNano() = 500000000`.
    - Code that reads individual fields instead of totals gets the wrong
      sign or size.
  - How it appears in code:
    - -1 or 0 passed as "no timeout" to an API where it means "expire now",
      or the reverse.
    - Sentinels such as -1 meaning "unset" stored in duration fields and
      later used in arithmetic.
    - Negative durations computed from clock differences and passed to
      sleeps, timers, or expiries without a check (PA-68).
    - Fields of `timedelta` or `Duration` read individually.
  - What to check:
    - Every duration passed across an API: whether negative and zero
      values are possible, and what the callee does with them.
    - Sentinel values in duration fields.
  - Fix:
    - Represent "no limit" and "unset" explicitly (nullable fields,
      optional types, named constants), not as negative numbers (PA-18).
    - Validate durations at boundaries: reject or clamp negatives by a
      stated rule before calling sleeps, timers, or expiry APIs.
    - Read totals (`total_seconds()`, `toMillis()`), not individual
      fields.
    - Document what negative and zero mean in each interface you own.
  - Not a finding:
    - Documented sentinel values used only with the API that defines them.
  - Escalate (NEEDS-HUMAN): configuration or interfaces where negative or
    zero durations are accepted without documented meaning.
  - Proposed severity (for the user to decide): HIGH when a negative or
    zero duration disables expiry, retention limits, or timeouts on a
    core path, or expires data immediately. MEDIUM for configuration
    validation. LOW for test-only code.
- PA-116: Good-faith date handling assumption. Teams assume no software
  ever mishandles dates on purpose.
  - Overlap: PA-11 covers users setting clocks to cheat. PA-26 covers
    user-controllable time. PA-31 covers falsified timestamps. PA-17,
    PA-24, and PA-105 cover privacy features that report coarse or false
    time. PA-116 covers deliberate date misbehavior as a category: kept
    for compatibility, built in as a time-triggered behavior, or used to
    deceive.
  - Why it is false:
    - Compatibility quirks are kept on purpose. Excel keeps the
      nonexistent 1900-02-29 for Lotus 1-2-3 compatibility (PA-4). JS
      keeps zero-based months and `getYear()` returning the year minus
      1900 for web compatibility (PA-2, PA-74). Java's legacy `Calendar`
      keeps zero-based months. Code that "fixes" these breaks.
    - Time-triggered behavior is built in on purpose: trial expirations,
      license time bombs, beta "kill dates", and certificate and token
      lifetimes.
    - Malicious time triggers exist. Logic bombs fire on a date or after a
      time. Historical viruses such as Michelangelo (March 6) and CIH (April
      26) were date-triggered. Insiders have planted time-triggered
      deletions.
    - Timestamps are falsified on purpose. Attackers change file
      timestamps to hide activity ("timestomping", MITRE ATT&CK technique
      T1070.006). Documents, records, and stock-option grants have been
      backdated.
    - Clocks and zones are misreported on purpose for privacy (Tor and
      Firefox's fingerprinting resistance report UTC, browsers coarsen
      timers) and for fairness (leap-second smearing) (PA-17, PA-20,
      PA-105).
    - Presentation can mislead on purpose: renewal or cancellation
      deadlines shown in a zone or format that favors the vendor, or
      rounding rules that always favor one side (PA-81, PA-82).
  - How it appears in code:
    - Comparisons against hardcoded future dates
      (`if now > 2027-01-01: ...`), especially guarding destructive,
      disabling, or exfiltrating actions.
    - Time-conditional branches in third-party dependencies.
    - Code that sets file or record timestamps outside tooling that is
      meant to (for example `os.utime` or `touch -d` in application code).
    - Audit or record timestamps that users or operators can edit.
    - "Fixes" to known compatibility quirks without checking consumers.
  - What to check:
    - Hardcoded dates and time-based conditions, and what each one guards.
    - Code that writes timestamps on files, records, or audit trails.
    - Dependency code with date-triggered behavior.
    - Deadline presentation and rounding rules in customer-facing flows.
  - Fix:
    - Require a documented owner and reason for every time-conditional
      behavior, and review hardcoded future dates as potential time bombs.
    - Keep audit timestamps server-assigned and append-only (PA-31).
    - Restrict timestamp-setting calls to tooling that needs them.
    - Document intentional compatibility quirks where code depends on them,
      and wrap them rather than "fix" them in place.
    - Present deadlines in the user's zone with the zone named (PA-17,
      PA-112).
  - Not a finding:
    - Documented, owned expirations (trials, certificates, tokens) that
      fail safely.
  - Escalate (NEEDS-HUMAN): any undocumented date-triggered behavior that
    disables, deletes, or sends data, in first- or third-party code.
  - Proposed severity (for the user to decide): CRITICAL for
    undocumented time-triggered destructive or exfiltrating code, or
    editable audit timestamps. HIGH for timestamp-forging code paths and
    misleading deadline presentation on core paths. MEDIUM for
    undocumented compatibility workarounds. LOW for test-only code.
- PA-117: Good-faith timer assumption. Teams assume no software ever
  mishandles timers on purpose.
  - Overlap: PA-21, PA-22, PA-24, and PA-62 cover throttled, paused, and
    imprecise timers. PA-26 covers fake clocks reaching production.
    PA-116 covers deliberate date mishandling. PA-117 covers deliberate
    timer interference: by platforms, tools, users, and attackers.
  - Why it is false:
    - Platforms delay timers on purpose to save power or improve
      security:
      - Browsers throttle background-tab timers, clamp nested `setTimeout`
        delays to at least 4 ms, and coarsen `performance.now()` (PA-21,
        PA-24).
      - Operating systems coalesce timers to save power (macOS App Nap,
        Windows power throttling, Linux timer slack).
      - Android Doze and App Standby defer alarms and jobs. Android's
        documentation has limited idle-allowed alarms to about once per
        nine minutes per app during Doze.
      - iOS suspends background apps, stopping their timers.
      - Serverless platforms freeze execution between invocations
        (PA-22).
    - Services slow responses on purpose: rate limiting, `Retry-After`,
      tarpitting abusive clients, and random jitter in backoff.
    - Security code adds or removes timing on purpose: constant-time
      comparisons, random delays against timing attacks.
    - Tools fake time on purpose: fake timers in tests (Jest, Sinon),
      `libfaketime`, and debuggers that pause execution (PA-25, PA-26).
    - Users speed up or slow down a process's time functions to cheat
      (Cheat Engine's speedhack) (PA-21).
    - Attackers evade analysis with time. Malware sleeps for long periods
      to outlast sandboxes, and sandboxes skip or accelerate sleeps in
      response. MITRE ATT&CK lists this as "Time Based Evasion"
      (T1497.003).
  - How it appears in code:
    - Correctness or security that depends on a client-side timer firing
      on time (cooldowns, session locks, timed exams, rate limits)
      (PA-21).
    - Reminders, payments, or alarms on mobile scheduled with timers that
      the OS can defer.
    - Fake-timer setup in shared test code that can load in production
      (PA-26).
    - Sleeps used to delay security-relevant actions, assuming nobody can
      skip them.
  - What to check:
    - Any timer whose late, early, skipped, or accelerated firing changes
      an outcome.
    - Platform scheduling APIs used for time-critical mobile work.
    - Separation of test timer utilities from production code.
  - Fix:
    - Enforce time-dependent rules on the server with server time
      (PA-14, PA-21).
    - On mobile, use platform scheduling APIs intended for exact or
      user-visible alarms, within the platform's rules, and recheck the
      clock when the work runs (PA-22).
    - Keep fake timers out of production builds (PA-26).
    - Design for late, skipped, and accelerated timers: compare against
      the clock on every wake, and make actions idempotent (PA-54,
      PA-62).
  - Not a finding:
    - Client-side timers used only for user experience, with the server
      enforcing the rule.
  - Escalate (NEEDS-HUMAN): time-critical mobile or embedded features
    whose required timing guarantees are not stated.
  - Proposed severity (for the user to decide): HIGH when a deliberately
    delayed, skipped, or accelerated timer can bypass a security or
    billing rule, or miss a safety-relevant action, on a core path.
    MEDIUM for reminders and UX timers. LOW for test-only code.
- PA-118: Known historical year length assumption. Code assumes the
  length of every historical year is known.
  - Overlap: PA-3, PA-19, PA-40, PA-43, and PA-45 cover reform years,
    proleptic calendars, and regional adoption. PA-118 covers years whose
    length is uncertain or disputed, year-start conventions, and the
    physical length of days and years over long spans.
  - Why it is false:
    - Ancient calendars were irregular. Roman Republican intercalation was
      decided by officials, sometimes for political reasons, and the year
      46 BC lasted 445 days as Julius Caesar realigned the calendar.
    - Early Julian leap years were misapplied: leap years were inserted
      every third year at first, then suspended under Augustus to correct
      the drift. Scholars disagree on the exact sequence, so Julian dates
      before about AD 8 are uncertain by a day or more.
    - Countries adopted the Gregorian calendar over more than three
      centuries: Catholic states in 1582, Protestant German states in 1700,
      Britain in 1752, Japan in 1873, Russia in 1918, Greece in 1923, and
      Turkey in 1926, with Swiss cantons switching at different times.
      Sweden followed its own path from 1700 to 1712 (PA-43). The length
      of a given year depends on the place.
    - The year did not always start on January 1. England started legal
      years on March 25 until 1752, so 1751 lasted only 282 days (PA-3),
      and many Italian states used other start dates. Records are often
      "double dated" (for example 1750/51).
    - Lunisolar and observational calendars set leap months or month
      lengths by observation, and historical records do not always say
      which choice was made (PA-39).
    - Physically, days and years change length. Tidal friction slows
      Earth's rotation, so a year contained more days in the geological
      past. The accumulated difference between rotation-based and uniform
      time (Delta T) grows to hours for ancient dates, and is known only
      approximately from historical eclipse records.
    - Since 1972, leap seconds have changed the length of some UTC years
      (PA-46).
  - How it appears in code:
    - Intervals, ages, or anniversaries computed across ancient or
      reform-era dates with a proleptic calendar (PA-19).
    - One reform date applied to every country (PA-45).
    - Historical years assumed to start on January 1.
    - Ancient astronomical events placed in UTC without a Delta T model.
    - Historical dates shown without uncertainty.
  - What to check:
    - The date range of historical data and the calendar of each source.
    - How year starts and double dating are handled.
  - Fix:
    - Record each historical date's source calendar, region, and
      year-start convention, and keep the original text (PA-19).
    - Convert with libraries or tables built for historical chronology,
      and show uncertainty where scholars disagree.
    - Support double dating where sources use it.
    - Use a published Delta T model for astronomical work on ancient
      dates.
  - Not a finding:
    - Modern-date products validated to a modern range (PA-72).
  - Escalate (NEEDS-HUMAN): historical, genealogical, legal-archive, or
    astronomical data where source calendars, regions, and year-start
    conventions are not recorded.
  - Proposed severity (for the user to decide): HIGH when historical or
    legal-archive records on a core path are converted or compared with
    wrong year lengths. MEDIUM for display. LOW for test-only code.
- PA-119: Integer frequency assumption. Code assumes devices refresh,
  sample, or respond at whole-number frequencies.
  - Overlap: PA-20 and PA-21 cover clock rates. PA-24 covers timer
    granularity. PA-21 covers fixed time steps per frame. PA-119 covers
    media, display, audio, power, and device frequencies that are not
    whole numbers or not fixed.
  - Why it is false:
    - Video frame rates descended from NTSC color television are
      fractional: "29.97" is exactly 30000/1001 (29.97002997...),
      "23.976" is 24000/1001, and "59.94" is 60000/1001. Treating 30000/1001
      as 30 fps drifts by about 107.9 frames, or 3.6 seconds, per hour
      (computed with exact fractions). SMPTE drop-frame timecode exists
      to keep labels aligned with clock time: it skips frame numbers 00
      and 01 at the start of each minute, except every tenth minute.
    - Display refresh rates are often fractional (59.94 Hz, 119.88 Hz) or
      variable (adaptive sync, phone displays that change rate with
      content). `requestAnimationFrame` follows the display and can drop
      to zero in background tabs (PA-21).
    - Audio devices with the same nominal rate (48,000 Hz) drift apart by
      parts per million, so streams between devices need resampling or
      drift correction (PA-20).
    - Power grids run near, not at, 50 or 60 Hz. Clocks that count grid
      cycles drift with it: in 2018 a sustained frequency deficit in the
      continental European grid left such clocks (for example in ovens)
      about six minutes slow.
    - Kernel timer frequencies are whole numbers of hertz, but the periods
      are not whole milliseconds: Windows' default 64 Hz tick is 15.625
      ms, and Linux `HZ=300` gives 3.333 ms (PA-24).
    - Sensors and game servers sample at nominal rates with jitter, and
      networks deliver samples late or in bursts.
  - How it appears in code:
    - Media timestamps computed as `frame_count / 30` or with float 29.97.
    - Drop-frame and non-drop-frame timecode mixed or hand-converted.
    - Animation or physics stepped by a fixed 1/60 second per frame
      (PA-21).
    - Durations derived from sample counts at a nominal device rate over
      long recordings.
    - Grid-cycle or tick counts used as clocks.
  - What to check:
    - Frame-rate and sample-rate representations: floats, integers, or
      rationals.
    - Timecode handling in media code.
    - Any time derived from counting frames, samples, ticks, or cycles.
  - Fix:
    - Represent rates as exact rationals (for example the numerator and
      denominator pairs FFmpeg uses), and derive times from presentation
      timestamps, not frame counts times a float rate.
    - Use timecode libraries that implement drop-frame rules (BP-1).
    - Step animation by measured elapsed time (PA-21).
    - Measure actual device rates and correct drift between devices.
    - Use a real clock, not cycle counts, for time.
  - Not a finding:
    - Rational-rate media pipelines using timestamps from the container or
      stream.
  - Escalate (NEEDS-HUMAN): media, broadcast, or audio products whose
    frame-rate and timecode standards are not stated.
  - Proposed severity (for the user to decide): HIGH when broadcast
    timing, captions, billing by media duration, or synchronization on a
    core path drift because of integer-rate assumptions. MEDIUM for
    animation and metrics. LOW for test-only code.
- PA-120: Constant frequency assumption. Code assumes a device keeps
  refreshing, sampling, or responding at one steady rate.
  - Overlap: PA-119 covers non-integer and variable display rates. PA-21
    and PA-117 cover throttled and deferred timers. PA-120 covers rates
    that change over time on one device, and code that infers time from
    counts.
  - Why it is false:
    - Displays change rate: adaptive refresh panels move between high
      rates and very low ones for always-on displays, and power-saving
      modes cap the rate.
    - Frame pacing is uneven even at fixed rates: 24 fps video on a 60 Hz
      display alternates frames shown for 3 and 2 refreshes, about 50 ms
      and 33 ms (3:2 pulldown, computed from the rates).
    - Phone recordings are often variable-frame-rate video. Tools that
      assume a constant rate desynchronize audio and video.
    - Power and heat change rates: thermal throttling lowers frame and
      processing rates, and battery savers reduce GPS and sensor sampling.
    - Operating systems batch sensor events and deliver them late in
      groups, and background location updates become infrequent.
    - Radios and networks vary: Bluetooth connection intervals are
      renegotiated, Wi-Fi power saving delays delivery, and network jitter
      reorders and bunches packets.
    - Servers vary: game servers drop ticks under load, and pauses stall
      processing (PA-21).
  - How it appears in code:
    - Time computed as `sample_index * nominal_period`.
    - A fixed `dt` per frame or per sample in physics, animation, or sensor
      fusion (PA-21).
    - Game cooldowns and effects counted in frames, so they run faster or
      slower with frame rate.
    - Media pipelines that assume constant frame rate.
    - Gaps or bursts treated as faults or data loss.
  - What to check:
    - Any time inferred from counts of frames, samples, or ticks.
    - Handling of variable-rate input, gaps, and bursts.
  - Fix:
    - Use the timestamp attached to each sample, event, or frame (sensor
      event timestamps, presentation timestamps), not the count.
    - Support variable-frame-rate media end to end, or convert it
      deliberately at ingest.
    - Run game and simulation logic on measured time. For physics, use a
      fixed step with an accumulator driven by measured time, so results
      stay stable when frame rate changes.
    - Buffer for jitter and tolerate gaps and bursts.
  - Not a finding:
    - Pipelines driven by per-sample timestamps.
  - Escalate (NEEDS-HUMAN): sensor, medical-device, or control systems
    whose required sampling regularity is not stated.
  - Proposed severity (for the user to decide): HIGH when medical,
    safety, or control readings, or media synchronization, on a core path
    assume a constant rate. MEDIUM for games and animation. LOW for
    test-only code.
- PA-121: Same-rate synchronization assumption. Code assumes two signals
  or streams with the same clock rate are synchronized.
  - Overlap: PA-13 and PA-16 cover offsets between clocks. PA-20 and
    PA-119 cover drift between nominally equal rates. PA-60 and PA-94
    cover ordering and frames of reference. PA-121 covers the difference
    between matching rates and matching time, for media, sensors, and
    hardware.
  - Why it is false:
    - Equal frequency (syntonization) is not equal time (synchronization).
      Two 48 kHz streams can start at different moments and stay offset
      forever.
    - Independent oscillators with the same nominal rate drift apart
      (PA-20, PA-119).
    - Pipelines add different latencies: buffers, encoders, networks, and
      device drivers delay each stream by different and changing amounts.
    - Streams use different time bases. Presentation timestamps start at
      arbitrary values, and MPEG transport-stream timestamps (33 bits at
      90 kHz) wrap about every 26.5 hours (computed).
    - In hardware, two clocks at the same nominal frequency from different
      oscillators are asynchronous. Passing signals between them needs
      clock-domain-crossing synchronizers, or data is corrupted by
      metastability.
    - People notice small offsets: ITU-R BT.1359 reports audio-video
      offsets becoming detectable at about 45 ms with audio leading and
      about 125 ms with audio lagging.
    - Sensors at the same rate (for example camera and inertial sensor
      both at 100 Hz) sample at different instants, and each stamps time
      with its own clock (PA-94).
  - How it appears in code:
    - Streams merged or aligned by sample or frame index.
    - Offsets between streams assumed to be zero, or measured once.
    - Pipeline latency ignored when combining audio, video, or sensor
      data.
    - Timestamps from different streams compared without a common base,
      or without handling wraparound.
  - What to check:
    - How streams are aligned, and the common reference used.
    - Latency measurement and compensation.
    - Timestamp wraparound handling.
  - Fix:
    - Share a reference: genlock for video, word clock for audio, PTP
      (IEEE 1588) or GPS pulse-per-second for distributed systems.
    - Timestamp at capture against the common clock, and align by
      timestamp, not index.
    - Measure and correct offset, latency, and drift continuously
      (PA-119).
    - Handle timestamp wraparound explicitly (PA-68).
  - Not a finding:
    - Pipelines aligned by capture timestamps from a shared reference
      clock.
  - Escalate (NEEDS-HUMAN): media, broadcast, sensor-fusion, or test and
    measurement systems whose synchronization tolerance is not stated.
  - Proposed severity (for the user to decide): HIGH when misaligned
    streams corrupt measurements, control, or broadcast output on a core
    path. MEDIUM for consumer media lip sync. LOW for test-only code.
- PA-122: Persistent synchronization assumption. Code assumes two signals
  that were synchronized once, at the same clock rate, stay synchronized.
  - Overlap: PA-13 and PA-16 cover offsets measured once between clocks.
    PA-121 covers rate versus time alignment and shared references.
    PA-122 covers how synchronization is lost over time and through
    events, and code that syncs only at the start.
  - Why it is false:
    - Small rate differences accumulate. A 10 ppm difference is 0.864
      seconds per day, or 41,472 samples per day at 48 kHz (computed).
      Long recordings, live streams, and long-running sessions drift out
      of alignment (PA-20, PA-119).
    - References get lost. When GPS reception, a PTP grandmaster, or an
      NTP server drops out, local clocks enter "holdover" and drift at
      the oscillator's rate. Failing over to another reference or
      reacquiring the original can step the clock (PA-11).
    - Events break alignment: device sleep and resume, Bluetooth
      reconnects, hot-plugged audio interfaces, VM migration, and thermal
      changes (PA-20, PA-21, PA-22).
    - Lost packets, dropped frames, and buffer underruns or overruns shift
      any alignment based on counting samples or frames, permanently
      (PA-120).
    - Timestamps wrap (PA-121) and leap-second handling differs between
      sources (PA-20).
    - In film and broadcast, separate recorders synced once with a clap or
      slate drift apart unless they share timecode or a reference clock.
  - How it appears in code:
    - Synchronization performed once at start, then alignment by index or
      by a fixed offset.
    - No monitoring of offset or lock state during a session.
    - No defined behavior when the reference is lost.
    - Gaps and duplicates not detected, so later data misaligns.
  - What to check:
    - Whether synchronization is continuous, and how loss of lock is
      detected and reported.
    - Holdover requirements and behavior.
    - Gap and overrun handling in streams.
  - Fix:
    - Monitor and correct continuously: servo loops that adjust rate, and
      resampling for audio (PA-119, PA-121).
    - Detect loss of lock and mark the affected data's quality and sync
      state (PA-94).
    - Specify a holdover budget, and re-synchronize after resume,
      reconnect, and failover.
    - Align by timestamps, and fill or flag gaps rather than shifting data.
  - Not a finding:
    - Systems with continuous synchronization, monitored lock state, and
      documented holdover behavior.
  - Escalate (NEEDS-HUMAN): long-running media, measurement, or control
    systems whose drift tolerance and holdover requirements are not
    stated.
  - Proposed severity (for the user to decide): HIGH when drift or lost
    lock corrupts measurements, control, or broadcast output on a core
    path without detection. MEDIUM for consumer media. LOW for test-only
    code.
- PA-123: January fiscal year assumption. Code assumes the fiscal year
  starts on January 1.
  - Overlap: PA-7 notes that fiscal and tax years do not start on
    January 1, and covers attribution across year boundaries. PA-6 and
    PA-7 cover 52/53-week years. PA-123 covers the variety of fiscal and
    tax years, labeling conventions, and code that derives fiscal periods
    from calendar dates.
  - Why it is false:
    - Governments differ:
      - US federal government: October 1 to September 30. Most US states
        start July 1. New York starts April 1, and Texas September 1.
      - UK government: April 1. UK personal tax year: April 6 to April 5,
        a date inherited from the 1752 calendar change.
      - Canada federal, Japan, and India: April 1.
      - Australia: July 1 to June 30. New Zealand: government July 1, tax
        year April 1.
      - Iran: Nowruz, around March 21, on the Solar Hijri calendar.
    - Companies choose freely: July 1 (Microsoft), February 1 (Walmart,
      whose year ends January 31), or a 52/53-week year ending on the last
      Saturday of September (Apple).
    - Labels differ: "FY2027" in the US federal convention is the year
      ending in 2027 (starting October 2026). Many Japanese organizations
      name the fiscal year by its starting year.
    - Fiscal quarters follow the fiscal year, so "Q1" means different
      months for different entities.
    - Entities change fiscal years, producing short transition years.
  - How it appears in code:
    - Fiscal year computed as the calendar year, or quarter as
      `(month - 1) // 3 + 1`.
    - Tax calculations grouped by calendar year.
    - "FY" labels built with one convention for every entity.
    - 52/53-week fiscal years approximated by month boundaries.
  - What to check:
    - Every fiscal or tax period calculation and label.
    - Where each entity's fiscal calendar is defined.
  - Fix:
    - Make the fiscal calendar configuration per entity and jurisdiction:
      start date or 52/53-week rule, label convention, and effective dates
      for changes.
    - Compute fiscal periods from that configuration in one service, and
      test transition years.
    - Use the jurisdiction's tax year for tax calculations.
  - Not a finding:
    - Configurable fiscal calendars with documented label conventions.
  - Escalate (NEEDS-HUMAN): financial or tax features whose fiscal
    calendar and label convention are not stated.
  - Proposed severity (for the user to decide): HIGH when financial
    statements, tax filings, budgets, or regulated reports on a core path
    use the wrong fiscal year. MEDIUM for dashboards and labels. LOW for
    test-only code.
- PA-124: Global fiscal year assumption. Code assumes a company uses the
  same fiscal year everywhere it operates.
  - Overlap: PA-123 covers fiscal-year variety and per-entity
    configuration. PA-124 covers multinational groups whose legal
    entities must or do use different years, and consolidation across
    them. Merged per the class ledgers.
  - Why it is false:
    - Local law can dictate the year. India's Companies Act 2013 defines
      the financial year as April 1 to March 31, with exceptions only by
      approval for subsidiaries of foreign companies. Chinese statutory
      accounts use the calendar year. Many Japanese companies close on
      March 31.
    - Local calendars set some years: Iran's fiscal year starts at Nowruz
      on the Solar Hijri calendar (PA-41), and Ethiopia's and Nepal's
      start in July.
    - Tax years differ from accounting years in many jurisdictions (UK
      personal tax year from April 6), and VAT and payroll periods differ
      again (PA-123).
    - Groups consolidate subsidiaries with different year-ends.
      Accounting standards permit this within limits: IFRS 10 allows a
      subsidiary's reporting date to differ from the parent's by no more
      than three months, with adjustments for significant events.
    - Acquisitions bring entities with their own years, and changes create
      short transition periods.
    - Entities in one group mix 52/53-week years and month-end years
      (PA-6, PA-7).
  - How it appears in code:
    - One global fiscal calendar setting for all entities.
    - Consolidation by period label (for example "Q2") without mapping
      each entity's period to the group's.
    - Local statutory or tax reports generated from the group calendar.
    - Payroll and tax periods derived from the fiscal year.
  - What to check:
    - Where fiscal, statutory, tax, and payroll calendars are defined, and
      at what level (group, legal entity, jurisdiction).
    - How periods are mapped during consolidation.
  - Fix:
    - Define calendars per legal entity, with separate statutory, tax,
      management, and payroll calendars where they differ, all
      effective-dated (PA-123).
    - Map each entity's periods to group periods explicitly, with
      documented offsets and adjustments.
    - Generate statutory and tax reports from each entity's own
      calendars.
  - Not a finding:
    - Per-entity calendars with documented consolidation mapping.
  - Escalate (NEEDS-HUMAN): finance, tax, or payroll systems for
    multi-entity organizations where calendars per entity and
    jurisdiction are not stated.
  - Proposed severity (for the user to decide): HIGH when statutory
    filings, tax returns, payroll, or consolidated statements on a core
    path use another entity's fiscal year. MEDIUM for management
    dashboards. LOW for test-only code.
- PA-125: Date-as-UTC-midnight assumption. Code assumes a date such as
  2026-10-03 is the same as the instant 2026-10-03T00:00:00Z.
  - Overlap: PA-17 covers date-only values shifting across zones. PA-96
    covers a date as a range of about 49 hours. PA-36 covers missing
    local midnights. PA-125 covers the implicit date-to-instant
    conversions that layers perform, and how they disagree.
  - Why it is false:
    - A date is a calendar day in some zone, not an instant. Its start is
      midnight in that zone, which is UTC midnight only for UTC and +00:00
      zones (PA-96).
    - Layers convert dates differently. On a Los Angeles host (verified):
      - JS `new Date("2026-10-03")` gives `2026-10-03T00:00:00.000Z` (UTC
        midnight), and `toLocaleDateString` then shows `10/2/2026`.
      - JS `new Date("2026-10-03T00:00")` gives
        `2026-10-03T07:00:00.000Z` (local midnight).
      - Python `datetime.combine(date, time())` gives naive local midnight,
        whose timestamp is 07:00 UTC.
    - Other layers: HTML `<input type="date">` `valueAsDate` returns UTC
      midnight (PA-90). Postgres casts `date` to `timestamptz` at midnight
      in the session zone, not UTC. Serializers often write dates as UTC
      midnight timestamps (PA-17).
    - Some local midnights do not exist: in Santiago on 2026-09-06, the day
      starts at 01:00 (PA-36).
    - Many dates have meaning only as dates: birthdays, holidays, due
      dates, contract effective dates, and statutory deadlines that run to
      the end of a day in a jurisdiction.
  - How it appears in code:
    - Date-only values stored in timestamp columns as UTC midnight.
    - Dates compared with instants through implicit coercion.
    - Date values shown in negative-offset zones as the previous day.
    - Date ranges converted with UTC midnight boundaries for users in
      other zones.
  - What to check:
    - Types used for date-only values in every layer.
    - Implicit conversions between dates and instants.
  - Fix:
    - Keep dates as date types end to end: SQL `DATE`, Java `LocalDate`,
      ISO `YYYY-MM-DD` strings in JSON (PA-17, PA-96).
    - When an instant is needed, convert with an explicit zone to a
      half-open range `[start of day, start of next day)`, using the
      library's start-of-day operation (PA-36).
    - Make every layer use the same rule, and test from hosts and users in
      negative and positive offsets.
  - Not a finding:
    - UTC-midnight conversions where the requirement defines the day in
      UTC and says so.
  - Escalate (NEEDS-HUMAN): deadlines or effective dates whose governing
    zone is not stated.
  - Proposed severity (for the user to decide): HIGH when dates shift by a
    day on a core path (birth dates, due dates, effective dates,
    bookings). MEDIUM for display and reports. LOW for test-only code.
- PA-126: Customer-zone sufficiency assumption. Code assumes "the
  customer's time zone" is the right rule for every date and time
  decision.
  - Overlap: PA-17 escalates when "whose zone" is not stated. PA-99 covers
    contact-hour rules at the called party's location. PA-33 covers
    meetings anchored to an owner zone. PA-126 states the general rule:
    each decision has its own governing zone and calendar, and the
    customer's is only one of them.
  - Why it is false: different decisions are governed by different
    parties' time.
    - Courts and regulators: US federal court rules end an electronic-filing
      day at midnight in the court's time zone (FRCP 6(a)(4)(A)). Tax and
      regulatory deadlines follow the authority's rules.
    - Contracts: governing-law clauses and notice provisions can fix the
      zone, or make deadlines run to the recipient's local time.
    - Merchants and operations: store hours, same-day shipping cutoffs
      (the warehouse's zone), support hours, and maintenance windows.
    - Venues and events: start times are in the venue's zone, whatever
      the attendee's.
    - Markets and banks: trading hours and settlement follow the
      exchange's zone. Interest accrual and payment cutoffs follow the
      bank's.
    - Recipients: telemarketing hours follow the called party's location
      (PA-99).
    - Reporting: company reports use the reporting entity's zone or
      calendar, and logs use UTC (PA-10, PA-124).
    - Multi-party events: meetings anchor to the organizer's or an agreed
      zone (PA-33).
    - "The customer" may have several zones: profile, device, current
      location, billing address, and shipping address. Business accounts
      have users in many zones (PA-50, PA-89, PA-97).
    - Some rules are not about zones at all: business days, holidays,
      fiscal years, and calendar systems (PA-41, PA-58, PA-59, PA-123).
  - How it appears in code:
    - One `customer.timezone` field used for every decision.
    - Legal, contractual, or regulatory deadlines computed in the
      customer's zone where the governing rule names another.
    - Merchant cutoffs and venue times shown or enforced in the viewer's
      zone (PA-101).
  - What to check:
    - Each time-dependent decision, and which party's zone and calendar
      govern it.
    - Which zones the data model stores.
  - Fix:
    - Document a governing zone and calendar for each decision (a
      decision table reviewed with product and legal owners).
    - Store each relevant zone as an IANA ID: customer, account, merchant,
      venue, warehouse, jurisdiction.
    - Compute each rule in its own zone, and show users both the
      governing time and their own when they differ.
  - Not a finding:
    - Decisions documented as governed by the customer's zone.
  - Escalate (NEEDS-HUMAN): legal, contractual, or regulatory deadlines
    where the governing zone is not stated.
  - Proposed severity (for the user to decide): HIGH when legal,
    regulatory, financial, or contractual deadlines on a core path use the
    wrong party's zone. MEDIUM for operational cutoffs and display. LOW
    for test-only code.
- PA-127: Offset-equals-zone assumption. Code assumes a numeric UTC
  offset such as -05:00 is the same as a named zone such as
  America/Chicago.
  - Overlap: PA-9 covers offsets losing rules. PA-87 covers zones versus
    offsets. PA-89 covers inferring zones from offsets. PA-127 covers
    offsets and zone IDs as data types: what each can and cannot do in
    storage, arithmetic, and exchange. Merged per the class ledgers.
  - Why it is false (verified with tzdata 2026b and Java):
    - An offset is one value at one instant. A zone is a set of rules over
      time. America/Chicago is -06:00 in January and -05:00 in July.
    - Many zones share an offset at a given time. In January 2026, -05:00
      is New York, Bogota, Lima, Panama, and Cancun. In July it is
      Chicago, Bogota, Lima, Panama, and Cancun.
    - Arithmetic on offset-only values ignores DST. Java
      `OffsetDateTime.parse("2026-10-30T09:00-05:00").plusDays(5)` gives
      `2026-11-04T09:00-05:00`, which is 08:00 in Chicago. The zoned
      equivalent gives `2026-11-04T09:00-06:00[America/Chicago]`, still
      09:00 local.
    - Formats carry only offsets: RFC 3339 timestamps, most JSON dates,
      and Postgres `timestamptz` (which stores an instant and no zone at
      all). The zone is lost unless stored separately.
    - RFC 9557 (2024) extends RFC 3339 with a bracketed zone suffix, as in
      `2026-07-01T10:00-05:00[America/Chicago]`, which Java
      `ZonedDateTime` and the JS Temporal proposal use.
  - How it appears in code:
    - User or location zones stored as offsets (PA-9, PA-89).
    - Recurring events or future local times stored with a fixed offset
      (PA-9, PA-69).
    - Offset-only types (`OffsetDateTime`, Python `timezone(timedelta(...))`)
      used for local-time arithmetic.
    - Offsets mapped back to a zone by lookup (PA-89).
  - What to check:
    - Where zones are stored, and as what.
    - Arithmetic on offset-only types.
    - Whether interfaces carry a zone ID where local semantics matter.
  - Fix:
    - Store IANA zone IDs wherever local semantics matter, and keep
      offsets only to identify instants (PA-9).
    - Do local arithmetic with zoned types (`ZonedDateTime`, Luxon with a
      zone) (BP-1).
    - Exchange zone IDs with timestamps, for example in RFC 9557 format or
      as a separate field.
  - Not a finding:
    - Offsets used only to identify instants (logs, audit records,
      RFC 3339 exchange).
  - Escalate (NEEDS-HUMAN): interfaces where consumers need local
    semantics but receive only offsets.
  - Proposed severity (for the user to decide): HIGH when offset-only
    values drive future scheduling, recurrence, or deadlines on a core
    path. MEDIUM for display. LOW for test-only code.
- PA-128: Abbreviation identity assumption. Code assumes a zone
  abbreviation such as EST, CST, or IST reliably identifies one zone.
  - Overlap: PA-67 covers BST and IST collisions and Java short IDs.
    PA-66 covers GMT. PA-27 covers parsing abbreviations as input. PA-128
    collects abbreviation ambiguity and the behavior of common parsers.
    Merged per the class ledgers.
  - Why it is false (tzdata 2026b abbreviations for January and July,
    verified):
    - CST is US Central Standard Time (`America/Chicago`, -06:00), China
      Standard Time (`Asia/Shanghai`, +08:00), and Cuba Standard Time
      (`America/Havana`, -05:00).
    - IST is India Standard Time (`Asia/Kolkata`, +05:30), Israel Standard
      Time (`Asia/Jerusalem`, +02:00 in winter), and Irish Standard Time
      (`Europe/Dublin`, +01:00 in summer, when Dublin is not on GMT).
    - Abbreviations name a DST state, not a zone. New York is EST in winter
      and EDT in summer. People write "EST" all year, so "EST" in July
      text is usually an hour off.
    - Abbreviations change. Australian zones now use AEST and AEDT
      (`Australia/Sydney`), where tzdata once used EST. tzdata also
      replaced many invented abbreviations with numeric ones (for example
      `+06` for Dhaka) (PA-67).
  - Parsers disagree (verified):
    - JS `Date.parse` accepts US abbreviations: "CST" becomes -06:00 and
      "EST" -05:00. It returns `NaN` for "IST", "BST", and "AEST".
    - Python `strptime` with `%Z` accepts "UTC" and rejects "CST" and
      "IST".
    - Java `ZoneId.SHORT_IDS` maps "EST" to a fixed -05:00 with no DST,
      "MST" to -07:00, "HST" to -10:00, "CST" to `America/Chicago`, "IST" to
      `Asia/Kolkata`, and "BST" to `Asia/Dhaka`.
  - How it appears in code:
    - Abbreviations parsed from user input, emails, logs, or partner feeds
      and turned into offsets or zones (PA-27, PA-67).
    - Abbreviations stored as the zone identifier.
    - Java short IDs used for lookup, giving fixed offsets without DST.
    - Displays that print a stored abbreviation instead of computing it.
  - What to check:
    - Any parsing or storage of zone abbreviations.
    - Java `SHORT_IDS` or three-letter legacy IDs.
  - Fix:
    - Accept and store IANA zone IDs or numeric offsets, never
      abbreviations (PA-9, PA-127).
    - Generate abbreviations for display only, from the zone and instant,
      and pair them with the city or region where ambiguity matters.
    - Where input must contain abbreviations, resolve them with an
      explicit, context-specific table, and reject unknown or ambiguous
      ones.
  - Not a finding:
    - Abbreviations computed for display from a stored zone ID.
  - Escalate (NEEDS-HUMAN): inputs that supply only abbreviations, where
    the intended region cannot be established.
  - Proposed severity (for the user to decide): HIGH when parsed
    abbreviations shift stored times or deadlines on a core path. MEDIUM
    for display. LOW for test-only code.
- PA-129: Year-round fixed offset assumption. Code assumes a fixed offset
  such as UTC-5 stays correct all year for places that observe DST.
  - Overlap: PA-9 covers hardcoded offsets. PA-127 covers offsets versus
    zones as data types. PA-128 covers Java's fixed-offset short IDs.
    PA-129 covers the configuration and scheduling places where fixed
    offsets stand in for DST-observing zones. Merged per the class ledgers.
  - Why it is false (verified with `date` and tzdata 2026b):
    - DST-observing places change offset twice a year: New York is -05:00
      in winter and -04:00 in summer.
    - POSIX `TZ` strings without DST are fixed. `TZ=EST5` gives 07:00
      EST at 12:00 UTC in both January and July. `TZ=EST5EDT` and
      `TZ=America/New_York` give 08:00 EDT in July (verified). The
      `EST5EDT` form follows built-in rules, which a future rule change
      would not update, while the IANA ID would follow tz data (PA-35).
    - Schedules expressed in UTC drift in local time. A job at 14:00 UTC
      runs at 09:00 in New York in January and 10:00 in July (verified).
    - Fixed offsets appear in many places: Java short ID "EST" (PA-128),
      `Etc/GMT+5` (PA-66), database session settings, cloud scheduler
      expressions, calendar invites, and text such as "9am EST" written
      all year.
  - How it appears in code:
    - `TZ=EST5`, `TZ=UTC-5`-style settings, or fixed-offset zone objects
      in configuration.
    - Cron or cloud schedules in UTC meant to run at a local time
      (PA-54).
    - Offsets computed once and stored for users, sites, or events
      (PA-9, PA-89).
    - Documentation and UI text with year-round "EST" or "PST".
  - What to check:
    - Time zone settings in configuration, containers, databases, and
      schedulers.
    - Schedules meant to follow local time.
  - Fix:
    - Use IANA zone IDs in configuration (`TZ=America/New_York`) (PA-9).
    - Run local-time schedules with a scheduler that accepts a zone, or
      compute each run in the zone (PA-54).
    - Store zone IDs, not offsets, for users, sites, and events (PA-127).
    - Write "Eastern Time" or the zone ID in text, not a year-round "EST".
  - Not a finding:
    - Fixed offsets for places that do not observe DST, documented as such
      (for example Arizona outside the Navajo Nation, or Bogota).
  - Escalate (NEEDS-HUMAN): schedules or SLAs stated in a fixed offset
    where the intended local time is not stated.
  - Proposed severity (for the user to decide): HIGH when fixed offsets
    shift scheduled jobs, deadlines, or SLAs on a core path by an hour for
    half the year. MEDIUM for display and documentation. LOW for
    test-only code.
- PA-130: Universal numeric date assumption. Code assumes numeric dates
  such as 03/04/2026 mean the same thing everywhere.
  - Overlap: PA-27 and PA-32 cover locale formats and display strings.
    PA-83 covers two-digit years. PA-84 covers parsing mechanics. PA-130
    covers numeric field order specifically: how often it is ambiguous,
    and how parsers and databases resolve it. Merged per the class ledgers.
  - Why it is false:
    - Three orders are in everyday use: month-day-year (United States),
      day-month-year (most of the world), and year-month-day (East Asia,
      ISO 8601, and several European countries). Canada uses all three.
    - `03/04/2026` is March 4 in the US and April 3 in the UK. With a
      two-digit year, `03/04/26` adds 2026 versus 2003 and a third reading
      as year-month-day.
    - Ambiguity is common: whenever day and month are both 12 or less and
      differ, both readings are valid. That is 132 of each year's dates,
      about 36% (computed).
    - Separators do not settle it: dots, slashes, and hyphens each appear
      with more than one order.
    - Parsers and databases pick an order by default or by setting:
      - JS `Date` reads `03/04/2026` as March 4, and rejects `13/04/2026`
        as an invalid date (verified).
      - Python `dateutil` assumes month first unless `dayfirst=True`
        (PA-27).
      - SQL Server interprets such literals by `SET DATEFORMAT` or the
        session language. Postgres interprets them by its `DateStyle`
        setting.
      - Spreadsheets apply the system locale when opening CSV files.
  - How it appears in code:
    - CSV and spreadsheet imports, free-text form fields, and partner feeds
      with numeric dates and no declared order.
    - SQL literals in numeric formats that depend on session settings.
    - Validation that accepts any value that parses, so day-month swaps
      pass silently for 36% of dates.
  - What to check:
    - Every numeric date input: declared order, source locale, and parser
      settings.
    - Database date-style settings and literals in queries.
  - Fix:
    - Use ISO 8601 (`YYYY-MM-DD`) for all machine exchange and SQL
      literals (PA-27).
    - Use date pickers or separate fields for human input (PA-32).
    - Declare the order for each source and parse strictly with it.
    - When the order is unknown, reject values that are ambiguous (both
      fields 12 or less) rather than guess.
    - Set database date-style settings explicitly, or avoid relying on
      them.
  - Not a finding:
    - Numeric dates with a declared, enforced order from a single source.
  - Escalate (NEEDS-HUMAN): imported data with numeric dates whose source
    order cannot be established.
  - Proposed severity (for the user to decide): HIGH when day-month swaps
    store wrong dates on a core path (contracts, medical records,
    payments). MEDIUM for analytics imports. LOW for test-only code.
- PA-131: Zero-offset equivalence assumption. Code assumes the RFC 3339
  offsets `-00:00`, `Z`, and `+00:00` mean exactly the same thing.
  - Overlap: PA-27 and PA-28 cover offset spellings as format variants.
    PA-89 covers inferring a user's zone from an offset. PA-131 covers the
    meaning the standards assign to each zero offset, and the information
    lost when parsers merge them.
  - Why it is false:
    - All three identify the same instant, but they do not say the same
      thing about local time.
    - RFC 3339 section 4.3 defines `-00:00` as "unknown local offset": the
      time is known in UTC, but the local offset is not. `+00:00` says UTC
      is the local reference point.
    - RFC 9557 (2024) updated RFC 3339 so that `Z` carries the same
      meaning as `-00:00`: UTC time known, local offset unknown.
    - Email follows the same idea. RFC 5322 defines `-0000` as a time from
      a system whose local zone may not be UTC and is not stated.
    - ISO 8601 does not permit a negative zero offset, so strict ISO
      parsers may reject `-00:00`.
    - Common parsers merge all three (verified): Python `fromisoformat`
      turns `Z`, `+00:00`, and `-00:00` into the same `+00:00` UTC value,
      JS `Date` outputs `Z` for each, and Java `OffsetDateTime.parse`
      normalizes `-00:00` and `+00:00` to `Z`. The "unknown local offset"
      meaning is lost after parsing.
  - How it appears in code:
    - Treating a `Z` timestamp as evidence that the user or source is in
      UTC, and deriving local dates or zones from it (PA-17, PA-89).
    - Serializing every UTC value as `+00:00` or `Z` without considering
      what the receiver will infer about local time.
    - Discarding `-00:00` meaning on parse when the local offset matters
      later (email, audit, legal records).
    - Strict parsers rejecting `-00:00` from systems that use it.
  - What to check:
    - Whether any logic infers local time from a zero offset.
    - How zero offsets are produced and parsed at each interface.
  - Fix:
    - Treat a zero offset as identifying the instant only. Get local time
      from a stored zone ID, never from the offset (PA-17, PA-127).
    - Where "local offset unknown" matters, keep it as explicit data
      rather than relying on the offset spelling.
    - Accept `-00:00` at input where sources use it, and document how it
      is handled.
  - Not a finding:
    - Zero-offset timestamps used only as instants, with local context
      stored separately.
  - Escalate (NEEDS-HUMAN): records (email, audit, legal) where the
    original local offset matters and the source used `-00:00` or `Z`.
  - Proposed severity (for the user to decide): HIGH when local dates or
    deadlines on a core path are derived from a zero offset as if it were
    the user's zone. MEDIUM for lost provenance in records. LOW for
    test-only code.
- PA-132: Uniform `timestamp` type assumption. Code assumes a database
  field typed `timestamp` means the same thing across database products
  and drivers.
  - Overlap: PA-10 covers MySQL `TIMESTAMP` session conversion. PA-18
    covers ranges. PA-23 and PA-29 cover precision. PA-90 covers driver
    conversions. PA-132 catalogs what the type name means in each product,
    including types that are not times at all.
  - Why it is false:
    - SQL standard: `TIMESTAMP` means `TIMESTAMP WITHOUT TIME ZONE`, a
      zone-less local value. `TIMESTAMP WITH TIME ZONE` is a separate
      type.
    - Postgres: `timestamp` has no zone and no conversion. `timestamptz`
      stores an instant and keeps no zone or offset (PA-127).
    - MySQL: `TIMESTAMP` converts through the session zone, covers only
      1970 to 2038 (PA-18), and on older defaults the first `TIMESTAMP`
      column in a table updates itself whenever the row changes (changed
      by `explicit_defaults_for_timestamp`, on by default since 8.0.2).
      `DATETIME` is the zone-less type.
    - SQL Server: `timestamp` is a synonym for `rowversion`, a binary row
      version counter that holds no date or time at all. Date types are
      `datetime`, `datetime2`, and `datetimeoffset`.
    - Oracle: `TIMESTAMP` has no zone. `TIMESTAMP WITH TIME ZONE` stores a
      region or offset. `TIMESTAMP WITH LOCAL TIME ZONE` normalizes to the
      database zone and displays in the session zone. Oracle's `DATE` also
      holds a time of day to the second.
    - SQLite: there is no date type. A column declared `timestamp` stores
      whatever it receives: on this host it held the text
      `2026-10-04 12:00`, the integer 1791110400, and the text `not a date`
      side by side (verified). `CURRENT_TIMESTAMP` returns UTC text.
    - Warehouses and formats: BigQuery `TIMESTAMP` is an instant and
      `DATETIME` is zone-less. Snowflake maps `TIMESTAMP` to
      `TIMESTAMP_NTZ` (no zone) by default through a setting. Spark
      `TIMESTAMP` behaves as an instant in the session zone, with
      `TIMESTAMP_NTZ` added later. Parquet and Avro distinguish
      UTC-adjusted from local timestamps, and legacy Parquet `INT96`
      timestamps are read differently by different engines.
    - Drivers map each type differently: JDBC `java.sql.Timestamp` uses
      the JVM zone (PA-90), and Python `psycopg` returns aware values for
      `timestamptz` and naive values for `timestamp`.
  - How it appears in code:
    - Schemas or migrations ported between products by type name.
    - SQL Server `timestamp` columns treated as dates.
    - MySQL `TIMESTAMP` columns changing on unrelated updates (PA-31).
    - Data pipelines moving timestamps between warehouses, Parquet, and
      Avro without checking UTC-adjusted versus local semantics.
    - SQLite timestamp columns with mixed types.
  - What to check:
    - The actual type and semantics in each database and file format, not
      the name.
    - Driver mappings and session settings (PA-90).
    - Migration scripts between products.
  - Fix:
    - Choose types by semantics: instant types for instants
      (`timestamptz`, BigQuery `TIMESTAMP`, `datetimeoffset`), zone-less
      types for local values, and date types for dates (PA-96, PA-125).
    - Document each column's meaning and zone policy in the schema.
    - Map types explicitly in migrations and pipelines, and test round
      trips across products.
    - In SQLite, store one documented representation (ISO 8601 UTC text or
      integer epoch with a unit) and enforce it with checks.
  - Not a finding:
    - Columns whose product-specific semantics are documented and match
      their use.
  - Escalate (NEEDS-HUMAN): migrations between database products where
    timestamp semantics have not been mapped.
  - Proposed severity (for the user to decide): HIGH when type-name
    assumptions shift, corrupt, or misinterpret stored times on a core
    path, or a row version is used as a time. MEDIUM for analytics
    pipelines. LOW for test-only code.
- PA-133: Automatic reanchoring assumption. Code assumes every future
  local commitment should move to keep its local time when a zone's rules
  change.
  - Overlap: PA-9 recommends storing future local events as local time
    plus zone so rule changes apply, and exempts fixed-instant events.
    PA-34 covers recomputing stored conversions. PA-126 covers which
    party's zone governs. PA-133 states that each commitment has an
    anchor, and only some anchors follow local time.
  - Why it is false: commitments are anchored differently.
    - Local wall time in one zone: a dentist appointment at 09:00 in the
      clinic's zone should stay at 09:00 local, so its instant moves.
    - A fixed instant: a global product launch, a live broadcast, a
      satellite pass, or a market-wide event happens at one instant,
      whatever local rules do (PA-9).
    - Another party's zone: a meeting anchored to the organizer's zone
      keeps the organizer's local time, so other attendees' local times
      move (PA-33, PA-126). With participants in several zones, only one
      local time can stay fixed.
    - A duration from an event: "24 hours after purchase" is elapsed time
      and does not follow local rules (PA-1, PA-44).
    - A jurisdiction's rule: legal deadlines follow the governing law,
      which may fix the zone or the instant (PA-126).
    - An astronomical event: sunset-based times follow the sun, not the
      clock (PA-57).
    - iCalendar distinguishes these: a `DTSTART` with a `TZID` is anchored
      to local time, and a UTC value ending in `Z` is anchored to an
      instant (RFC 5545).
    - A rule change can make a stored local time nonexistent or
      ambiguous (PA-1, PA-92).
  - How it appears in code:
    - All future events stored as local time plus zone and recomputed
      after every tz data update, moving instant-anchored events.
    - All future events stored as UTC, so none follow local rules
      (PA-9).
    - Recomputation without notifying participants of changed times.
    - No handling for recomputed times that fall in a gap or overlap.
  - What to check:
    - Whether each commitment type declares its anchor.
    - What runs after a tz data update, and what it changes (PA-35).
  - Fix:
    - Model the anchor explicitly per commitment: local wall time plus
      zone, fixed instant, other party's zone, elapsed duration,
      jurisdiction rule, or astronomical event.
    - After a tz data update, recompute only commitments whose anchor
      depends on the changed zone, apply the gap and overlap policy
      (PA-92), and keep the previous values for audit.
    - Notify affected participants with old and new times in their own
      zones.
  - Not a finding:
    - Commitment models with explicit anchors and a tested rule-change
      process.
  - Escalate (NEEDS-HUMAN): commitment types whose anchor is not stated,
    especially multi-zone meetings and legal deadlines.
  - Proposed severity (for the user to decide): HIGH when rule changes
    silently move or fail to move appointments, broadcasts, or deadlines
    on a core path. MEDIUM for missing notifications. LOW for test-only
    code.
- PA-134: Date-and-clock-time completeness assumption. Teams assume a
  time-sensitive requirement is complete once it gives a date and a clock
  time.
  - Overlap: many items end in an escalation for an unstated rule. PA-96
    lists what identifies an instant. PA-134 collects the questions a
    time-sensitive requirement must answer, so reviewers can check
    requirements, tickets, and API specifications, not only code.
  - Why it is false: a date and clock time leave most decisions open.
    For example, "the offer expires 2026-11-01 01:30" in New York names a
    local time that happens twice that night, at -04:00 and then at -05:00
    (PA-1, PA-92, verified for that date).
  - What a complete time-sensitive requirement states:
    - Governing zone and party: whose clock decides (customer, merchant,
      venue, court, regulator) (PA-126), and the calendar system (PA-41).
    - Anchor: local wall time, fixed instant, another party's zone,
      elapsed duration, legal rule, or astronomical event (PA-133).
    - Boundary: inclusive or exclusive, the precision compared, what
      "midnight" or "end of day" means (PA-57, PA-112), and rounding
      (PA-81, PA-82).
    - Event: which moment counts, such as created, sent, received, or
      processed (PA-31).
    - Durations: elapsed time or calendar periods (PA-1, PA-44, PA-69),
      business days and which holiday calendar (PA-58, PA-59), and
      month-end and February 29 policies (PA-2, PA-3).
    - Skipped and repeated local times, and skipped or repeated dates
      (PA-40, PA-92).
    - Recurrence rules, if any (PA-2, PA-36).
    - Clock authority and tolerance: server or client clock, accepted
      skew, and required accuracy (PA-14, PA-46).
    - Display: what users see, in which zone, and labeled how (PA-17,
      PA-73).
    - Change handling: zone-rule changes, travel, and corrections
      (PA-50, PA-133).
  - How it appears in work products:
    - Tickets, specifications, or contracts with "due 2026-10-10 17:00"
      and nothing more.
    - API fields documented only as "date-time".
    - Tests written from the same incomplete specification, so they pass
      whatever the code assumes.
  - What to check:
    - Requirements, acceptance criteria, API documentation, and test
      names for each point above.
  - Fix:
    - Use the checklist above as a requirements template for
      time-sensitive features.
    - Record each answer next to the code that implements it, and test
      each one.
    - When an answer is missing, escalate rather than infer (the review
      itself follows this rule).
  - Not a finding:
    - Requirements that answer every applicable point, or state that a
      point does not apply.
  - Escalate (NEEDS-HUMAN): any time-sensitive requirement missing a
    governing zone, anchor, boundary rule, or duration semantics.
  - Proposed severity (for the user to decide): HIGH when a legal,
    financial, safety, or contractual deadline is implemented from an
    incomplete requirement. MEDIUM for other features. LOW for internal
    tooling.
- PA-135: 23:59:59 end-of-day assumption. Code assumes 23:59:59 is a safe,
  universal way to represent the end of a day.
  - Overlap: PA-10 and PA-29 recommend half-open ranges and note closed
    ranges missing fractions. PA-57 covers day boundaries that are not
    midnight. PA-112 covers "midnight" deadlines. PA-135 covers the
    23:59:59 sentinel itself and every way it fails.
  - Why it is false:
    - Time continues after 23:59:59. Values such as 23:59:59.5 fall after
      it and before midnight, so a closed range ending at 23:59:59 misses
      them (PA-29).
    - Adding fractions only moves the gap: 23:59:59.999 misses
      23:59:59.9995 in microsecond or nanosecond systems, and a value
      written at higher precision can round up to the next day on storage
      (PA-23, PA-81).
    - A leap second, 23:59:60, comes after 23:59:59 (PA-64).
    - 23:59:59 can happen twice. In Santiago, the clocks go back at
      midnight on 2026-04-04, so 23:59:59 occurs at -03:00 and again at
      -04:00, an hour apart (verified).
    - Days differ in length and may be skipped altogether (PA-1, PA-40),
      so "end of day" is not a fixed clock time in every zone.
    - "End of day" in business or law may mean close of business, such as
      17:00, rather than midnight (PA-57).
    - Spreadsheets approximate end of day as a fraction (date plus 0.99999),
      with similar gaps.
  - How it appears in code:
    - Ranges such as `BETWEEN '2026-10-03 00:00:00' AND '2026-10-03
      23:59:59'`.
    - Deadlines stored as 23:59:59 or 23:59:59.999 and compared with `<=`.
    - Date-only values converted to "end of day" timestamps for
      comparison.
  - What to check:
    - Literal 23:59:59, 23:59:59.999, or 0.99999 near date logic.
    - Closed ranges on timestamps.
  - Fix:
    - Use half-open ranges: `>= start of day AND < start of next day`, with
      both starts computed by the library in the governing zone (PA-36,
      PA-125).
    - Express deadlines as an exclusive instant (the first moment after
      the deadline) and compare at full precision.
    - State what "end of day" means in the requirement (PA-134).
  - Not a finding:
    - 23:59:59 shown to users as a display convention, with a half-open
      comparison behind it.
  - Escalate (NEEDS-HUMAN): "end of day" deadlines whose zone or business
    meaning is not stated.
  - Proposed severity (for the user to decide): HIGH when closed
    end-of-day ranges drop records, or deadlines accept or reject the wrong
    submissions, on a core path. MEDIUM for reports. LOW for test-only
    code.
- PA-136: Uptime-only monitoring assumption. Teams assume monitoring
  uptime is enough, even when they cannot detect clock drift, stale zone
  data, skipped or duplicated jobs, or time-parsing failures.
  - Overlap: many items recommend monitoring as part of their fix (PA-11,
    PA-12, PA-35, PA-54, PA-104, PA-122). PA-136 collects time-related
    observability into one requirement, because these failures leave
    services "up".
  - Why it is false: time failures are usually silent.
    - Drifting or stepped clocks keep serving requests while timestamps,
      tokens, leases, and ordering go wrong (PA-11 to PA-13).
    - Stale tz data or leap-second lists produce wrong local times with no
      errors (PA-35, PA-104).
    - Scheduled jobs that skip or run twice on DST days, after clock
      jumps, or after outages raise no alarms (PA-12, PA-54).
    - Parsing failures and dropped records look like quiet days (PA-28).
    - Out-of-range client clocks, future-dated records, negative
      durations, and out-of-order timestamps corrupt data without
      failing requests (PA-15, PA-65, PA-68).
    - Expiring certificates and tokens fail at a known future time
      (PA-116).
  - What to monitor:
    - Clock offset, sync status, and estimated error on every host, with
      alerts. For example, Prometheus node_exporter exposes
      `node_timex_offset_seconds` and `node_timex_sync_status`.
    - Loss of synchronization and time in holdover (PA-122).
    - tz data version in every layer, its age, and unapplied IANA
      releases. Leap-second list expiry (PA-35, PA-104).
    - Scheduled jobs: expected versus actual runs per window, late runs,
      and duplicates, using check-in ("heartbeat" or "dead man's switch")
      monitoring and run IDs (PA-54).
    - Rates of parse failures, rejected timestamps, implausible or
      future-dated values, negative durations, and monotonicity violations
      (PA-12, PA-28, PA-65, PA-68).
    - Distribution of client clock skew (PA-15).
    - Sync watermark lag (PA-65).
    - Certificate and token expiry dates (PA-116).
    - Synthetic checks around DST transitions, month-ends, and year-ends
      (PA-95).
  - How it appears in code and operations:
    - Health checks that only return HTTP 200.
    - Cron jobs with no run tracking.
    - Parse errors swallowed or logged without metrics (PA-28).
    - No metrics on clock offset or skew.
  - What to check:
    - Monitoring coverage for each item above that applies to the system.
  - Fix:
    - Add the metrics and alerts above, with owners and runbooks.
    - Log in UTC with offsets so events correlate across hosts (PA-10).
  - Not a finding:
    - Systems with documented time-health monitoring appropriate to their
      risk.
  - Escalate (NEEDS-HUMAN): systems with time-critical behavior whose
    monitoring is outside the review unit.
  - Proposed severity (for the user to decide): HIGH when skipped or
    duplicated jobs, clock drift, or parse failures on a core path
    (billing, expiry, compliance) would go undetected. MEDIUM for other
    gaps. LOW for internal tooling.

- PA-137: Time-sync guarantee assumption. Teams assume relying on the
  system's time synchronization always yields the correct current date.
  - Overlap: PA-11 and PA-12 list clock errors and mention running sync
    as part of the fix. PA-137 covers why sync itself is not a guarantee,
    and code that relies on it without checking. Merged per the class
    ledgers (destination C27.1, the time synchronization class).
  - Why it is false:
    - Sync may not run at all. This cloud container has no sync daemon
      and no chrony or timesyncd configuration, `timedatectl` cannot
      query it, and the kernel's `adjtimex` reports `TIME_ERROR` with
      `STA_UNSYNC` and a maximum error of 16 s (the kernel's cap value)
      (verified). Containers cannot set the clock; they inherit the
      host's, right or wrong. Users and administrators disable automatic
      time.
    - Sync may be unreachable: offline and air-gapped devices, firewalls
      blocking UDP 123, captive portals, ships and aircraft, and devices
      whose HTTPS time fetch fails because the wrong clock breaks TLS
      certificate validation (PA-12).
    - Sync takes time: it completes some time after boot or resume, so
      early events carry the unsynced time (PA-11).
    - Sync may refuse or crawl: ntpd exits beyond its 1,000 s panic
      threshold unless started with `-g`, and chrony slews large offsets
      slowly unless `makestep` applies (PA-12).
    - Sources can be wrong: a misconfigured or faulty server, a pool
      member serving bad time, mixed smeared and unsmeared sources
      (PA-20), or a GPS receiver after a week rollover or spoofing.
    - Plain NTP is unauthenticated, so an on-path attacker can shift a
      client's clock. Authenticated NTP (NTS, RFC 8915) exists but is not
      the default in most setups.
    - Accuracy has limits: asymmetric network paths bias the offset
      estimate, and a synced clock still carries an error bound that the
      requirement may exceed (PA-13, PA-46).
    - The protocol has its own range: NTP's 32-bit era rolls over on
      2036-02-07 (PA-18).
    - Sync gives UTC, not the date. The local date also needs the right
      zone and current tz data (PA-8, PA-9, PA-35).
  - How it appears in code and operations:
    - Code or runbooks that treat "the host runs NTP" as proof the clock
      is right, with no check of sync status.
    - Security or expiry decisions on devices that may never sync.
    - Applications implementing their own SNTP query (raw UDP 123, or an
      NTP client library) and trusting a single unauthenticated reply.
    - Container images or pods granted `CAP_SYS_TIME`, or running a sync
      daemon, in the belief that the container controls its own clock.
    - Sync configuration with one server, no `makestep` or `-g`, and no
      NTS where the threat model needs authentication.
    - No monitoring of offset or sync state (PA-136).
  - What to check:
    - Whether code that depends on correct time checks sync status
      (`adjtimex` status, `timedatectl show` `NTPSynchronized`, `chronyc
      tracking`) or a plausibility bound (PA-12).
    - Sync configuration and daemon presence, where in scope.
    - Hand-rolled time queries.
  - Fix:
    - Treat sync as best effort: check sync state and estimated error
      where correctness depends on time, and apply plausibility bounds
      (PA-12).
    - Use several sources, step large offsets at startup, and use NTS
      where spoofing matters.
    - Keep authoritative time on servers whose sync is monitored
      (PA-14, PA-136).
    - Use the platform's sync service instead of hand-rolled queries
      (BP-1). Adding an NTP client library needs user approval.
    - Leave clock setting to the host; containers should not need
      `CAP_SYS_TIME`.
  - Not a finding:
    - Display-only use of device time.
    - Systems that check and act on sync status, with monitored sync.
  - Escalate (NEEDS-HUMAN): security, billing, or regulated timing on
    devices or hosts whose sync arrangement cannot be established from
    the review unit.
  - Proposed severity (for the user to decide): CRITICAL when
    authorization, token validity, or payment relies on an unchecked,
    unauthenticated, or possibly absent sync on a client-controlled or
    attacker-reachable path. HIGH when expiry, retention, or scheduling on
    a core path assumes sync without checking. MEDIUM for missing
    monitoring and weak sync configuration. LOW for test-only code.

- PA-138: Uniform time-sync assumption. Teams assume time
  synchronization behaves the same on every operating system and device
  (Windows, macOS, Linux, and others).
  - Overlap: PA-137 covers sync as best effort in general. PA-138 covers
    differences between platforms and environments. Merged per the class
    ledgers (destination C27.6).
  - Why it is false (documented behavior unless marked verified; Windows,
    macOS, and mobile facts are not verified on this Linux host):
    - Different services and protocols:
      - Windows: the Windows Time service (W32Time). Domain members follow
        the Active Directory hierarchy (NT5DS) up to the PDC emulator;
        standalone machines use NTP with `time.windows.com` by default.
        W32Time was long designed for Kerberos tolerance (5 minutes by
        default) rather than high accuracy; Microsoft documents much
        tighter accuracy only on newer versions and under specific
        configuration. Polling intervals and limits on how far it will
        correct (`MaxPosPhaseCorrection`, `MaxNegPhaseCorrection`) are
        registry settings that differ by version and domain role. Windows
        keeps the hardware clock in local time by default (PA-11).
      - macOS: the `timed` daemon replaced `ntpd` in macOS 10.14, with
        `time.apple.com` by default and `sntp` as the command-line client.
      - Linux: several clients with different behavior: systemd-timesyncd
        (an SNTP client only), chrony (default on RHEL and Fedora), ntpd or
        NTPsec, and OpenNTPD. ntpd steps offsets above 128 ms and slews
        smaller ones; chrony steps only under `makestep` (PA-137).
      - Android and iOS: "set automatically" combines network sources such
        as carrier NITZ with NTP, and users can turn it off. Carrier NITZ
        can be wrong or absent.
      - Embedded and IoT: SNTP in firmware, often no battery-backed clock,
        possibly no sync until a network appears, or never (PA-12).
    - Virtualization and cloud add their own layers: hypervisor time
      integration (Hyper-V integration services, VMware Tools, KVM
      `kvm-clock` or `ptp_kvm`) and cloud time services (AWS Time Sync
      at 169.254.169.123, Google's metadata server, Azure host time),
      several of which smear leap seconds (PA-20). This guest offers
      `tsc` and `kvm-clock` clock sources and uses `tsc`, with no PTP
      device (verified). Containers and Kubernetes pods share the node
      clock (PA-137). WSL2 guests have drifted after host sleep (reported
      by users and Microsoft issue trackers; not verified here).
    - Sync state is queried differently and sometimes not at all:
      Linux `adjtimex`/`ntp_adjtime` and `timedatectl show`, `chronyc
      tracking`, `ntpq -p`; Windows `w32tm /query /status`; macOS has no
      equivalent standard status command for `timed`. Browsers expose no
      sync state at all, so JS cannot tell whether the device clock is
      synced. Language runtimes (Python `time.get_clock_info`) report clock
      properties, not sync state.
    - Correction behavior differs: step versus slew thresholds, maximum
      slew rates, refusal limits on large offsets, and leap-second
      handling (kernel insertion, smearing, or Windows' own leap-second
      support on newer versions) (PA-20, PA-46).
    - Permissions differ: setting time needs administrator or
      `CAP_SYS_TIME`; sandboxed apps and containers cannot.
  - How it appears in code and operations:
    - One sync check written for one platform (for example parsing
      `timedatectl` output) and assumed everywhere, failing or reporting
      wrongly on Windows, macOS, containers, or mobile.
    - Scripts calling platform-specific tools (`w32tm`, `sntp`,
      `ntpdate`, `timedatectl`, `hwclock`) without platform checks, or
      deprecated tools (`ntpdate`).
    - Accuracy assumptions taken from one platform's sync and applied to
      all (for example sub-second skew assumed on Windows clients or
      mobile devices).
    - Code that tries to set the clock from an app, needing privileges it
      will not have.
    - Cross-platform clients that assume the device is synced because the
      server is.
  - What to check:
    - Platform-specific time or sync commands and APIs, and whether other
      platforms are handled.
    - Accuracy or skew assumptions per platform the product supports.
    - How sync state is determined on each supported platform.
  - Fix:
    - List the supported platforms and, for each, its sync mechanism,
      expected accuracy, and how to read sync state (or that it cannot be
      read).
    - Where sync state cannot be read (browsers, many mobile apps), treat
      device time as untrusted and use server time (PA-14, PA-103).
    - Isolate platform-specific sync checks behind one interface with a
      defined "unknown" result.
    - Never set the clock from application code; leave it to the platform.
  - Not a finding:
    - Single-platform tools that document their platform.
    - Server-authoritative designs that do not depend on client sync.
  - Escalate (NEEDS-HUMAN): products spanning several platforms whose
    accuracy requirement and per-platform sync assumptions are not stated.
  - Proposed severity (for the user to decide): HIGH when a security,
    billing, or deadline decision on a core path assumes another
    platform's sync behavior or accuracy. MEDIUM for platform-specific
    scripts and monitoring gaps. LOW for test-only code.

- PA-139: Public pool authority assumption. Teams assume default public
  NTP pool sources are fit to serve as authoritative time, rather than a
  set of anonymous volunteer servers that may themselves be poorly
  synced and syncing from one another.
  - Overlap: PA-137 covers sync as best effort and unauthenticated NTP.
    PA-138 covers platform defaults. PA-139 covers the choice and quality
    of time sources, and where authoritative or traceable time is
    required. Merged per the class ledgers (destination C27.7).
  - Why it is false (documented unless marked verified):
    - The NTP Pool (`pool.ntp.org`) is a volunteer project. DNS hands out
      a rotating set of servers run by unknown operators, and a client
      cannot tell who runs the server it got. On this host,
      `pool.ntp.org` resolved to four addresses, none of which answered on
      UDP 123 (verified), so a client here would get no time at all.
    - The pool monitors members and drops servers whose score falls
      after detected bad time, but detection is after the fact, so
      clients can receive bad time until a server is removed.
    - Pool servers are often stratum 2 or lower, syncing from upstreams
      that may themselves be pool members, so errors propagate through
      chains of servers with no traceability.
    - There is no authentication by default (no NTS), no service level,
      and no traceability to UTC from a national laboratory (UTC(k), such
      as NIST, PTB, or NPL). Regulations that require traceable time (for
      example EU MiFID II RTS 25 for trading timestamps) are not met by
      "we use the pool".
    - Reputable-looking sources can also be wrong: in November 2012 US
      Naval Observatory NTP servers briefly served time about 12 years in
      the past (reported incident; not verified here).
    - Default sources are often hardcoded vendor zones or, worse, fixed IP
      addresses: Netgear routers hardcoded a University of Wisconsin
      server in 2003 and flooded it (documented incident). The pool asks
      vendors to register their own vendor zones and never to hardcode
      pool IPs.
    - Mixing sources with different leap policies (smeared cloud
      services with unsmeared pool servers) gives clocks that disagree
      during a smear (C27.4).
  - How it appears in code and operations:
    - Sync configurations using only `pool.ntp.org` (or a distribution
      default) for systems that issue authoritative timestamps: audit
      trails, trading, legal records, token issuers, certificate
      authorities, or time services for other systems.
    - Hardcoded NTP server IP addresses in code, firmware, or images.
    - Products shipping with the generic pool instead of a registered
      vendor zone.
    - Applications querying one pool server directly and trusting the
      reply (PA-137).
    - Claims of "accurate" or "traceable" time with no stated source or
      accuracy.
  - What to check:
    - Configured time sources (`server`, `pool` lines, cloud metadata
      sources, Windows `NtpServer`) and who operates them.
    - Whether any component issues authoritative or regulated timestamps,
      and what source and accuracy it states.
    - Hardcoded server names or IP addresses.
  - Fix:
    - For authoritative, regulated, or security-relevant time, use
      sources with known operators and stated accuracy: a cloud
      provider's time service with documented behavior, national
      laboratory services, authenticated NTS servers from known operators,
      or local GPS- or PTP-disciplined servers; document traceability to
      UTC where required.
    - Use several independent sources so a bad one can be outvoted, with
      one leap policy (C27.4).
    - Ship a registered vendor zone instead of the generic pool, and never
      hardcode server IP addresses.
    - Monitor offset against more than one reference (C26.3).
  - Not a finding:
    - Ordinary clients and servers using the pool or distribution
      defaults where no authoritative or regulated timestamps are issued.
  - Escalate (NEEDS-HUMAN): systems issuing authoritative, legal, or
    regulated timestamps whose time source, accuracy, and traceability are
    not stated.
  - Proposed severity (for the user to decide): HIGH when authoritative,
    regulated, or security-relevant timestamps rest on unauthenticated,
    unmonitored public pool sources or a single source, or when firmware
    hardcodes server IPs. MEDIUM for products shipping the generic pool
    instead of a vendor zone, and missing source documentation. LOW for
    test-only code.

- PA-140: Accurate-server assumption. Teams assume an NTP server always
  serves accurate time, so its reply can be taken as the correct time.
  - Overlap: PA-139 covers which sources to choose. PA-137 covers sync as
    best effort. PA-13 covers offset estimation and round-trip error.
    PA-140 covers the reply itself: what it does and does not promise,
    the fields that say how good it is, and servers that serve bad time.
    Merged per the class ledgers (destination C27.8).
  - Why it is false (protocol facts from RFC 5905 and RFC 4330 unless
    marked; UDP 123 is blocked from this host, so no live reply could be
    inspected):
    - A reply is a measurement, not a guarantee. The server reports how
      good its own time is: stratum, leap indicator, root delay, root
      dispersion, and the reference timestamp (when it last synced). The
      maximum error is bounded by the root distance (about half the root
      delay plus the root dispersion) plus the client's own path error.
    - The server may not be synchronized at all: leap indicator 3 means
      "alarm, clock not synchronized", stratum 16 means unsynchronized,
      and stratum 0 replies are Kiss-o'-Death packets (for example `RATE`
      or `DENY`), not time.
    - Servers serve their own free-running clock: ntpd's undisciplined
      local clock driver (`server 127.127.1.0` with a fudged stratum),
      chrony's `local` directive, orphan mode, or a Windows domain
      controller announcing itself reliable with no external source. They
      keep answering with confident-looking strata while drifting.
    - The reference timestamp can be old: the server may have lost its
      upstream hours or days ago and still answer.
    - Upstream failures pass through: GPS receivers after week rollovers
      served time about 20 years off (PA-12), and leap-second announcements
      have been mishandled and propagated.
    - Path asymmetry limits accuracy: the offset error can be up to half
      the round-trip time, which on the public internet can be tens of
      milliseconds or more (PA-13).
    - Accurate is not the same as correct for the purpose: a server can be
      precise and consistently biased, or smeared during a leap second
      (C27.4).
    - Replies can be forged without authentication (PA-137). Plain SNTP
      clients that skip the origin-timestamp check accept off-path forged
      replies.
  - How it appears in code and operations:
    - Hand-written SNTP clients that read only the transmit timestamp and
      ignore leap indicator, stratum, root delay, root dispersion,
      reference timestamp, and Kiss-o'-Death codes.
    - No round-trip compensation, so the result is off by the path delay.
    - No check that the reply's origin timestamp matches the request.
    - Clients accepting the first reply from one server (PA-137).
    - Servers configured with an undisciplined local clock (`127.127.1.0`,
      chrony `local`) serving others, or domain controllers with no
      external source.
    - Accuracy claims ("synced to NTP, so accurate to 1 ms") with no
      measured error bound.
  - What to check:
    - Custom NTP or SNTP code: which reply fields it reads and validates.
    - Server configurations that serve time: local-clock fallbacks and
      upstream sources.
    - Stated accuracy versus what the sources and paths can deliver.
  - Fix:
    - Use the platform sync service or a maintained client that validates
      replies (BP-1; new client libraries need approval).
    - If a custom client is unavoidable, reject replies with leap
      indicator 3, stratum 0 or 16, a stale reference timestamp, or a
      mismatched origin timestamp; honor Kiss-o'-Death; compensate round
      trip; and keep the error bound (root distance plus half the round
      trip).
    - Query several servers and discard outliers (PA-139).
    - Serve time only from servers disciplined by real references, and
      alarm when a server falls back to its local clock.
    - State accuracy as a measured bound, not as "uses NTP".
  - Not a finding:
    - Platform sync services with validated configurations, where only
      ordinary accuracy is needed.
  - Escalate (NEEDS-HUMAN): systems whose accuracy requirement is stated
    but whose achieved error bound is not measured or reported.
  - Proposed severity (for the user to decide): CRITICAL when
    authoritative, regulated, or security-relevant time accepts replies
    without validating synchronization status or origin. HIGH for custom
    clients that ignore reply quality fields on a core path, and for
    servers serving an undisciplined local clock to other systems.
    MEDIUM for unmeasured accuracy claims. LOW for test-only code.

- PA-141: Government-stratum assumption. Teams assume government time
  servers always give them stratum 0 or stratum 1 sources, and that this
  makes their time authoritative.
  - Overlap: PA-139 covers source choice and traceability. PA-140 covers
    reply quality fields. PA-141 covers what stratum means, what
    government and national services actually offer, and why stratum is
    not accuracy. Merged per the class ledgers (destination C27.9).
  - Why it is false (RFC 5905 and published service documentation unless
    marked; names below resolved from this host but UDP 123 is blocked,
    so no reply was inspected):
    - No NTP server serves stratum 0. Stratum 0 names the reference clock
      itself (atomic clock, GPS receiver), which is wired to a server; in
      an NTP packet, stratum 0 means "unspecified", used for Kiss-o'-Death
      replies (PA-140). The best a network client can get is stratum 1.
    - "Government" is not "national metrology institute". National
      laboratories that maintain UTC(k) (NIST, PTB, NPL, NRC, and others)
      run stratum 1 services; other agencies run ordinary stratum 2 or
      lower servers, and many countries offer no public national service.
      Military services (such as the US Naval Observatory) have their own
      history of serving bad time (PA-139).
    - Names hide many servers: `time.nist.gov` is a rotating name over
      servers at several sites; this host resolved it to one address and
      a site-specific name to another (verified resolution). A client may
      reach a distant or overloaded server.
    - Services set rules: NIST asks clients not to query any server more
      often than about once every 4 seconds and may refuse or rate-limit
      those that do; public NIST time is unauthenticated unless a client
      registers for its authenticated service. Outages and maintenance
      happen, and status notices are published separately.
    - Some government servers are restricted to agency, military, or
      registered users, or are unreachable from some networks.
    - Stratum is a hop count, not accuracy. A stratum 1 server reached
      over a long, asymmetric internet path can give a worse offset than a
      nearby stratum 2 server (PA-13, PA-140). A stratum 1 server whose
      reference fails can keep announcing stratum 1 until it notices.
    - Traceability needs more than the server's name: a stated
      uncertainty chain from the lab's UTC(k) through the network path to
      the local clock (PA-139).
  - How it appears in code and operations:
    - Configurations or documents claiming "stratum 0" or "stratum 1 from
      NIST, so authoritative" with no measured error bound.
    - Code that treats a low stratum value as proof of accuracy, or
      accepts stratum 0 replies as time (PA-140).
    - One government server as the only source, often hardcoded by IP.
    - Polling national services more often than their published limits,
      or ignoring their rate-limit replies.
  - What to check:
    - Source lists: which servers are national laboratories, which are
      other agencies, and how many independent sources there are.
    - Stratum handling and accuracy claims in code and documentation.
    - Polling intervals against service rules.
  - Fix:
    - Treat stratum as context only; measure and report the error bound
      (C27.8).
    - Use several independent sources; a national laboratory service can
      be one of them. Use the lab's authenticated service, or NTS from a
      known operator, where authentication matters.
    - For traceable time, document the uncertainty chain, or use local
      GPS- or PTP-disciplined references with stated accuracy (C27.7).
    - Follow each service's polling rules and honor rate-limit replies.
  - Not a finding:
    - National laboratory servers used as one of several monitored,
      politely polled sources, with no unsupported accuracy claim.
  - Escalate (NEEDS-HUMAN): regulated or legal timestamping that claims
    traceability via a government server without a documented
    uncertainty chain.
  - Proposed severity (for the user to decide): CRITICAL when
    authoritative, regulated, or security-relevant time relies on a single
    government server or on stratum as proof of accuracy. HIGH for code
    accepting stratum 0 replies as time, or treating stratum as accuracy
    on a core path. MEDIUM for unsupported accuracy claims and polling
    beyond service rules. LOW for test-only code.

- PA-142: Nearest-server assumption. Teams assume the right time sources
  are always the servers closest to them with the lowest latency.
  - Overlap: PA-13 and PA-140 cover round-trip error and the error bound.
    PA-139 and PA-141 cover source choice and authority. PA-142 covers
    latency and proximity as a selection rule, and what it misses. Merged
    per the class ledgers (destination C27.10).
  - Why it is false (RFC 5905 and NTP documentation unless marked):
    - Low latency limits only part of the error. A client's offset error
      is bounded by half the round trip, but the server's own error (root
      distance, PA-140) adds to it. A nearby server that is unsynced,
      free-running on its local clock, or fed by a poor upstream is close
      and wrong. Select by total error bound, not by round trip alone.
    - Nearest sources are often not independent: same operator, same
      upstream, same network, same failure. NTP's selection algorithm can
      outvote a bad source ("falseticker") only among enough independent
      ones; NTP guidance recommends at least four.
    - The closest responder can be an attacker. A rogue server on the
      local network, a DHCP-supplied NTP server (DHCP option 42; many
      clients accept it by default), or an on-path attacker that replies
      fastest wins a lowest-latency rule.
    - Geographic and network proximity differ: routes may detour through
      distant exchanges, and anycast addresses map to different sites as
      routing changes.
    - Latency changes over time, with load, routing, and mobility, so a
      one-time "ping and pick" choice goes stale. Roaming devices change
      their nearest server constantly.
    - Everyone choosing the same nearest server concentrates load; pool
      zones and vendor zones exist to spread it (PA-139).
    - Sync daemons already weigh delay, dispersion, and agreement
      continuously; a hand-rolled latency choice usually does worse.
  - How it appears in code and operations:
    - Scripts or code that ping candidate servers once and pin the lowest
      latency one.
    - Configurations with only a nearby local server or two from the same
      operator.
    - DHCP-supplied NTP servers accepted on untrusted networks by hosts
      that issue authoritative time.
    - Server selection by geolocation of the client.
  - What to check:
    - How sources are chosen, how many there are, and whether they are
      independent.
    - Whether DHCP or other network-supplied NTP settings are accepted,
      and where.
  - Fix:
    - Configure several diverse, independent sources (at least four where
      a bad one must be outvoted) and let the daemon's selection choose
      among them continuously.
    - Judge sources by their error bound (root distance plus half the
      round trip) and by monitored agreement, not by latency alone
      (C27.8).
    - Do not accept network-supplied NTP servers on untrusted networks
      for hosts that need correct or authoritative time; authenticate
      sources where it matters (C27.2).
    - Nearby disciplined servers (local GPS- or PTP-backed) are good when
      monitored and backed by independent sources (C27.7).
  - Not a finding:
    - Daemon-managed selection among several independent sources,
      including nearby ones.
  - Escalate (NEEDS-HUMAN): authoritative-time hosts whose source
    selection and independence cannot be established.
  - Proposed severity (for the user to decide): CRITICAL when
    authoritative, regulated, or security-relevant time follows a single
    nearest source or accepts network-supplied NTP servers on untrusted
    networks. HIGH for pinned lowest-latency single-source selection on a
    core path. MEDIUM for low source diversity and stale one-time
    selection. LOW for test-only code.

- PA-143: Good-faith server assumption. Teams assume NTP servers never
  serve the wrong time on purpose.
  - Overlap: PA-116 covers deliberate date misbehavior in software in
    general. PA-137 covers unauthenticated NTP and spoofed replies.
    PA-139 to PA-142 cover source choice. PA-143 covers servers and
    attackers that shift time on purpose, what that enables, and the
    defenses. Merged per the class ledgers (destination C27.11).
  - Why it is false (published research and documentation; not verified
    here because UDP 123 is blocked):
    - Some deliberate offsets are benign and announced: leap-smearing
      services serve time that differs from UTC by up to about half a
      second during a smear (PA-20).
    - Anyone can operate a server, including in the volunteer pool
      (PA-139). A malicious operator can serve shifted time until
      monitoring removes it, and can answer monitors correctly while
      lying to chosen clients, because monitors observe from a limited
      set of locations.
    - Attackers shift time without owning a server: on-path tools (for
      example "Delorean", presented at Black Hat Europe 2014) rewrite NTP
      replies, and off-path attacks using spoofed Kiss-o'-Death packets
      and fragmentation were published by Malhotra and others (NDSS
      2016). Unauthenticated NTP makes these possible (PA-137).
    - Test and fake time servers (time-travel test environments, fudged
      local clocks) can be left reachable from production (PA-26).
    - Malware and insiders repoint hosts to attacker servers by changing
      NTP configuration or registry settings.
    - Shifted time is a weapon: it revives expired or revoked
      certificates, replays expired tokens, expires HSTS entries,
      breaks Kerberos and DNSSEC validation, empties or freezes caches,
      triggers time bombs and license checks (PA-116), and corrupts logs
      and audit order (PA-31, PA-60).
  - How it appears in code and operations:
    - Security decisions (certificate validity, token expiry, replay
      windows, license checks) trusting the local clock with no defense
      against a shifted clock (PA-11).
    - Unauthenticated NTP on hosts that issue or validate security
      tokens or certificates.
    - Sync configurations that accept any jump after startup, with no
      limit on later corrections.
    - NTP settings writable by unprivileged users or applications.
    - Test or fake time servers reachable from production networks.
  - What to check:
    - Which security decisions depend on local time, and how time is
      protected on those hosts.
    - Authentication, source diversity, and correction limits in sync
      configuration.
    - Who can change NTP configuration.
  - Fix:
    - Authenticate time on security-relevant hosts (NTS, RFC 8915), while
      remembering that authentication proves who sent the time, not that
      the sender is honest (C27.2).
    - Use several independent sources so one liar is outvoted (C27.10).
    - Step only at startup, and limit or alarm on large corrections later
      (for example chrony `maxchange`, or ntpd's panic threshold without
      `-g` after boot) (C27.2).
    - Apply plausibility bounds to "now" in security decisions (PA-12).
    - Consider protocols that make misbehavior provable, such as
      Roughtime (an IETF draft run by some operators); adding a client
      needs user approval.
    - Restrict who can change time configuration, and alarm on changes.
    - Keep fake time servers out of production networks (PA-26).
  - Not a finding:
    - Announced leap smearing used consistently across a fleet (C27.4).
    - Hosts with authenticated, diverse sources, correction limits, and
      monitoring.
  - Escalate (NEEDS-HUMAN): security-relevant hosts whose time protection
    (authentication, diversity, correction limits) cannot be established
    from the review unit.
  - Proposed severity (for the user to decide): CRITICAL when certificate,
    token, replay, or license decisions rely on time that an attacker can
    shift (unauthenticated single source, unlimited corrections, or
    writable configuration). HIGH for unauthenticated sync on
    security-relevant hosts and fake time servers reachable from
    production. MEDIUM for missing change alarms. LOW for test-only code.

- PA-144: Sovereign-service assumption. Teams assume a government (the
  user's example is the US government and NIST) will never take its time
  services down, block access to them, or deliberately serve wrong time.
  - Overlap: PA-141 covers what national services offer. PA-143 covers
    deliberate shifts by servers and attackers. PA-144 covers dependence
    on one government or operator as a single point of failure for
    availability and integrity, including policy decisions, funding,
    conflict, and blocking. Merged per the class ledgers (destination
    C27.12).
  - Why it is false (historical and documented facts; the audit takes no
    political position, it treats every operator as a dependency):
    - Governments have deliberately degraded time and positioning
      signals: the US degraded civilian GPS accuracy through Selective
      Availability until it was turned off on 2000-05-02. GPS time and
      GPS-disciplined clocks depend on that system's policy.
    - Funding and policy change services: a 2018 US budget proposal
      sought to defund NIST's WWV, WWVH, and WWVB radio time stations
      (reported; the stations continued). During the October 2013 US
      federal shutdown, NIST's main website went offline, though its time
      services kept running (reported). Services can be retired, limited,
      or reprioritized.
    - States interfere with timing signals in conflict: widely reported
      GNSS jamming and spoofing attributed to state actors has affected
      aviation and shipping in regions such as the Baltic and the Eastern
      Mediterranean in recent years.
    - Sovereign systems fail without intent: Galileo had a service outage
      of about a week in July 2019 after a ground infrastructure fault.
      Other constellations (GLONASS, BeiDou, Galileo) exist partly so
      countries are not dependent on one government's system.
    - Access is blocked for many reasons: network policy (UDP 123 is
      blocked from this host, verified), national firewalls, sanctions,
      export controls, or a country blocking another government's
      endpoints. Clients abroad may lose access to a foreign national
      service.
    - Any operator, government or not, can be compromised, legally
      compelled, misconfigured, or overloaded (PA-139, PA-143).
  - How it appears in code and operations:
    - All time sources from one operator or one government domain (for
      example only `*.nist.gov`), or one GNSS constellation in receivers.
    - Critical infrastructure (trading, telecom, power, aviation,
      healthcare) with no holdover plan if an external reference is lost
      or manipulated (PA-122).
    - Products sold internationally that hardcode one country's national
      service.
    - Risk assessments that list a government time service as
      "guaranteed".
  - What to check:
    - Operator and jurisdiction diversity of time sources and GNSS
      constellations.
    - Holdover capability and duration against the requirement.
    - Reachability of chosen services from every deployment region.
  - Fix:
    - Diversify sources across operators and jurisdictions, and receivers
      across GNSS constellations where hardware allows (C27.10).
    - Keep local holdover for critical systems (disciplined oscillators
      with a stated holdover budget, C27.5), and detect sudden shifts
      (C27.11).
    - Choose regional services per deployment region instead of one
      country's service everywhere.
    - Record time-source dependencies and their failure modes in the risk
      register, without labeling any operator as guaranteed.
  - Not a finding:
    - A national laboratory service used as one of several independent,
      monitored sources (C27.9).
  - Escalate (NEEDS-HUMAN): critical infrastructure or regulated systems
    whose time-source diversity, holdover, and loss-of-reference plan are
    not stated.
  - Proposed severity (for the user to decide): CRITICAL when
    authoritative, regulated, safety, or critical-infrastructure time
    depends on a single government or operator with no holdover or
    alternative. HIGH for single-constellation GNSS timing on core paths
    and single-country services hardcoded in international products.
    MEDIUM for undocumented time-source dependencies. LOW for test-only
    code.

- PA-145: IPv4-only sync assumption. Teams assume supporting IPv4 alone
  is enough to synchronize time over the internet.
  - Overlap: PA-137 covers unreachable sync. PA-139 covers pool sources
    and hardcoded IPs. PA-145 covers address families, transports, and
    ports needed to reach time sources, and the access-control gaps
    between them. Merged per the class ledgers (destination C27.13).
  - Why it is false (DNS results verified from this host on 2026-10-04;
    other facts documented):
    - IPv6-only networks exist: many mobile carriers run IPv6-only access
      with NAT64 and DNS64 or 464XLAT, and cloud providers offer
      IPv6-only subnets. IPv4 literal addresses cannot be reached there
      unless the device translates them itself (464XLAT); a hostname with
      DNS64 can.
    - Sources differ in IPv6 support: `pool.ntp.org` returned four IPv4
      addresses and no IPv6 address, while `2.pool.ntp.org`,
      `time.google.com`, `time.cloudflare.com`, `time.nist.gov`, and
      `time.aws.com` returned both (verified). An IPv6-only host
      configured with `pool.ntp.org` gets no time.
    - Cloud link-local time endpoints differ by family: AWS documents
      169.254.169.123 for IPv4 and an IPv6 address for Nitro instances; a
      hardcoded IPv4 endpoint fails in an IPv6-only subnet.
    - Dual-stack has its own failure: a client that picks an IPv6 address
      over a broken IPv6 path times out, and NTP over UDP gets no "happy
      eyeballs" fallback in hand-rolled clients.
    - Shared IPv4 addresses behind carrier-grade NAT put many clients
      behind one address, so servers' per-address rate limits and
      Kiss-o'-Death replies hit innocent clients (PA-140).
    - Time protocols use more than UDP 123 over IPv4: NTS key exchange
      runs over TCP port 4460 (RFC 8915), and PTP uses its own UDP ports or
      Ethernet directly. Firewalls opening only UDP 123 break NTS.
    - Access control can cover one family only: ntpd needs separate
      `restrict -6` rules, and firewall rules written for IPv4 can leave a
      server open, or closed, on IPv6.
  - How it appears in code and operations:
    - Custom SNTP clients hardcoding `AF_INET`, or resolving only A
      records.
    - Validators or configuration UIs accepting only dotted-quad NTP
      server addresses.
    - Hardcoded IPv4 time-server or link-local addresses (PA-139).
    - Daemons forced to IPv4 (`ntpd -4`, `chronyd -4`) on hosts that may
      be IPv6-only.
    - Firewall or security-group rules allowing UDP 123 only on IPv4, or
      not allowing TCP 4460 where NTS is used.
    - ntpd configurations with `restrict` rules for IPv4 only.
  - What to check:
    - Address families supported by time clients, configurations, and
      validators.
    - Whether chosen sources have IPv6 addresses where hosts may be
      IPv6-only.
    - Firewall and ACL rules for both families and for NTS ports.
  - Fix:
    - Use hostnames, not literal addresses, and sources that publish both
      A and AAAA records; use `2.pool.ntp.org`-style IPv6-capable zones
      or vendor zones where the pool is acceptable (PA-139).
    - Support both families in custom clients, resolve both record types,
      and fall back across addresses.
    - Use the cloud provider's documented endpoint for each family.
    - Write firewall and ACL rules for both families, and open TCP 4460
      where NTS is used.
    - Test sync on IPv4-only, IPv6-only, and dual-stack networks.
  - Not a finding:
    - Deployments documented and enforced as IPv4-only networks, using
      hostnames.
  - Escalate (NEEDS-HUMAN): products deployed on customer or mobile
    networks whose address-family support is not stated.
  - Proposed severity (for the user to decide): HIGH when hosts or devices
    that can land on IPv6-only networks cannot sync on a core path, when
    ACLs leave a time server open on one family, or when NTS is blocked
    on security-relevant hosts. MEDIUM for IPv4-only validators and
    clients in products that may need IPv6. LOW for test-only code.

- PA-146: Always-answering server assumption. Teams assume an NTP server
  always replies with time and never blocks, refuses, or rate-limits a
  client.
  - Overlap: PA-137 covers sync being unreachable. PA-140 covers
    Kiss-o'-Death codes as reply fields. PA-141 covers national services'
    polling rules. PA-145 covers rate limits behind shared IPv4. PA-146
    covers client behavior when a server stays silent, refuses, or
    throttles, and the client designs that cause or worsen it. Merged per
    the class ledgers (destination C27.14).
  - Why it is false (RFC 5905 and documentation unless marked):
    - Servers refuse on purpose: Kiss-o'-Death replies (`RATE` asks the
      client to slow down; `DENY` and `RSTR` tell it to stop using the
      server), access rules that drop queries silently (ntpd `restrict`
      with `ignore`, `limited`, or `kod`), and per-service polling rules
      (PA-141).
    - Networks drop NTP: firewalls and network policy block UDP 123 (no
      server answered from this host, verified), and some providers filter
      or rate-limit NTP traffic since the 2013-2014 amplification attacks
      that abused ntpd's `monlist` command (CVE-2013-5211), after which
      many operators restricted their servers.
    - Shared addresses trigger limits meant for others (PA-145).
    - Servers go down, get overloaded, or are retired, and a pool name may
      resolve to a server that has just left (PA-139).
    - Client fleets overload servers themselves: default firmware polling
      too often, or all devices polling at the same second after a
      scheduled job or a mass reboot, creates load spikes that cause drops
      (PA-139 cites hardcoded-server floods).
    - NTP's normal minimum poll interval is 64 seconds (ntpd `minpoll 6`);
      clients polling far faster are the ones most likely to be limited.
  - How it appears in code and operations:
    - Blocking time queries with no timeout, at boot or in request paths,
      so a silent server hangs startup or requests.
    - Tight retry loops with no backoff, making rate limiting worse.
    - Kiss-o'-Death replies ignored, or parsed as a timestamp (PA-140).
    - A failed query treated as success: offset 0, the local clock, or the
      epoch used as "network time".
    - Polling every few seconds, or fleets polling on the same schedule
      with no jitter.
    - No failover to other sources, and no defined behavior when no time
      source answers (PA-137).
  - What to check:
    - Timeouts, retries, backoff, jitter, and polling intervals in time
      clients and schedules.
    - Kiss-o'-Death and no-reply handling.
    - What the system does while it has no network time.
  - Fix:
    - Use the platform sync daemon, which handles polling and backoff
      (BP-1).
    - In custom clients: set timeouts, back off exponentially with jitter,
      honor `RATE` by polling less and `DENY` or `RSTR` by dropping the
      server, and fail over to other sources.
    - Never treat a failed query as a time value; report "no time" and
      apply the stated policy (C27.1).
    - Keep polling within NTP's normal intervals and each service's rules,
      and spread fleet schedules with jitter.
    - Monitor failed queries and Kiss-o'-Death counts (PA-136).
  - Not a finding:
    - Platform daemons with several sources and default polling.
  - Escalate (NEEDS-HUMAN): devices or fleets whose behavior with no
    reachable time source is not stated.
  - Proposed severity (for the user to decide): HIGH when a silent or
    refusing server hangs startup or a core request path, when a failed
    query becomes a time value, or when a fleet's polling can overload a
    third-party service. MEDIUM for missing backoff, jitter, or failover.
    LOW for test-only code.

- PA-147: Few-sources assumption. Teams assume checking one or two time
  sources is enough.
  - Overlap: PA-142 recommends at least four independent sources as a fix
    and covers independence. PA-144 covers operator diversity. PA-146
    covers sources that stop answering. PA-147 covers source count itself:
    what one, two, three, and four sources can and cannot detect, daemon
    minimums, and combining replies. Merged per the class ledgers
    (destination C27.15).
  - Why it is false (RFC 5905 and NTP documentation unless marked):
    - One source cannot be checked: if it is wrong, nothing disagrees.
    - Two sources that disagree cannot say which is right; the client
      can only notice a conflict ("a man with two watches never knows the
      time").
    - Three sources can outvote one bad source while all three answer,
      but lose that ability as soon as one stops answering.
    - NTP guidance therefore recommends at least four sources, so one can
      fail and one can be wrong while a majority still agrees. NTP's
      selection algorithm (an intersection of confidence intervals)
      works by finding a majority of agreeing "truechimers".
    - Daemons sync to a single source by default: chrony's `minsources`
      and ntpd's `tos minsane` default to 1, so a host with one reachable
      source follows it without complaint. chrony's `pool` directive
      takes up to four sources by default (`maxsources 4`); a single
      `server` line gives one.
    - Configured count is not live count: sources become unreachable,
      refuse, or get rejected over time (PA-146), so a host configured
      with four may be running on one.
    - Count without independence is not diversity: several servers from
      one operator or upstream fail together (PA-142, PA-144).
    - Averaging is not voting: a client that averages two replies moves
      halfway toward a bad one instead of rejecting it.
  - How it appears in code and operations:
    - Configurations with one or two `server` lines on hosts that need
      correct or authoritative time.
    - `minsources 1` or `tos minsane 1` (often by default) on such hosts.
    - Custom clients querying one or two servers and taking the first
      answer or the average.
    - No monitoring of how many sources are reachable and selected.
  - What to check:
    - Configured and live source counts, and their independence.
    - Daemon minimum-source settings.
    - How custom clients combine replies.
  - Fix:
    - Configure at least four independent sources where a wrong source
      must be outvoted (PA-142), more where some may be unreachable.
    - On authoritative hosts, require a minimum number of agreeing
      sources before adjusting the clock (chrony `minsources`, ntpd
      `tos minsane`), and alarm when it is not met.
    - Combine replies by agreement (intersection or median with outlier
      rejection), not by averaging or first answer; better, use the
      daemon (BP-1).
    - Monitor reachable and selected source counts (PA-136).
  - Not a finding:
    - Ordinary clients syncing to a local, monitored time server that
      itself uses several independent sources.
  - Escalate (NEEDS-HUMAN): authoritative-time hosts whose live source
    count and independence cannot be established.
  - Proposed severity (for the user to decide): CRITICAL when
    authoritative, regulated, or security-relevant time follows one or
    two sources with no agreement requirement. HIGH for custom clients
    averaging or taking the first reply on a core path. MEDIUM for
    missing source-count monitoring. LOW for test-only code.

- PA-148: NTP-only assumption. Teams assume that once a host has NTP
  time, every other time source (RTC, GPS, and others) can be ignored.
  - Overlap: PA-11 and PA-12 cover RTC failures and boot defaults.
    PA-122 and PA-144 cover holdover and GNSS dependence. PA-143 covers
    detecting shifted time. PA-148 covers the roles each source plays
    alongside NTP, how they must be combined, and the conflicts when
    several discipline one clock. Merged per the class ledgers
    (destination C27.16).
  - Why it is false (documented unless marked):
    - The RTC carries time across power loss and boot. If it is never
      updated from synced system time, the next boot starts from a drifted
      or wrong value, and everything before the next sync is wrong
      (PA-12). Linux updates the RTC from system time only while the
      kernel considers the clock synchronized ("11-minute mode", enabled
      by chrony `rtcsync` or ntpd), or when `hwclock --systohc` runs. This
      container exposes no RTC device and the kernel reports the clock
      unsynchronized, so that mode is off here (verified). Windows keeps
      the RTC in local time (PA-11).
    - The RTC and build time give a floor: an NTP result earlier than the
      last known good time or the build date is suspect (PA-12, PA-143).
    - GNSS and PPS references are more accurate than internet NTP:
      microseconds or better locally against milliseconds over the
      internet, which matters where regulation or measurement needs it
      (PA-46, PA-139). GPS time runs 18 s ahead of UTC and receivers
      convert it (PA-13).
    - Independent sources cross-check each other: NTP can expose GNSS
      spoofing, and a local GNSS reference can expose shifted NTP
      (PA-143). Ignoring one removes the check.
    - When NTP is lost, the remaining sources provide holdover: the
      disciplined RTC, a GNSS receiver, or a good oscillator (PA-122).
    - Other sources exist and may be better in context: PTP on local
      networks, hypervisor time (Hyper-V, VMware Tools, `kvm-clock`,
      `ptp_kvm`, PA-138), cellular network time (NITZ), and radio time
      signals (WWVB, DCF77, MSF).
    - Two mechanisms disciplining one clock fight: running hypervisor
      periodic time sync and an NTP daemon together, or two daemons, makes
      the clock step or oscillate. One source should discipline the clock;
      the others should feed it as references or act as checks.
    - NTP disciplines the wall clock only; elapsed time still comes from
      monotonic clocks (PA-11).
  - How it appears in code and operations:
    - Sync configured without updating the RTC (no `rtcsync`, no
      `hwclock --systohc`), so reboots start from stale time.
    - GNSS or PPS hardware present but not used as a reference, or used
      without UTC conversion.
    - VMs running hypervisor periodic sync and NTP at once, or two sync
      daemons on one host.
    - No cross-check between independent sources on authoritative hosts.
    - No fallback plan when NTP is unavailable (PA-137, PA-146).
  - What to check:
    - RTC update settings and boot-time time handling.
    - Available references (GNSS, PPS, PTP, hypervisor) and how they are
      used.
    - How many mechanisms adjust the clock.
  - Fix:
    - Keep the RTC updated from synced time (`rtcsync`, or `hwclock
      --systohc` at shutdown) and use it, with build time, as a floor
      (PA-12).
    - Use local GNSS, PPS, or PTP references where accuracy needs them,
      with correct GPS-to-UTC conversion, alongside independent network
      sources (PA-139).
    - Let exactly one mechanism discipline each clock, and feed or
      cross-check it from the others; disable conflicting periodic syncs.
    - Define holdover and fallback order for when NTP is lost (PA-122).
  - Not a finding:
    - Hosts whose single discipline uses several references with RTC
      updates enabled.
    - Containers that rely on the host clock by design (PA-137).
  - Escalate (NEEDS-HUMAN): authoritative or measurement systems with
    local references available but no stated source hierarchy and
    holdover plan.
  - Proposed severity (for the user to decide): HIGH when conflicting
    disciplines step or oscillate the clock on a core path, when reboots
    start from stale time on devices that act before syncing, or when
    authoritative hosts ignore available independent references. MEDIUM
    for missing RTC updates and fallback plans. LOW for test-only code.

- PA-149: Every-node-is-authoritative assumption. Teams assume each
  client device and server in a system should sync independently to its
  own external sources and treat the result as authoritative.
  - Overlap: PA-14 and PA-103 cover server-authoritative time for
    decisions. PA-60 covers ordering across systems. PA-142 and PA-147
    cover source selection and counts. PA-146 covers fleet load on public
    servers. PA-149 covers time distribution architecture: who syncs to
    what, and which node's time is authoritative. Merged per the class
    ledgers (destination C27.17).
  - Why it is false (documented unless marked):
    - Systems need consistent time between their own nodes, often more
      than each node's absolute accuracy. Nodes syncing independently to
      different public sources, over different paths, with different smear
      policies, disagree with each other by more than nodes sharing an
      internal hierarchy (PA-13, PA-20).
    - Designed hierarchies exist for this: Windows domain members sync
      from domain controllers up to the PDC emulator (PA-138); fleets use
      internal stratum servers or the cloud provider's in-region time
      service; PTP distributes time from a grandmaster.
    - Every node reaching the internet for time multiplies load on public
      servers (PA-146), requires outbound UDP 123 from every host, and
      gives attackers more targets to shift (PA-143). A few monitored
      internal servers are easier to secure and observe (PA-136).
    - Many nodes cannot sync themselves at all: browsers, sandboxed apps,
      containers (which share the host clock), and offline devices
      (PA-137, PA-138).
    - Authority for decisions is a role, not a property of every clock:
      ordering, expiry, and audit time should come from one designated
      authority (PA-14, PA-60); a client's well-synced clock is still
      untrusted input (PA-103).
    - The opposite failure also exists: one internal time server with no
      redundancy is a single point of failure (PA-147).
  - How it appears in code and operations:
    - Every host image configured with public pool or vendor servers,
      with no internal time tier, in large fleets.
    - Outbound UDP 123 to the internet allowed from every host.
    - Client device time used as authoritative for system decisions
      because "the device syncs NTP".
    - Mixed sources across one system (some hosts on a smeared cloud
      service, others on the pool) (PA-20).
    - A single internal time server with no redundancy or monitoring.
  - What to check:
    - The system's time distribution design: tiers, sources per tier, and
      redundancy.
    - Which node is authoritative for each time-dependent decision.
    - Egress rules for time traffic.
  - Fix:
    - Design a hierarchy: a redundant internal tier (or the cloud
      provider's in-region service) synced to several independent
      upstreams (PA-139, PA-147), with all other nodes syncing to it.
    - Use one leap policy across the system (PA-20).
    - Keep decision authority on designated servers; treat client time as
      untrusted (PA-14, PA-103).
    - Restrict outbound time traffic to the internal tier, and monitor
      the tier and node offsets against it (PA-136).
  - Not a finding:
    - Small systems or standalone devices that sync independently and do
      not depend on cross-node time agreement.
    - Offline-capable edge devices with their own sync that defer to
      server time when connected.
  - Escalate (NEEDS-HUMAN): distributed systems whose time distribution
    design and cross-node skew requirement are not stated.
  - Proposed severity (for the user to decide): HIGH when cross-node
    ordering, leases, or expiry on a core path depend on agreement between
    independently synced nodes, or when client device time is treated as
    authoritative. MEDIUM for fleets without an internal tier, mixed
    policies, and an unredundant internal server. LOW for test-only code.

- PA-150: External-time-always assumption. Teams assume external
  authoritative time (NTP, GNSS, or both) should drive the system even
  where the software or architecture depends, for its own reliability,
  performance, or stability, on internal timekeeping that is less
  accurate against UTC.
  - Overlap: PA-11 and PA-55 cover monotonic clocks for durations.
    PA-60 covers logical clocks for ordering. PA-121 and PA-122 cover
    media and signal clocks. PA-148 covers combining sources for one
    clock. PA-149 covers distribution. PA-150 covers choosing the right
    time domain for each job, and the damage done when external time is
    forced into mechanisms that need internal consistency or stability.
    Merged per the class ledgers (destination C27.18).
  - Why it is false (documented unless marked):
    - Different jobs need different clocks. Records that mean something
      outside the system (audit, legal, billing, logs) need UTC traceable
      to external time. Internal mechanics need stability and
      consistency: elapsed time and timeouts need monotonic clocks
      (PA-11), ordering needs logical, vector, or hybrid clocks or
      consensus terms (PA-60), and media and control need their own
      sample or frame clocks (PA-121).
    - Steering mechanics by external time breaks them: a wall-clock step
      fires or stalls timers, breaks leases, and reorders logs (PA-11,
      PA-21, PA-68); adjusting an audio or video clock to NTP causes
      glitches where resampling should absorb drift (PA-121).
    - Distributed systems bound skew between nodes instead of trusting
      external time alone: CockroachDB requires node clocks within a
      configured maximum offset (500 ms by default) and stops nodes that
      exceed it; Spanner's TrueTime exposes uncertainty intervals
      (PA-60).
    - Internal consistency can matter more than UTC accuracy: an isolated
      or air-gapped cluster keeps running on agreed internal time (for
      example an internal tier in orphan mode), and should neither halt
      nor jump when external time is lost and later restored. This is a
      deliberate design, unlike an undisciplined server passed off as
      accurate (PA-140).
    - Hard dependence on external time is an availability risk: a system
      that refuses to run without NTP or GNSS fails whenever they do
      (PA-137, PA-144); holdover with degraded accuracy claims keeps it
      running (PA-122).
    - Reconnecting to external time after a long gap can require a large
      correction; slewing slowly or holding until a maintenance window
      can be safer than stepping a live system (PA-137).
  - Scenario from the user: a legacy server that has run for decades,
    with little documentation, that must stay up, is running the wrong
    time, and cannot be synced, fixed, or updated because downtime is
    unacceptable.
    - Correcting its clock in place is the risky act: unknown jobs,
      licenses, certificates, sequences, caches, or replication on the box
      may depend on the current, wrong time, and a step could break them
      or force the downtime the owners forbid (PA-11, PA-68).
    - Its time is a separate time domain. Treat it like a foreign clock:
      measure its offset (compare its timestamps, logs, or protocol
      responses with a trusted reference from outside), track how the
      offset drifts, and keep a dated record of measurements.
    - Translate at the boundary: an adapter or ingestion step converts its
      timestamps to UTC using the measured offset and drift model, keeps
      the raw value, and records the correction applied and its
      uncertainty (PA-31, PA-94).
    - Never let it be authoritative: other systems must not sync from it,
      and its raw timestamps must not decide ordering, expiry, billing,
      or audit outcomes elsewhere (PA-60, PA-149).
    - Protect it from well-meaning fixes: a new NTP setting, a hypervisor
      time sync, or a migration that silently corrects the clock can be
      the outage. Document "do not sync" with the reason and owner.
    - Watch its limits: a wrong clock reaches range limits (2038, 2036,
      certificate expiry) at a different real date than expected, and
      peers validating its certificates or tokens may reject it (PA-18,
      PA-12).
    - Record it in the risk register with a replacement or controlled
      correction plan; whether its uncorrected timestamps are acceptable
      for audit or legal use is a human decision.
  - How it appears in code and operations:
    - Timeouts, leases, rate limits, or consensus logic reading the wall
      clock because it is "the accurate one" (PA-11).
    - Media, audio, or control loops slaved directly to NTP time.
    - Systems that halt or refuse requests when external time is
      unavailable, with no holdover mode.
    - Clusters configured to step to external time at any moment, with
      no skew bound between nodes.
    - Designs with one clock serving both external records and internal
      mechanics, with no stated mapping.
  - What to check:
    - Each time use: which time domain it needs (external UTC, monotonic,
      logical, media, or cluster time).
    - Behavior when external time is lost, degraded, or restored after a
      gap.
    - Skew bounds between nodes and what enforces them.
  - Fix:
    - Classify each time use and pick its clock: external UTC for
      externally meaningful records, monotonic for durations, logical or
      hybrid clocks for ordering, media clocks for media, bounded cluster
      time for coordination.
    - Bridge domains explicitly (for example record both a UTC timestamp
      and a logical or monotonic value) and document the mapping.
    - Design holdover: keep running on internal time with stated,
      degrading accuracy claims when external time is lost, and rejoin by
      slewing or at a planned moment (PA-122).
    - Bound and monitor inter-node skew, and stop or fence nodes that
      exceed it.
  - Not a finding:
    - External UTC used for records, with internal clocks used for
      mechanics, each documented.
  - Escalate (NEEDS-HUMAN): systems whose required time domains, skew
    bounds, and behavior on loss of external time are not stated.
  - Proposed severity (for the user to decide): HIGH when external time
    steering breaks leases, consensus, timeouts, media, or control on a
    core path, or when loss of external time halts a core service with no
    holdover. MEDIUM for undocumented time-domain mapping and missing
    skew bounds. LOW for test-only code.

- PA-151: Always-GPS assumption. Teams assume GPS will always be
  available to sync time.
  - Overlap: PA-12 covers GPS week rollover. PA-144 covers Selective
    Availability, state jamming, and constellation dependence. PA-148
    covers GNSS accuracy and combining it with other sources. PA-151
    covers the physical, operational, and failure reasons a GPS time
    source is unavailable or wrong, and designs that depend on it alone.
    Merged per the class ledgers (destination C27.19).
  - Why it is false (documented and reported; not verifiable from this
    container, which has no GNSS hardware):
    - A receiver needs sky view: indoors, data-center halls, basements,
      tunnels, urban canyons, and dense foliage block or degrade signals.
      Cloud and leased hosting usually offer no antenna access at all.
    - Hardware fails: antennas, cables, splitters, amplifiers, and
      lightning arrestors fail or get damaged, and a lightning strike can
      take out the whole chain.
    - Getting a fix takes time: a cold receiver needs several satellites
      and can take minutes before it outputs time; a timing receiver in
      position-hold mode can then keep time with fewer satellites.
    - Signals are jammed and spoofed: cheap illegal jammers (often in
      vehicles) knock out nearby receivers, militaries run announced GPS
      interference tests (published as aviation notices), and state
      jamming and spoofing affect whole regions (PA-144).
    - Space weather (ionospheric scintillation) degrades signals, worst
      near the equator and poles.
    - The system itself errs: in January 2016 a ground-segment upload
      error made some GPS satellites broadcast UTC offset data that was
      wrong by about 13 microseconds, causing timing alarms in telecom
      and other networks (reported). Receivers have mishandled week
      rollovers (1999, 2019; next 2038-11-21 for 10-bit week counts) and
      leap-second announcements (PA-12, PA-104).
    - Receivers age out: unsupported firmware cannot be fixed for the
      next rollover or leap-second change.
    - GPS time is not UTC: it runs 18 s ahead, and receivers must apply
      the broadcast offset correctly (PA-13).
    - A receiver gives time to one box; distributing it (PPS cabling,
      PTP, internal NTP) is another chain that can fail (PA-149).
  - How it appears in code and operations:
    - GPS or PPS as the only time source, with no network sources and no
      holdover oscillator.
    - Designs assuming time is available at power-on, before a fix.
    - No monitoring of fix status, satellite count, signal quality, or
      receiver alarms.
    - No handling of receiver-reported loss of fix: the host keeps
      following a free-running receiver.
    - Firmware with no update path before known rollover dates.
  - What to check:
    - Whether GPS is a sole source, and what happens without a fix.
    - Receiver monitoring and alarms.
    - Receiver firmware support and known rollover dates.
  - Fix:
    - Combine GPS with independent network sources and a holdover
      oscillator with a stated budget (PA-122, PA-148), preferably
      multi-constellation receivers (PA-144).
    - Define behavior until the first fix and on loss of fix: hold over,
      fall back, and mark data quality (PA-122).
    - Monitor fix status, satellites, signal levels, and spoofing or
      jamming indicators, with alarms.
    - Keep receiver firmware supported, and check rollover and
      leap-second handling before the dates arrive (PA-95).
  - Not a finding:
    - GPS used as one of several monitored references with holdover.
  - Escalate (NEEDS-HUMAN): critical timing that depends on GPS without a
    stated loss-of-signal plan and holdover requirement.
  - Proposed severity (for the user to decide): CRITICAL when safety,
    critical-infrastructure, regulated, or security-relevant time depends
    on GPS alone with no holdover or alternative. HIGH when core systems
    cannot start or keep correct time without a fix, or follow a
    receiver that has lost its fix. MEDIUM for missing receiver
    monitoring and unsupported firmware. LOW for test-only code.

- PA-152: GPS-equipped-device assumption. Teams assume a device with GPS
  hardware always sets its time from GPS, not from NTP, cellular network
  time, or its RTC.
  - Overlap: PA-138 covers platform sync differences. PA-148 covers
    sources beside NTP. PA-151 covers GPS availability. PA-152 covers
    which source actually sets a GPS-equipped device's clock, and code
    that confuses the device clock with GNSS time. Merged per the class
    ledgers (destination C27.20).
  - Why it is false (documented platform behavior; not verifiable from
    this container):
    - Phones usually set the clock from carrier network time (NITZ) and
      NTP. Android's automatic-time service ranks sources by a
      device-configurable priority list; the defaults favor telephony and
      network time, and GNSS time is an optional origin that many devices
      leave off. iOS sets time from the carrier and Apple's time servers.
      Users can turn automatic time off entirely.
    - The GNSS receiver often sits in a separate subsystem (modem or
      baseband) whose time does not discipline the OS clock. Apps get GNSS
      time only on location fixes (for example Android `Location.getTime`,
      the UTC time of the fix), which can differ from
      `System.currentTimeMillis`.
    - GPS is off much of the time: power saving, location permission or
      settings disabled, no sky view, or no fix yet (PA-151).
    - On Linux devices, a GPS receiver affects the clock only if gpsd (or
      similar) is configured to feed chrony or ntpd; otherwise it is
      ignored. NMEA sentence time arrives late with jitter on the order of
      tens to hundreds of milliseconds; precise time needs the PPS signal.
    - At boot, before any source answers, the RTC sets the clock
      (PA-148).
    - Vehicles, trackers, and IoT gateways mix GPS, cellular, NTP, and RTC
      by vendor-specific rules, often undocumented.
    - Receivers' own bugs (week rollover, leap seconds) can make GNSS time
      wrong when it is used (PA-12, PA-151).
  - How it appears in code and operations:
    - Device time treated as GPS-accurate "because the device has GPS".
    - Location fix times and system clock times mixed in one comparison,
      duration, or ordering.
    - gpsd installed but not connected to the time daemon, or NMEA time
      used where PPS precision is needed.
    - Fleet or tracking logic assuming every device uses the same time
      source.
  - What to check:
    - Which source sets each device type's clock, and how the code knows.
    - Mixing of GNSS fix time with the system clock.
    - gpsd and refclock configuration on Linux devices.
  - Fix:
    - Document each device type's time source priority, and treat device
      time as untrusted for decisions (PA-14, PA-103).
    - Use GNSS fix time only as fix time, and do not combine it with the
      system clock without measuring the offset.
    - On Linux devices that should use GPS, connect gpsd to the time
      daemon with PPS where precision matters, and keep network sources
      as cross-checks (PA-148).
    - Record each device's time source and quality with its data
      (PA-94).
  - Not a finding:
    - Apps that treat device time as untrusted and use server time for
      decisions.
  - Escalate (NEEDS-HUMAN): tracking, fleet, or measurement products whose
    devices' time sources are not documented.
  - Proposed severity (for the user to decide): HIGH when tracking,
    billing, evidence, or safety decisions on a core path assume device
    time is GPS time, or mix fix time and system time. MEDIUM for
    unconnected gpsd setups and undocumented device time sources. LOW for
    test-only code.

- PA-153: Correct-GPS assumption. Teams assume that when GPS gives a
  time, that time is correct.
  - Overlap: PA-12 covers week rollover. PA-104 covers leap-second
    announcements. PA-143 and PA-144 cover spoofing and jamming. PA-151
    covers availability and system-level errors. PA-152 covers which
    source sets a device clock. PA-153 covers why a receiver that is
    reporting time can still report the wrong time, and the receiver
    output details code must check. Merged per the class ledgers
    (destination C27.21).
  - Why it is false (receiver and protocol documentation; not verifiable
    from this container, which has no GNSS hardware):
    - GPS time is not UTC. GPS time runs 18 s ahead; receivers convert
      using the UTC parameters in the navigation message, which repeat
      only every 12.5 minutes. After a cold start a receiver can output
      time before it has them, off by the leap-second count, and some
      receivers output GPS time by default (PA-13).
    - Dates come from a week number that wraps: the legacy 10-bit week
      wraps every 1,024 weeks, and receivers infer the era from their
      firmware date, so old firmware can report dates about 19.7 years
      off (PA-12).
    - Validity flags exist and are ignored: NMEA `RMC` has a status field
      (`A` valid, `V` void), and fix-quality and satellite fields in other
      sentences tell whether the time is from a fix. Receivers keep
      outputting time while free-running without a fix.
    - Matching the PPS pulse to the right second is error-prone: whether
      the NMEA sentence after a pulse names that pulse or the next one is
      vendor-specific, and getting it wrong gives a one-second error.
    - Small biases add up: antenna cable delay (roughly 4 to 5 ns per
      metre of coax), receiver internal delays, a wrongly surveyed
      position in timing mode (about 3.3 ns per metre of error), PPS
      quantization ("sawtooth") error, multipath, and ionospheric delay.
      These matter where sub-microsecond accuracy is required.
    - Spoofed signals make a receiver report the attacker's time with a
      valid-looking fix (demonstrated by researchers, for example the
      University of Texas yacht spoofing experiment in 2013) (PA-143).
    - The system can broadcast wrong data (January 2016, about 13
      microseconds, PA-151), and receivers have mishandled leap seconds
      (PA-104).
  - How it appears in code and operations:
    - NMEA parsing that reads the time without checking the `RMC` status
      or fix quality.
    - GPS time used as UTC, or a hardcoded 18 s offset instead of the
      broadcast parameters (PA-13).
    - Week numbers handled modulo 1,024 without an era rule, or dates
      trusted from unsupported firmware.
    - PPS paired with NMEA by assumption, with no check for one-second
      errors (for example against network sources).
    - Precision timing with no cable or receiver delay compensation.
    - No spoofing or jump detection on GNSS time (PA-143).
  - What to check:
    - Receiver output parsing: validity flags, UTC conversion, week
      handling, and PPS pairing.
    - Delay compensation and survey accuracy where precision is required.
    - Cross-checks between GNSS and independent sources.
  - Fix:
    - Use gpsd or the vendor's maintained library rather than hand
      parsing (BP-1; new dependencies need approval), and accept time
      only from valid fixes with UTC parameters received.
    - Take the GPS-to-UTC offset from the receiver's broadcast data, not a
      constant (PA-13).
    - Keep firmware supported and check week-rollover and leap-second
      handling ahead of time (PA-151).
    - Calibrate cable and receiver delays and survey the antenna where
      precision matters.
    - Cross-check GNSS against independent network sources and alarm on
      disagreement or jumps, including whole-second errors (PA-148).
  - Not a finding:
    - Library-handled receivers whose time is cross-checked and monitored.
  - Escalate (NEEDS-HUMAN): precision or regulated timing from GNSS
    without a stated error budget, calibration, and spoofing defense.
  - Proposed severity (for the user to decide): CRITICAL when safety,
    regulated, or security-relevant time accepts GNSS time without
    validity checks or independent cross-checks. HIGH for GPS time used
    as UTC, invalid-fix time accepted, or unhandled week rollover on a
    core path. MEDIUM for missing delay calibration where precision is
    stated, and missing jump alarms. LOW for test-only code.

- PA-154: GPS-precedence assumption. Teams assume GPS time should
  override every other time source available to a system, device,
  software, or application.
  - Overlap: PA-148 covers combining sources and one discipline per
    clock. PA-150 covers choosing the right clock per job. PA-151 and
    PA-153 cover GPS being unavailable or wrong. PA-143 covers spoofing.
    PA-154 covers fixed-priority arbitration ("GPS always wins") and why
    selection must be by health and agreement instead. Merged per the
    class ledgers (destination C27.22).
  - Why it is false (documented unless marked):
    - A fixed priority lets one faulty or spoofed source override several
      sources that agree. A spoofed or misconfigured receiver with a
      valid-looking fix, a whole-second PPS error, or a stale leap offset
      then wins by rule (PA-143, PA-153).
    - Time daemons select by agreement and quality, not rank: NTP's
      selection discards sources outside the majority's intervals. Flags
      that override this are risky: chrony `trust` makes a source exempt
      from being rejected by the others, and `prefer` biases selection
      toward it; marking GPS both turns a check into a dictator.
    - GPS is the best source only while healthy: with a valid fix, UTC
      parameters, calibrated delays, and agreement with independent
      sources. Otherwise holdover or network sources are better
      (PA-122, PA-151).
    - Different jobs need different clocks: elapsed time, ordering, media,
      and decision authority do not come from GPS (PA-150). An app's GPS
      fix time should not override server-assigned authoritative time
      (PA-14, PA-152).
    - Legal or regulated time may be defined by a national authority or
      contract, and GPS-derived UTC needs documented traceability to be
      used there (PA-139, PA-141).
    - GPS gives UTC, not local time: zone and calendar still come from
      tz data and the governing zone (PA-17, PA-35).
  - How it appears in code and operations:
    - Time daemon configs marking the GPS refclock `trust` (and often
      `prefer`) so it cannot be outvoted.
    - Code that sets the system clock from GPS whenever a fix exists,
      without comparing to other sources.
    - App logic that replaces server time or device time with fix time
      unconditionally.
    - Logic deriving local time directly from GPS without a zone source.
  - What to check:
    - Source arbitration rules in configs and code.
    - Use of `trust`, `prefer`, or equivalent overrides.
    - Paths that set the clock or decision time from GPS.
  - Fix:
    - Arbitrate by health and agreement: prefer GPS for precision only
      while it is valid and agrees with independent sources, and fall
      back otherwise (PA-148).
    - Do not mark any single source as trusted beyond outvoting; use
      `prefer` only with enough independent sources to reject it.
    - Keep decision authority on servers, and keep elapsed, ordering, and
      media clocks separate (PA-150).
    - Document the source hierarchy, health criteria, and traceability.
  - Not a finding:
    - GPS preferred within a daemon's agreement-based selection, with
      independent sources able to reject it.
  - Escalate (NEEDS-HUMAN): critical systems whose source arbitration
    policy is not stated.
  - Proposed severity (for the user to decide): CRITICAL when safety,
    regulated, or security-relevant time lets GPS override agreeing
    sources by rule. HIGH for apps replacing authoritative server time
    with fix time on a core path, and for `trust` on a GPS refclock on
    core systems. MEDIUM for undocumented arbitration policy. LOW for
    test-only code.

- PA-155: Harmless-time-service assumption. Teams assume running a time
  service carries no risk, so it needs no securing.
  - Overlap: PA-143 covers attackers shifting clients' time. PA-145
    covers per-family ACLs. PA-146 mentions `monlist` amplification as a
    reason servers filter. PA-155 covers the time service itself (daemon,
    server, and its configuration) as attack surface: exposure, abuse,
    vulnerabilities, privileges, keys, and containers. Merged per the class
    ledgers (destination C27.23).
  - Why it is false (documented; not exercised from this container):
    - Time servers have been abused for denial of service: ntpd's
      `monlist` query (CVE-2013-5211) returned large responses to small
      spoofed requests, and US-CERT alert TA14-013A reported amplification
      factors in the hundreds. Open control queries (ntpd modes 6 and 7)
      also leak version, peers, and configuration.
    - Daemons have had serious vulnerabilities, including remotely
      exploitable buffer overflows in ntpd fixed in 4.2.8 (2014,
      CVE-2014-9295), so unpatched daemons on exposed hosts are a risk.
    - Management interfaces are exposed by mistake: chrony's command port
      (UDP 323) should be bound to localhost, and `cmdallow` kept narrow;
      ntpd needs `restrict ... noquery nomodify` to block remote control.
    - Servers meant for a private network end up open to the internet
      (UDP 123 inbound allowed broadly, `allow` all in chrony), serving and
      exposing themselves to anyone.
    - Privilege matters: setting the clock needs root or `CAP_SYS_TIME`.
      Daemons should drop to an unprivileged user keeping only that
      capability (chrony does with `-u`). Linux time namespaces virtualize
      only the monotonic and boot-time clocks, not the real-time clock, so
      a container granted `CAP_SYS_TIME` (or privileged) can change the
      host's clock for every workload on it.
    - Legacy NTP symmetric-key authentication commonly uses MD5 keys;
      RFC 8573 replaced MD5 with AES-CMAC for NTP. Under this
      repository's rules, MD5 in a security-sensitive context is a
      finding (user Rule 7). Key files readable by other users expose the
      keys.
    - NTS servers hold TLS keys and certificates that need management and
      renewal, and an expired certificate stops NTS clients from syncing
      (PA-137).
    - PTP deployments usually run without authentication and rely on
      network isolation; a reachable PTP network lets anyone become the
      grandmaster (IEEE 1588-2019 adds an optional security annex).
  - How it appears in code and operations:
    - ntpd configs without `restrict default ... noquery nomodify`, or
      older versions without `disable monitor`.
    - chrony with `bindcmdaddress 0.0.0.0` or broad `cmdallow`, or `allow`
      for all addresses on hosts not meant to serve the internet.
    - Security groups or firewalls allowing inbound UDP 123 from anywhere.
    - Time daemons running as root, or unpatched, on exposed hosts.
    - Containers granted `CAP_SYS_TIME` or `privileged: true` to run a
      time daemon or set time (PA-137).
    - NTP `keys` files using MD5 keys, or readable by other users.
    - NTS certificates without renewal; PTP on shared networks.
  - What to check:
    - Time daemon configuration (restrict, allow, command access, keys),
      exposure, version, and the user it runs as.
    - Container and pod capabilities.
    - Key algorithms and file permissions.
  - Fix:
    - Serve time only where intended, restrict queries and control
      (`noquery`, `nomodify`, localhost command ports), and block inbound
      UDP 123 elsewhere, for both address families (PA-145).
    - Patch daemons, and prefer maintained implementations (adding or
      switching implementations needs user approval).
    - Run daemons unprivileged with only `CAP_SYS_TIME`; never grant
      `CAP_SYS_TIME` or privileged mode to containers.
    - Replace MD5 NTP keys with AES-CMAC (RFC 8573) or use NTS; restrict
      key file permissions.
    - Automate NTS certificate renewal and monitor expiry (PA-136).
    - Isolate PTP networks, or use its security mechanisms where
      supported.
  - Not a finding:
    - Hardened, patched internal time servers serving only their intended
      networks, with restricted control access.
  - Escalate (NEEDS-HUMAN): time servers whose exposure, patch level, or
    configuration is outside the review unit.
  - Proposed severity (for the user to decide): CRITICAL when a container
    or untrusted workload can set a shared host's clock (`CAP_SYS_TIME` or
    privileged), or a time daemon with known remote-code-execution flaws
    is exposed. HIGH for amplification-capable or remotely controllable
    servers, MD5 NTP keys in security-relevant use (user Rule 7), and
    open serving on hosts not meant to serve. MEDIUM for daemons running
    as root, readable key files, and unmonitored NTS certificate expiry.
    LOW for test-only code.
