# C1 Calendar unit lengths

(sources: PA-1, 2, 3, 4, 39, 45, 102) Approved by the user.

Scope: hours, days, months, and years have no fixed length. Arithmetic
with them is C7. Leap rules and inserted days are C2. Historical and
non-Gregorian calendars are C6. Fiscal periods are C5.

- C1.1 Hour length varies.
  - Facts: a UTC hour with a leap second lasts 3601 s, and smeared hours
    hold longer seconds. Local DST hours happen twice or not at all.
    Seasonal (unequal) hours in religious law and older systems change
    with season and latitude. Sun-position prayer times move daily.
    Sidereal hours last about 59.84 min and Mars hours about 61.65 min.
    Decimal and alternative systems (French Revolutionary, Swatch beats)
    use other units. UT1 days vary by milliseconds.
  - In code: religious times computed with fixed 60-minute hours or
    fixed sunrise offsets. Sidereal, solar, and planetary hours mixed.
    Hourly billing or metrics bucketed by local hour on DST days. Wrong
    conversion constants for alternative units.
  - Fix: name the time system for each hour-based calculation. Use
    maintained libraries for religious, astronomical, and planetary time
    (new dependencies need user approval). Bucket by UTC hour or by
    instant ranges, and label local hours on DST days.
  - Not a finding: SI hourly calculations on UTC instants.
  - Escalate: religious, astronomical, or space features without a stated
    time system and accuracy.
- C1.2 Day length varies.
  - Facts: local days last 23 or 25 hours at DST changes, 23.5 or 24.5 on
    Lord Howe Island, and 22 or 26 at Troll Station. A zone change can
    remove a day (Samoa skipped 2011-12-30). A UTC day with a leap second
    lasts 86,401 s.
  - In code: `86400`, `86400000`, or `24*60*60*1000` added for "tomorrow"
    and shown in local time. Day counts as `(b - a) / 86400000`. Day loops
    stepping 24 hours. 24 hourly buckets assumed per day. Literal 1440.
  - Fix: count days on local dates. Bucket by local date and allow 23, 24,
    or 25 hours. For adding days, see C7.
  - Not a finding: a fixed 86,400 s TTL where the requirement is elapsed
    time on UTC instants. UTC-only systems with no local-day semantics.
- C1.3 Month length varies.
  - Facts: Gregorian months have 28 to 31 days. Hours per month vary with
    DST (743 or 745 local hours in a 31-day month with a change, 744
    elsewhere). The same month has different lengths in different places
    (December 2011 had 30 days in Samoa and 31 in Auckland, verified).
  - In code: hand-written days-in-month tables. "One month" as 30 days or
    2,592,000 s. "Last day of month" hardcoded to 28, 30, or 31.
    Assertions or grids that allow only 28 to 31 slots. Month length in
    hours as `days * 24`. One global days-in-month table for all regions.
    Maximum day-of-month used as the number of days.
  - Fix: get month length from the library for the specific month, zone,
    region, and calendar. Compute hours from the month's local boundaries.
    Count days by iterating dates.
  - Not a finding: named financial day-count conventions (30/360,
    Actual/360). Library-derived 28-to-31 validation in Gregorian-only,
    single-region products.
  - Escalate: multi-region monthly billing or proration without a stated
    defining zone or region for "the month".
- C1.4 Year length varies.
  - Facts: Gregorian years have 365 or 366 days, and some local years lost
    or gained days (Samoa 2011: 364).
  - In code: "one year" as 365 days or 31,536,000 s, or 365.25 days or
    31,557,600 s, or 8,760 hours. Age or tenure as `days / 365` or
    `days / 365.25`. Day-of-year arrays or loops sized 365 (day 366
    overflows; Zune freeze 2008-12-31, Azure outage 2012-02-29).
  - Fix: add years with the library (C7). Compute age by comparing year,
    month, and day. Size day-of-year structures for 366.
  - Not a finding: Actual/365 Fixed and similar named conventions. A
    requirement that defines exactly 365 elapsed days.
  - Escalate: "valid for one year" with no definition of calendar year
    versus 365 days.
- Proposed severity (for the user to decide), per check: HIGH when the
  value drives money, billing, renewals, deadlines, expiry, legal age,
  retention, religious observance, astronomical or mission timing, or
  crashes a core path. MEDIUM for reports, metrics, and display. LOW for
  test-only code.

Point ledger for C1 sources (every point and its destination):
- PA-1: DST, Lord Howe, Troll, Samoa, leap-second day lengths -> C1.2.
  Code patterns (86400 constants, day counts, 24 h loops, 24 buckets),
  what to check, bucket fix, not-a-finding -> C1.2. Elapsed-versus-
  calendar language traps table, "decide intent first" fix, and
  "expires in 1 day" escalation -> C7 (inbound). Severity -> C1 severity.
- PA-2: 28 to 31 days -> C1.3. Leap rule -> C2 (inbound). Reform months
  -> C6 (inbound). Other calendars' months -> C6 (inbound). Fiscal
  months -> C5 (inbound). Days-in-month tables, 30-day month, last-day
  hardcoding -> C1.3. 1-to-31 validators and impossible-date validation
  fix -> C2 and C23 (inbound: C2 for Feb 29/30, C23 for parsing
  validation). Monthly recurrence on 29 to 31, month-addition
  overflow/clamp/reject table, non-associativity, anchor-based
  recurrence fix, month-end policy fix and escalation -> C7 (inbound).
  Financial day-count not-a-finding -> C1.3. Fiscal or non-Gregorian
  not-a-finding -> C5 and C6 (inbound). Severity -> C1 severity, and the
  "silently stores an impossible date" condition -> C2 and C7 (inbound).
- PA-3: 365/366 -> C1.4. Reform and government-change years, England
  1751 -> C6 (inbound). Samoa 2011 -> C1.4. Other calendars' years -> C6
  (inbound). Week-years and 52/53-week fiscal years -> C4 and C5
  (inbound). 365-day constants, age by division, day-of-year arrays and
  outages -> C1.4. Feb 29 plus one year table, Feb 29 policy fix, Feb 29
  legal escalation -> C7 (inbound). Java `YYYY` and week-year tokens ->
  C24 (inbound). Actual/365 and 365-elapsed-days not-a-finding -> C1.4.
  Week-year-token not-a-finding -> C24 (inbound). "Valid for one year"
  escalation -> C1.4.
- PA-4: Feb 29 existence -> C2 (inbound). Sweden 1712, Russia 1918,
  Soviet Feb 30 -> C6 (inbound). Excel 1900 phantom day, serial
  conversion fix, 1900/1904 escalation, 1904 not-a-finding -> C2
  (inbound). February capped at 28 in validators and pickers, end of
  February hardcoded, `BETWEEN ... 02-28`, literal 28 checks and
  not-a-finding -> C2 (inbound). Half-open range fix -> C3 (inbound).
  Leap-day test fixtures and NZ fuel incident -> C25 (inbound).
- PA-39: Pagume, Baha'i, French Republican, reform months,
  observational Islamic months, regional sighting, calendar-library fix,
  provisional future lengths, calendar-variant escalation -> C6
  (inbound). Fiscal 35-day and 28-day periods -> C5 (inbound). 743/745
  hours, `days * 24`, 28-to-31 assertions and grids, Gregorian
  not-a-finding -> C1.3.
- PA-45: Samoa, Kwajalein, Philippines month lengths -> C1.3 (Samoa) and
  C6 (inbound, Kwajalein and Philippines with PA-40). Reform by country,
  Java `GregorianCalendar` cutover and October 1582 maximum-day result,
  per-country adoption fix -> C6 (inbound). Sighted months by country ->
  C6 (inbound). Hours per month by zone, global tables, proration,
  per-zone month length fix, maximum-day-of-month check, multi-region
  escalation, single-region not-a-finding -> C1.3. Local month
  boundaries -> C3 (inbound). Fiscal months -> C5 (inbound).
- PA-102: all points -> C1.1, except "Hourly billing bucketed by local
  hour" which -> C1.1 and C1.2 (both), and the UT1 point -> C1.1 with
  C17 (inbound reference).
