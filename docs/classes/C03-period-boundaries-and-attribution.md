# C3 Period boundaries and attribution

(sources: PA-5, 6, 7, 57, 135; inbound from PA-4, PA-45) Approved by the user.

Scope: where days, weeks, months, and years begin and end, which period
a span belongs to, and how ranges are closed. Week starts and weekday
rules are C4. Fiscal and tax calendars are C5. Week-year labels are C24.
Times at or past 24:00 in input are C23. Missing local midnights are C11.

- C3.1 Spans that cross period boundaries.
  - Facts: any span that does not start at a boundary crosses one: a
    24-hour window, a shift, a stay, a rental, a week, or a billing cycle
    can cross a day, week, month, or year. The week containing January 1
    usually starts in December (ISO week 1 of 2026 starts 2025-12-29,
    verified). Some years have an ISO week 53 (2020, 2026, 2032,
    verified). Islamic months can cross Gregorian years. Fiscal, tax,
    academic, and Hebrew years do not start on January 1 (details in C5,
    C6).
  - In code: grouping, bucketing, or partitioning by span start only.
    Using the start's date, week, month, or year for both ends.
    `start.date() == end.date()` assumptions. Daily file names, cache
    keys, and partitions from the span start. Month-end or year-end
    batches selecting by start. Weekly records assigned to the month or
    year of the week start. Monthly totals summed from weekly totals, and
    annual totals summed from 52 weeks, dropping week 53 or counting a
    straddling week twice. Billing cycles, subscriptions, and accruals
    across December 31 credited to one year. Overnight shifts and
    per-day overtime ignored.
  - Fix: state the attribution rule in the requirement (by start, by end,
    split, by overlap, or by majority, such as the ISO-style Thursday
    rule). Split spans at boundaries in the defining zone with library
    interval tools (for example Luxon `Interval.splitAt` and
    `Interval.splitBy`). Build month and year totals from daily data, or
    split straddling periods.
  - Not a finding: a documented attribution rule that the code follows.
    Periods defined in whole weeks by design (4-4-5 fiscal calendars).
  - Escalate: payroll, overtime, billing, tax, compliance, or regulatory
    limits and reports where the attribution rule for spans across
    boundaries is not stated.
- C3.2 Rolling windows versus calendar periods.
  - In code: daily quotas or rate limits that mix a rolling 24-hour
    window with a calendar-day reset, granting double quota or locking
    users out across midnight.
  - Fix: choose one per quota.
  - Not a finding: rolling windows never mapped onto calendar periods.
- C3.3 Boundaries depend on the zone.
  - Facts: the same span can sit inside one UTC day and cross a local
    boundary. Local January in Tokyo starts at 2026-12-31 15:00 UTC. A New
    York event at 2026-12-31 20:00 is 2027-01-01 01:00 UTC (verified).
    Local month boundaries are different instants in each zone.
  - In code: day, month, or year taken from a UTC instant for something
    whose period is local. Events near New Year land in the wrong year.
  - Fix: derive periods from the local date in the defining zone (C14
    covers which zone defines it).
  - Escalate: annual or regulatory reporting without a stated defining
    zone.
- C3.4 Weeks against months.
  - Facts: most months start and end mid-week. A month covers 4, 5, or 6
    calendar weeks (Sunday-start 2026: February 4, March 5, August 6,
    verified).
  - In code: "week of month" as `ceil(day / 7)`. Month grids fixed at 4
    or 5 rows, hiding days in 6-week months. Weekly payroll, invoices, or
    digests reconciled against months by week-start month.
  - Fix: state the week-to-month rule. Size month grids from the
    library's count of weeks in the month.
  - Escalate: weekly payroll, billing, or compliance reports crossing a
    month-end close without a stated rule.
- C3.5 Day boundaries other than midnight.
  - Facts: religious days start at sunset (Hebrew and Islamic days, the
    Sabbath). Julian Day numbers start at noon UTC, and the Modified
    Julian Date at midnight (`MJD = JD - 2400000.5`). Operational days have
    their own cutoffs: hotel nights, exchange sessions opening the
    previous evening (for example CME Globex), casino gaming days, bank
    cutoffs, retail business dates, broadcast days (for example 06:00 to
    05:59), and night shifts belonging to their start day. GTFS service
    days are measured from noon minus 12 hours, which differs from
    midnight on DST change days. Swahili time counts hours from about
    06:00. Polar regions have no daily morning. Users treat late night as
    part of the previous day.
  - In code: business, service, or trading days cut at midnight.
    Religious-calendar features switching dates at midnight. Julian Day
    conversions off by half a day. Daily user metrics resetting at
    midnight against the product's promise.
  - Fix: model each domain day explicitly with a cutoff and zone. Compute
    sunset-based days with an astronomy library and the location. Convert
    Julian Days with a library. Offer a configurable day boundary where
    the product promises "your day".
  - Not a finding: midnight-bounded calendar days where the domain uses
    calendar days.
  - Escalate: domain day concepts without a stated cutoff and zone.
- C3.6 End of day and range closure.
  - Facts: 23:59:59 is not the end of a day. Values such as 23:59:59.5 come
    after it. 23:59:59.999 still misses 23:59:59.9995, and values written
    at higher precision can round up into the next day. A leap second,
    23:59:60, comes after it. 23:59:59 can happen twice: in Santiago on
    2026-04-04 at -03:00 and again at -04:00 (verified). Days vary in
    length or are skipped. "End of day" in business or law may mean close
    of business, such as 17:00. Spreadsheets approximate end of day as
    date plus 0.99999.
  - In code: closed ranges such as `BETWEEN '... 00:00:00' AND
    '... 23:59:59'` (including February ranges ending on 02-28, C2.3).
    Deadlines stored as 23:59:59 or 23:59:59.999 and compared with `<=`.
    Date-only values turned into end-of-day timestamps for comparison.
    Literal 23:59:59, 23:59:59.999, or 0.99999 near date logic.
  - Fix: use half-open ranges (`>= start AND < next start`), with both
    starts computed by the library in the governing zone. Express
    deadlines as the first instant after the deadline and compare at full
    precision. State what "end of day" means in the requirement (C26).
  - Not a finding: 23:59:59 as a display convention with a half-open
    comparison behind it.
  - Escalate: "end of day" deadlines without a stated zone or business
    meaning.
- Proposed severity (for the user to decide), per check: HIGH when a
  boundary or attribution error misstates pay, charges, revenue, tax,
  quotas, annual caps, legal limits, settlements, hotel billing,
  trading, transit schedules, religious observance dates, or regulated
  reports, drops records, or accepts or rejects the wrong submissions on
  a core path. MEDIUM for reports, analytics, labels, user metrics, and
  calendar UIs that hide days. LOW for test-only code.

Point ledger for C3:
- Inbound from PA-4: half-open range fix -> C3.6.
- Inbound from PA-45: local month boundaries differ by zone -> C3.3.
- PA-5: boundary crossing facts, grouping by start, start date for both
  ends, `start.date() == end.date()`, overnight billing, file names and
  partitions, month-end and year-end batches, attribution fix, splitting
  fix, attribution not-a-finding, payroll escalation -> C3.1. Rolling
  versus calendar quotas and their fix and not-a-finding -> C3.2. Zone
  dependence and what-to-check zone -> C3.3. DST 24-hour span ending at
  23:00 or 01:00 -> C1.2. Week start by locale and fiscal boundaries ->
  C4 and C5 (inbound). Half-open fix -> C3.6. Severity -> C3 severity.
- PA-6: mid-week month starts, 4/5/6 weeks, `ceil(day / 7)`, grids,
  weekly payroll reconciliation, week-to-month rule fix, grid fix,
  escalation -> C3.4. Weekly records by week-start month, monthly totals
  from weekly totals, totals-from-daily fix -> C3.1. Week start by locale
  and hardcoded week start, library week-start fix -> C4 (inbound).
  Straddling week assigned to either ISO year -> C3.1. 4-4-5 not-a-finding
  -> C3.1. Documented rule not-a-finding -> C3.1. Severity -> C3 severity.
- PA-7: ISO week 1 starting in December, week 53 years, lunar months
  across years, years not starting January 1, weekly records by year,
  annual totals, billing across December 31, attribution fix, totals
  fix, documented-rule not-a-finding, tax-year escalation -> C3.1. Tokyo
  and New York UTC year examples, UTC-year code, local-date fix, zone
  escalation -> C3.3. `%Y-W%V` labels, week-label check, ISO week-year
  pairing fix, ISO reporting not-a-finding -> C24 (inbound). Fiscal or
  tax year computed as calendar year -> C5 (inbound). Severity -> C3
  severity.
- PA-57: midnight and missing midnights -> C3.5 and C11 (inbound
  reference). Sunset days, JD and MJD, operational days, GTFS service
  day, Swahili time, polar regions, users' "last night", midnight-cut
  business days, religious switching, JD errors, metric resets, domain-day
  fix, sunset fix, JD fix, configurable boundary, not-a-finding,
  escalation -> C3.5. Parsers rejecting `24:00` or `25:30` and GTFS times
  as clock times, GTFS parsing fix -> C23 (inbound). Severity -> C3
  severity.
- PA-135: all facts, code patterns, checks, fixes, not-a-finding, and
  escalation -> C3.6. Severity -> C3 severity.
