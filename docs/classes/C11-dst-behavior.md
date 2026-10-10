# C11 DST behavior

(sources: PA-36, 37, 38, 61, 110, 111, 129; inbound from PA-9, PA-92, C3.5, C7.3, C8.3, C10.2) Approved by the user.

Scope: when and how DST transitions happen, how large they are, how
they differ between zones, how DST is represented, and how code handles
skipped and repeated local times. Rule changes and tz data are C10.
Differences between zones are C12. Day and hour lengths are C1.
Scheduling at local times is C18.

- C11.1 Transition dates and times move.
  - Facts (tzdata 2026b, verified): rules are relative, so dates move
    (New York 2026-03-08 and 2026-11-01, then 2027-03-14 and 2027-11-07).
    Local transition times differ: US zones at 02:00 local, EU zones
    together at 01:00 UTC, some zones at midnight (Santiago: 23:59 on
    2026-09-05 is followed by 01:00). Rules change (US 2007, Energy Policy
    Act of 2005). Some rules follow religious or lunar calendars:
    Morocco's Ramadan suspension moves about 11 days earlier each year
    (2026-02-15 to 2026-03-22, 2027-02-07 to 2027-03-14), and Iran's
    former DST followed Persian dates until abolished in 2022. Some years
    skip DST by decision (Fiji 2022).
  - In code: hardcoded transition dates, DST tested by month range
    (`month in 4..10`), hand-written rules ("last Sunday of October")
    outdated or applied to the wrong zones, hand-rolled detection by
    comparing January and July offsets in JS, tests pinned to one year's
    dates.
  - Fix: never hardcode transitions. Ask the library for the offset at
    the instant or for the next transition (Java
    `ZoneRules.nextTransition`) (BP-1). Test several years, both
    hemispheres, Santiago, Morocco, and Dublin.
  - Not a finding: library-driven offset handling with no hand-coded DST
    logic.
  - Escalate: business rules written as "DST periods" without a stated
    zone and rule source.
- C11.2 Shift size and DST flags.
  - Facts (verified): Lord Howe shifts 30 minutes (+10:30 to +11:00),
    Troll 2 hours (+00:00 to +02:00). The UK ran +01:00 all year with
    +02:00 summers during the Second World War. Ireland's winter time is
    negative DST in tzdata's main format, and some builds use a format
    that does not model it: this host reports 0 DST for Dublin in January
    and 1 hour in July. Morocco drops an hour for Ramadan. Governments can
    choose any shift size.
  - In code: `offset + 60`, `hour += 1`, or `timedelta(hours=1)` applied
    when DST is active. A DST boolean stored and the offset rebuilt as
    standard plus one hour. Gaps and overlaps assumed to be 60 minutes.
    Validators or controls allowing only whole-hour shifts. Logic keyed
    on `isDST` instead of the actual offset.
  - Fix: get the full offset for each instant, and store the zone ID or
    full offset, never a DST boolean. Get gap and overlap size from the
    library (Java `ZoneOffsetTransition.getDuration()`). Test Lord Howe,
    Troll, Dublin, and historical London.
  - Not a finding: library-driven offsets with no hand-coded shift size.
- C11.3 Transitions differ by zone and instant.
  - Facts (verified): zones under one rule switch at different instants.
    US zones switch at 02:00 local, so New York minus Chicago is 2 hours
    from 07:00 to 08:00 UTC on 2026-03-08 and 0 hours from 06:00 to 07:00
    UTC on 2026-11-01. EU zones switch together. Hemispheres run opposite
    seasons, and many zones never observe DST (most of Asia and Africa,
    Arizona, Hawaii, Saskatchewan, Queensland). Transitions fall in other
    zones' working hours: the US change at 07:00 UTC on Sunday 2026-03-08
    is 09:00 in Jerusalem, 10:00 in Riyadh, 11:00 in Dubai, and 12:30 in
    Kolkata, where Sunday is a working day in Israel and Saudi Arabia; the
    EU change at 01:00 UTC on 2026-03-29 is 10:00 in Tokyo and 12:00 in
    Sydney. Many operations run around the clock, governments can set
    transitions at any hour, travelers' offsets change on landing, and a
    tz update deployed mid-day changes computed offsets from that moment.
  - In code: one global DST flag (`DST_ACTIVE = true`) or "+1 hour in
    summer" for every user. Per-region schedules derived from one
    reference zone. Global jobs, maintenance windows, or alert suppression
    at one instant "after the DST change". Offsets for all regions cached
    per day from the server zone. DST handling skipped in "business hours
    only" features. Offset computed at the start of the business day and
    reused until close. Schedulers assuming the 09:00 offset holds until
    17:00 for every participant.
  - Fix: compute offsets per zone, per instant, with the library. No
    global DST state and no per-day offset caches. Schedule cross-region
    work per region, or in UTC with per-region local handling. Treat every
    served zone, assume activity at any hour unless the requirement
    limits it, and recompute after tz updates (C10.3). Test the hours
    between zones' transition instants.
  - Not a finding: per-zone, per-instant offset computation.
  - Escalate: global operations planned around "the DST change", or
    multi-region business-hours features, where the zones and their
    working calendars are not stated.
- C11.4 DST periods are not one per calendar year.
  - Facts (verified, sampling every 6 hours from 2000 to 2026):
    southern-hemisphere DST crosses New Year (Sydney +11:00 from
    2026-10-04 to 2027-04-04), so every calendar year holds the end of
    one period and the start of the next. Years with two DST periods
    occurred in Cairo (2010, 2014: +03:00 from 2014-05-16, back on
    06-26, again from 08-01, ending 09-25), Casablanca (2012, 2013, 2015
    to 2017), and Hebron (2011), 15 zone-years in all. A period can start
    and not end (Moscow +04:00 from 2011-03-27 to 2014-10-26; Turkey from
    2016; Paraguay 2024), or end and not restart (Mexico 2022). Historical
    all-year and double summer time (UK 1968 to 1971, wartime).
  - In code: one `(start, end)` pair per calendar year with
    `start <= date < end`, failing when start is after end. Year-keyed
    tables with exactly one start and end. Validation rejecting more than
    two transitions a year. Seasonal pricing or "summer rates" defined by
    DST per calendar year. Year loops computing "the" DST period.
  - Fix: ask for the offset at each instant, or iterate the zone's actual
    transitions, with no fixed count per year (BP-1). Define seasonal
    business rules by explicit date ranges that may cross the year. Test
    southern-hemisphere zones, Cairo 2010 and 2014, Casablanca 2012 to
    2017, Hebron 2011, and Moscow 2011 to 2014.
  - Not a finding: library offset lookups with no per-year DST model.
  - Escalate: seasonal rules linked to "summer time" without a stated
    zone and period definition.
- C11.5 Fixed offsets standing in for DST zones.
  - Facts (verified with `date`): `TZ=EST5` gives 07:00 EST at 12:00 UTC
    in both January and July, while `TZ=EST5EDT` and
    `TZ=America/New_York` give 08:00 EDT in July. `EST5EDT` follows
    built-in rules that a future rule change would not update. Schedules
    in UTC drift in local time: 14:00 UTC is 09:00 New York in January
    and 10:00 in July. Fixed offsets also appear as Java short ID "EST"
    (C13), `Etc/GMT+5` (C13), session settings, cloud scheduler
    expressions, invites, and year-round "9am EST" text.
  - In code: `TZ=EST5`, fixed-offset zone objects in configuration, cron
    or cloud schedules in UTC meant to run at a local time, offsets stored
    for users, sites, or events (C10.1), year-round "EST" or "PST" in UI
    and documentation.
  - Fix: use IANA IDs in configuration (`TZ=America/New_York`). Run
    local-time schedules with a zoned scheduler or compute each run in the
    zone (C18). Write "Eastern Time" or the zone ID in text.
  - Not a finding: fixed offsets for places without DST, documented
    (Arizona outside the Navajo Nation, Bogota).
  - Escalate: schedules or SLAs stated in a fixed offset where the
    intended local time is not stated.
- C11.6 Skipped and repeated local times.
  - Facts (verified for New York): libraries resolve gaps and overlaps
    with silent defaults. Python accepts 02:30 on 2026-03-08 with -05:00,
    and a UTC round trip turns it into 03:30-04:00; in the repeated hour
    on 2026-11-01, 01:30 takes -04:00 with `fold=0` and -05:00 with
    `fold=1`. JS `new Date(2026, 2, 8, 2, 30)` becomes 03:30 EDT and the
    repeated 01:30 picks EDT. Java `ZonedDateTime.of` shifts skipped
    times forward (C7.3). Each default is a policy decision. Some local
    midnights do not exist (Santiago, C11.1), so start of day is not
    always 00:00 (C3.5, C8.3). Rule changes can create new gaps in stored
    future local times (C10.2).
  - In code: no explicit handling or documented policy for skipped and
    repeated local times. Local midnight constructed by hand (`date +
    00:00`). Zone-less local timestamps in the repeated hour stored as if
    unique.
  - Fix: state the gap and overlap policy (shift forward, earlier, later,
    or reject) and apply it explicitly with the library's strict or
    explicit-offset APIs. Get start of day from the library (Java
    `LocalDate.atStartOfDay(zone)`, Luxon `startOf('day')`). Store
    instants or offsets with local times (C9.2).
  - Not a finding: library defaults the team has reviewed, documented,
    and tested as the intended policy.
  - Escalate: local-time features (jobs, appointments, deadlines) inside
    gaps or overlaps without a stated policy (job scheduling detail in
    C18).
- Proposed severity (for the user to decide), per check: HIGH when
  hardcoded transitions, a one-hour shift assumption, a global DST flag,
  an offset cached across a transition, a per-year DST model, a fixed
  offset for a DST zone, or an unexamined gap or overlap default drives
  scheduling, billing, SLAs, or deadlines on a core path. MEDIUM for
  display, seasonal reports, monitoring windows, documentation, and
  historical data. LOW for test-only code.

Point ledger for C11:
- Inbound from PA-9: hand-written DST rules -> C11.1.
- Inbound from PA-92: Python, JS, and Java gap and overlap defaults,
  each-default-is-policy -> C11.6.
- Inbound from C3.5: missing local midnights -> C11.6.
- Inbound from C7.3: library defaults as unexamined policy -> C11.6.
- Inbound from C8.3: missing local midnight (Santiago 2026-09-06) ->
  C11.6.
- Inbound from C10.2: gap and overlap policy after rule changes ->
  C11.6.
- PA-36: relative rules, transition times, Santiago midnight, 2007,
  Morocco and Iran, Fiji, hardcoded dates, month ranges, hand rules,
  January-July detection, pinned tests, library fix, multi-year tests,
  not-a-finding, escalation -> C11.1. Southern-hemisphere New Year ->
  C11.4. DST flags and Dublin -> C11.2. Missing midnight, start-of-day
  fix -> C11.6. Severity -> C11 severity.
- PA-37: rolling US transitions, EU together, hemispheres, non-DST
  zones, global flag, single adjustment, reference-zone schedules,
  global jobs, cached offsets, per-zone fix, regional scheduling,
  transition-hour tests, not-a-finding, escalation -> C11.3. Severity ->
  C11 severity.
- PA-38: Lord Howe, Troll, wartime UK, negative and suspended DST, any
  size, hour adjustments, flag-rebuilt offsets, 60-minute gaps,
  whole-hour controls, full-offset fix, transition duration, tests,
  not-a-finding -> C11.2. 23- and 25-hour days -> C1.2. Severity -> C11
  severity.
- PA-61: Jerusalem, Riyadh, Dubai, Kolkata, Tokyo, Sydney examples,
  round-the-clock operations, any-hour transitions, travelers, mid-day
  tz updates, skipped DST handling, per-day offsets, schedulers,
  multi-region office-hours jobs, per-instant fix, all-zones fix,
  any-hour fix, recompute fix, not-a-finding, escalation -> C11.3.
  Severity -> C11 severity.
- PA-110: Sydney, Egypt 2014, Moscow 2011 to 2014, Turkey, Paraguay,
  Mexico, historical all-year time, per-year pair model, year tables,
  seasonal pricing, year loops, library fix, date-range fix, tests,
  not-a-finding, escalation -> C11.4. Severity -> C11 severity.
- PA-111: 15 zone-years, Cairo, Casablanca, Hebron, southern-hemisphere
  years, Morocco format dependence, wartime double summer time,
  transition-count validation, single-window "is DST", one summer
  period, iterate fix, tests, not-a-finding -> C11.4. Severity -> C11
  severity.
- PA-129: `TZ` string results, `EST5EDT` built-in rules, UTC schedule
  drift, fixed-offset locations, configuration, UTC cron, stored
  offsets, year-round EST text, IANA fix, zoned scheduler fix, text fix,
  not-a-finding, escalation -> C11.5. Severity -> C11 severity.
