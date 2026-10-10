# C4 Weeks, weekdays, weekends, holidays

(sources: PA-48, 56, 58, 59; inbound from PA-3, PA-5, PA-6) Approved by the user.

Scope: weekday sequence and numbering, week start and week numbering,
weekends, holidays, and business-day calendars. Span attribution across
weeks and months is C3. Fiscal weeks and 52/53-week fiscal years are C5.
Historical calendars and skipped dates are C6. Business-hours arithmetic
is C7. Week-year format tokens and labels are C24. Which zone governs a
weekday is C14.

- C4.1 Weekday sequence and derivation.
  - Facts: date-line moves skip weekdays: Samoa went from Thursday
    2011-12-29 to Saturday 2011-12-31, Kwajalein from Friday 1993-08-20 to
    Sunday 1993-08-22, the Philippines from Monday 1844-12-30 to Wednesday
    1845-01-01. Alaska repeated a day in 1867. Reform kept the weekday
    sequence while jumping the date (Thursday 1582-10-04 Julian, then
    Friday 1582-10-15), and proleptic Gregorian libraries call 1582-10-04
    a Monday (verified). Other week lengths existed (Soviet 5- and 6-day
    weeks 1929 to 1940, French Republican 10-day weeks). One instant falls
    on different weekdays in different zones.
  - In code: "day before Saturday is Friday" logic. Weekday taken from a
    UTC or server date instead of the local date. Weekdays computed for
    Julian-dated records with proleptic rules.
  - Fix: do date arithmetic first, then ask the library for the weekday
    of the resulting local date in the relevant zone and calendar (zone
    choice C14, historical calendars C6).
  - Not a finding: library-derived weekdays for modern local dates.
- C4.2 Weekday numbering across systems.
  - Facts: Monday = 1 to Sunday = 7 (ISO 8601, Java `DayOfWeek`, Python
    `isoweekday()`). Monday = 0 (Python `weekday()`, MySQL `WEEKDAY`).
    Sunday = 0 (JS `getDay()`, .NET `DayOfWeek`, Postgres `EXTRACT(DOW)`).
    Sunday = 1 (MySQL `DAYOFWEEK`). SQL Server depends on `SET DATEFIRST`.
    cron accepts Sunday as 0 or 7.
  - In code: weekday numbers passed between systems with different
    conventions. Modulo arithmetic on weekday numbers: `(day - 1) % 7` is
    -1 for Sunday = 0 in JS, Java, and C, but 6 in Python (verified).
  - Fix: map conventions explicitly at every boundary, or exchange ISO
    numbers or names. Use floor modulo or library weekday arithmetic.
  - Not a finding: one documented convention used end to end.
- C4.3 Week start and week numbering.
  - Facts: week start varies by locale (CLDR via Node `Intl.Locale`,
    verified): Monday (`en-GB`, `de-DE`, minimum 4 days in week 1),
    Sunday (`en-US`, `he-IL`, `ja-JP`, `pt-BR`, `en-IN`, minimum 1 day),
    Saturday (`ar-EG`, `fa-IR`), Friday (`dv-MV`). Week numbers depend on
    start day and minimum days: Sunday 2026-01-04 is week 01 under `%U`,
    00 under `%W`, and ISO week 01 under `%V` (verified). Tool defaults
    differ: Postgres `date_trunc('week')` Monday; MySQL `WEEK()` mode 0
    Sunday; SQL Server `DATEFIRST`; BigQuery `WEEK` Sunday with
    `WEEK(MONDAY)` and `ISOWEEK` separate; Excel `WEEKNUM` Sunday versus
    `ISOWEEKNUM`; Luxon `startOf('week')` Monday unless `useLocaleWeeks`;
    date-fns `startOfWeek` Sunday; moment locale-dependent. Users can set
    their own week start. ISO week-years have 364 or 371 days and start
    on a Monday near January 1 (2027-01-01 is in ISO week 53 of 2026,
    verified).
  - In code: week start hardcoded to Monday or Sunday for all users.
    Database and application weekly buckets using different starts, so
    totals disagree between layers. Week numbers from one convention
    joined or labeled with another. "This week" filters disagreeing with
    the calendar UI. Implicit tool defaults.
  - Fix: choose the week definition per feature (ISO, locale, or user
    preference) and state it in the requirement. Configure it explicitly
    in every layer, never by default, for example Luxon
    `startOf('week', { useLocaleWeeks: true })` or ISO weeks on purpose.
    Use one definition for bucketing and labeling across the stack. Test
    boundaries on Friday through Monday and at year ends.
  - Not a finding: a documented, explicitly configured week definition
    used consistently across layers.
  - Escalate: weekly reports, payroll weeks, or calendar views in
    multi-locale products without a stated week definition.
- C4.4 Weekends.
  - Facts: CLDR reports (verified) Saturday-Sunday for `en-US` and
    `ar-AE`, Friday-Saturday for `ar-SA`, `ar-EG`, `he-IL`, Friday only
    for `fa-IR`, Sunday only for `en-IN`. Locale data is not
    authoritative: the same build reports Saturday-Sunday for `bn-BD` and
    `dv-MV`, where government offices close Friday and Saturday (practice
    to confirm per deployment). Weekends change: Saudi Arabia moved from
    Thursday-Friday to Friday-Saturday in 2013, the UAE from
    Friday-Saturday to Saturday-Sunday in 2022 with a Friday half day,
    and Malaysian states differ and have switched. Weekends differ by
    sector, organization, shift pattern, and four-day weeks. Markets keep
    their own trading weeks (the Saudi exchange trades Sunday to
    Thursday). Swapped working days turn weekend days into workdays
    (C4.5).
  - In code: `is_weekend = weekday in (SATURDAY, SUNDAY)`. Business-day
    arithmetic (delivery, settlement T+N, SLA timers) skipping Saturday
    and Sunday only. Weekend surcharges fixed to Saturday and Sunday.
    Historical business days computed with today's weekend. Locale
    weekend data used as the business authority.
  - Fix: define weekends in an effective-dated business calendar per
    region and organization. Use locale data only as a display default.
    Combine weekends, holidays, and swapped workdays in one business-day
    service. Support per-site or per-employee patterns where shifts
    differ.
  - Not a finding: single-region products with a documented
    Saturday-Sunday business calendar applied through one service.
- C4.5 Holidays and business-day calendars.
  - Facts: holidays can be partial days (December 24 and 31 half days, US
    exchanges closing at 13:00 Eastern on some days). Jewish holidays and
    the Sabbath run sunset to nightfall (Yom Kippur about 25 hours), and
    Islamic holidays start at sunset after a sighting (sunset days C3.5).
    A DST change inside a holiday changes its length (Easter Sunday
    2024-03-31 lasted 23 hours in Berlin, verified). Holidays differ by
    state, province, canton, and city. Ad hoc holidays are declared at
    short notice (UK 2022-09-19, about ten days ahead), and sighted
    holidays are confirmed a day before. Weekend holidays move to observed
    weekdays, and some countries swap weekend days into workdays (China's
    adjusted working days). Bank, exchange, school, and company calendars
    differ. Floating or personal holidays apply to some employees. A
    company-wide holiday falls at different instants per office zone.
  - In code: holiday tables as plain date lists and boolean
    `is_holiday(date)`. Business-hours and SLA timers pausing only for
    whole holiday dates (business-hours arithmetic C7). "Previous business
    day" coded as "if Saturday, use Friday". Market calendars without
    early closes. One global list with no regional scope. Static lists
    with no update path. Weekend days always non-working. Holiday pay as
    `days * 24` or fixed hours per day (day length C1.2).
  - Fix: model holidays as local-time intervals with zone, region, and
    purpose, supporting partial days. Keep separate calendars per
    purpose. Use a maintained holiday source with an update process, and
    audited operator additions for ad hoc holidays. Support observed
    dates and swapped workdays. Compute sunset starts with an astronomy
    library and location (C3.5). Compute durations from interval
    instants (C1.2). Movable feasts from other calendars come from C6.
  - Not a finding: interval-based, region-scoped holiday calendars from a
    maintained source.
  - Escalate: SLA, settlement, payroll, or multi-country business-day
    rules where the weekend, holiday calendar, region, and partial-day
    rules are not stated.
- Proposed severity (for the user to decide), per check: HIGH when the
  wrong weekday, week definition, weekend, or holiday data drives
  settlement, payroll, delivery, trading, SLA deadlines, billing, or
  regulated weekly reports on a core path. MEDIUM for pricing, calendar
  UIs, analytics, scheduling, and display. LOW for test-only code.

Point ledger for C4:
- Inbound from PA-3: ISO week-years (364 or 371 days, boundaries off
  January 1, 2027-01-01 in week 53 of 2026) -> C4.3. 52/53-week fiscal
  years -> C5 (inbound).
- Inbound from PA-5: week start by locale -> C4.3. Fiscal boundaries ->
  C5 (inbound).
- Inbound from PA-6: week start by locale, hardcoded week start,
  week-start-source check, library week-start fix -> C4.3.
- PA-48: date-line weekday skips, Alaska repeat, reform weekday
  continuity, proleptic weekday error, Soviet and French weeks, zone
  dependence, "day before Saturday" logic, UTC or server weekday,
  historical weekdays, calendar-and-zone fix, library not-a-finding ->
  C4.1. Original-calendar fix for historical dates -> C6 (inbound).
  Numbering table, modulo bug, boundary enums (SQL, cron), mapping fix ->
  C4.2. Regional weekends, UAE 2022, hardcoded weekends -> C4.4.
  "Previous business day" logic, business-day calendar fix,
  multi-country escalation -> C4.5. Severity -> C4 severity.
- PA-56: all locale week starts, minimum days, `%U`/`%W`/`%V`, tool
  defaults, user preference, hardcoded starts, cross-layer buckets,
  mixed conventions, "this week" filters, what to check, per-feature
  definition, explicit configuration, single definition, boundary tests,
  not-a-finding, escalation -> C4.3. Year-boundary test reference -> C3.1.
  Severity -> C4 severity.
- PA-58: half days, early closes, sunset holidays, Berlin Easter DST,
  regional scope, ad hoc holidays, substitute and swapped days, purpose
  calendars, floating holidays, per-office instants, date-list models,
  whole-date SLA pauses, early-close gaps, global lists, static lists,
  swapped workdays, what to check, interval model, purpose calendars,
  maintained source, observed dates, not-a-finding, escalation -> C4.5.
  Sunset computation -> C4.5 with C3.5. Holiday pay `days * 24` and
  durations from instants -> C4.5 with C1.2. Movable holidays from other
  calendars -> C6 (PA-41, already there). Severity -> C4 severity.
- PA-59: CLDR weekends, non-authoritative locale data, weekend changes
  (Saudi 2013, UAE 2022, Malaysia), sector and organization differences,
  market weeks, hardcoded weekends, Saturday-Sunday business-day
  arithmetic, weekend surcharges, historical weekends, locale data as
  authority, what to check, effective-dated calendar, display-only locale
  data, per-site patterns, not-a-finding -> C4.4. Swapped working days
  and combined business-day service -> C4.4 with C4.5. Escalation ->
  C4.5 (combined business-day escalation). Severity -> C4 severity.
