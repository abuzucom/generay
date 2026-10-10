# C6 Calendar systems and historical dates

(sources: PA-19, 40, 41, 118; inbound from PA-2, PA-3, PA-4, PA-39, PA-43, PA-45, PA-48) Approved by the user.

Scope: non-Gregorian calendars, observational calendars, calendar reform
and its regional adoption, skipped and repeated local dates, year
numbering, eras, year-start conventions, and uncertain historical
chronology. Leap rules are C2. Fiscal calendars are C5. Epochs, type
ranges, and special values are C22. Zone history before standard time
(LMT) is C10. Era and calendar display is C24.

- C6.1 Several calendars in use.
  - Facts: calendars in official or daily use beside the Gregorian:
    Solar Hijri (Iran, Afghanistan), Islamic (religious and some official
    use), Ethiopian, Bikram Sambat (Nepal), Hebrew (Israel), Indian
    national and regional Hindu calendars, Buddhist-era years (Thailand),
    Japanese era years, Minguo years (Taiwan), and Chinese and Korean
    lunisolar dates. Month lengths differ: Hebrew and Islamic 29 or 30,
    Solar Hijri 29 to 31, Ethiopian and Coptic 13th month (Pagume) 5 or
    6, Baha'i 19 months of 19 days plus 4 or 5 intercalary days, French
    Republican (historical) 5 or 6 complementary days. Year lengths
    differ: Islamic 354 or 355, Hebrew 353 to 355 or 383 to 385. One
    person uses several calendars. Orthodox churches keep Julian feast
    dates (Christmas on January 7). Users and devices choose a calendar:
    Java `Calendar.getInstance()` returns `BuddhistCalendar` for `th-TH`
    (2568 for 2025) and `JapaneseImperialCalendar` for `ja-JP-JP` (year
    7) (verified).
  - In code: default-calendar APIs (iOS `Calendar.current`, Java
    `Calendar.getInstance()`) used with fixed formats or year arithmetic,
    so stored values, payloads, and file names get non-Gregorian years.
    Annual events from another calendar (Hijri anniversaries, lunar
    birthdays) repeated on the Gregorian date (Hijri dates drift about 11
    days a year). Static holiday tables with Gregorian dates for movable
    feasts (Easter, Orthodox Easter, Eid, Lunar New Year, Diwali). Month
    lengths or leap rules of one calendar applied to another. Age counted
    by a system the user or law does not use (Korean age, standardized
    to international age in Korean law in 2023).
  - Fix: compute and store in one canonical system (ISO 8601, proleptic
    Gregorian) and convert at the edges. Pin the Gregorian calendar and a
    fixed locale for machine formats (iOS `Calendar(identifier:
    .gregorian)` with `en_US_POSIX`, Java `java.time` ISO types or
    `Locale.ROOT`). Compute recurrences, holidays, and month lengths in
    the defining calendar with a supporting library (ICU, Java
    `java.time.chrono`, `Intl` with a `calendar` option). Keep the source
    calendar and original value where it matters.
  - Not a finding: Gregorian-only products that pin the Gregorian
    calendar and a fixed locale. A fiscal or non-Gregorian calendar
    handled through a library or a table owned by its definition.
  - Escalate: products for markets using another calendar where the
    calendars for display, input, holidays, and recurrence are not
    stated.
- C6.2 Observational and provisional calendars.
  - Facts: observational Islamic months last 29 or 30 days by moon
    sighting, announced on the evening of the 29th. Computed variants
    (Umm al-Qura) differ from observed dates. Countries following
    sighting can start the same month on different Gregorian days, so a
    month can have 29 days in one country and 30 in another. Sighted
    holidays are confirmed a day ahead (C4.5). Lunisolar leap months are
    set by astronomical rule.
  - In code: observational month lengths computed by fixed formula.
    Future dates in these calendars treated as final.
  - Fix: name the calendar variant and region. Treat future month
    lengths as provisional and allow correction.
  - Escalate: products using Islamic, Hebrew, Ethiopian, Baha'i, or
    other calendars where the variant (observed or computed, and for
    which region) is not stated.
- C6.3 Calendar reform and regional adoption.
  - Facts: Gregorian adoption spanned more than three centuries:
    Catholic states 1582 (October had 21 days, the year 355), Protestant
    German states 1700, Britain and its colonies 1752 (September had 19
    days, the year 355), Japan 1873, Russia 1918 (February had 15 days,
    the year 352), Greece 1923 (February had 15 days), Turkey 1926, with
    Swiss cantons at different times. Sweden skipped the 1700 leap day,
    then added February 30 in 1712 (a 367-day year) to return to Julian.
    The Soviet revolutionary calendar had February 30 in 1930 and 1931.
    The same month had different lengths by country (October 1582: 21
    days in Spain, 31 in England). Weekdays continued through the reform
    while dates jumped (C4.1). Java's legacy `GregorianCalendar` switches
    at 1582-10-15 by default while `java.time` is proleptic, and the
    legacy class reports 31 as October 1582's maximum day though it had
    21 (verified).
  - In code: historical dates computed proleptic Gregorian or with a
    library's default cutover for every country. Julian-dated records
    (including February 29 in 1700, 1800, 1900, see C2.4) converted
    without the source calendar. Maximum day-of-month read as the number
    of days.
  - Fix: use per-country adoption dates (for example
    `GregorianCalendar.setGregorianChange`, or ICU equivalents). Validate
    each date in its source calendar and region. Count days by iterating
    dates.
  - Escalate: historical, genealogical, legal-archive, or astronomical
    data where the source calendar or region of each date is not stated.
- C6.4 Skipped and repeated local dates.
  - Facts (tzdata 2026b, verified): Samoa and Tokelau went from
    2011-12-29 to 2011-12-31. Kwajalein from 1993-08-20 to 1993-08-22
    (August 1993 had 30 days there). The Philippines from 1844-12-30 to
    1845-01-01 (December 1844 had 30 days). Alaska repeated 1867-10-18 in
    tzdata's proleptic model when it moved from Russian to American
    dating. Reform skipped dates (C6.3). Travelers and ships crossing the
    date line skip or repeat a date in their own reckoning (moving-device
    testing is C25).
  - In code: local-date loops asserting each date is the previous plus
    one. Gap detection reporting skipped dates as data loss. Daily jobs,
    partitions, or reports expecting every local date exactly once, then
    failing on a skipped date or overwriting on a repeated one.
    "Yesterday" as `today - 1 day` naming a partition that never existed.
    Streak or consecutive-day logic breaking or double counting.
    (Iteration by adding 86400 seconds is C1.2.)
  - Fix: iterate local dates with library calendar-day operations in the
    zone and let the zone's history decide which dates exist. Key
    partitions on UTC dates, or tolerate missing and repeated local dates
    explicitly. Treat gaps in zones with known date-line changes as
    expected.
  - Not a finding: modern-date products iterating dates with library
    operations.
  - Escalate: consecutive-day rules (streaks, daily entitlements,
    interest accrual) that do not say how skipped or repeated local dates
    count.
- C6.5 Year numbering, eras, and year starts.
  - Facts: historical AD/BC numbering has no year 0 (1 BC is followed by
    AD 1). ISO 8601 astronomical numbering has year 0 = 1 BC and -1 =
    2 BC. Eras restart counts: Japan moved from Heisei to Reiwa on
    2019-05-01, so 2019 is both Heisei 31 and Reiwa 1, and Java renders
    2019-04-30 and 2019-05-01 accordingly (verified). Software needed
    data updates for the new era. The year did not always start on
    January 1: England's legal year started March 25 until 1752 (1751
    had 282 days), many Italian states used other starts, and records are
    often double dated (1750/51).
  - In code: astronomical and historical year numbers mixed. Era names
    hardcoded or era data outdated. Historical years assumed to start on
    January 1. Double-dated sources stored with one year chosen silently.
  - Fix: pick one numbering scheme, state it, and convert explicitly.
    Keep era and calendar data current (C10 for the update process).
    Record each historical date's year-start convention and support
    double dating where sources use it.
  - Not a finding: modern-date applications validated to a modern range.
- C6.6 Uncertain historical chronology.
  - Facts: Roman Republican intercalation was decided by officials, and
    46 BC lasted 445 days. Early Julian leap years were misapplied
    (every third year, then suspended under Augustus), and scholars
    disagree on the sequence, so Julian dates before about AD 8 are
    uncertain by a day or more. Historical lunisolar records do not always
    say which leap month was used. Tidal friction lengthens the day over
    time, and the accumulated difference between rotation time and
    uniform time (Delta T) reaches hours for ancient dates and is known
    only approximately. Proleptic Gregorian libraries and databases
    disagree with historical records.
  - In code: intervals, ages, or anniversaries computed across ancient or
    reform-era dates with a proleptic calendar. Ancient astronomical
    events placed in UTC without a Delta T model. Historical dates shown
    without uncertainty. Original date text discarded.
  - Fix: keep the original date text, source calendar, region, and
    year-start convention. Convert with libraries or tables built for
    historical chronology, and show uncertainty where scholars disagree.
    Use a published Delta T model for astronomical work on ancient
    dates.
  - Not a finding: modern-date products validated to a modern range.
- Proposed severity (for the user to decide), per check: HIGH when a
  user's calendar setting corrupts stored or transmitted dates, religious
  or legal dates are wrong, daily billing, interest, or entitlements
  mishandle skipped or repeated dates, or historical, legal-archive, or
  genealogical records on a core path are converted, validated, or
  compared wrongly. MEDIUM for display, holiday tables, reports,
  partitions, and gap alerts. LOW for test-only code.

Point ledger for C6:
- Inbound from PA-2: reform months (1582, 1752, 1918, Sweden 1712),
  proleptic disagreement -> C6.3. Hebrew, Islamic, Solar Hijri,
  Ethiopian, Coptic month lengths -> C6.1. Non-Gregorian not-a-finding ->
  C6.1.
- Inbound from PA-3: reform and government-change years (1582, 1752,
  1918, Sweden 1712) -> C6.3. England 1751 -> C6.5. Islamic and Hebrew
  year lengths -> C6.1.
- Inbound from PA-4: Sweden 1712, Russia 1918 -> C6.3. Soviet February
  30 -> C6.3.
- Inbound from PA-39: Pagume, Baha'i, French Republican -> C6.1. Reform
  months -> C6.3. Observational Islamic months, regional sighting,
  provisional future lengths, calendar-variant escalation -> C6.2.
  Calendar-library month-length fix (`java.time.chrono` chronologies) ->
  C6.1.
- Inbound from PA-43: Sweden 1700 and 1712, and Sweden's 1700 leap year
  without a leap day -> C6.3.
- Inbound from PA-45: Kwajalein and Philippines month lengths -> C6.4.
  Reform by country, Java `GregorianCalendar` cutover and maximum-day
  result, per-country adoption fix, iterate-to-count fix -> C6.3. Sighted
  months by country -> C6.2.
- Inbound from PA-48: original-calendar fix for historical weekdays ->
  C6.3 (weekday facts stay in C4.1).
- PA-19: no year 0, astronomical numbering, numbering scheme fix -> C6.5.
  Gregorian start in 1582 and proleptic disagreement -> C6.3 and C6.6.
  Original text and calendar for historical records -> C6.6. Calendar or
  numbering escalation -> C6.3 escalation. Epoch list, epoch constants,
  Apple-as-Unix error, named-epoch fix -> C22 (inbound). LMT, tzdata
  reliable from 1970, pytz `tzinfo=` misuse, historical local times with
  modern rules -> C10 (inbound). Future rules are projections -> C10
  (inbound). Java `uuuu` versus `yyyy G` output -> C24 (inbound). Java
  strict parse with `yyyy` and no era -> C23 (inbound). Postgres
  `infinity`, unbounded iteration, historical data in narrow types,
  type-range fix -> C22 (inbound). Modern-range not-a-finding -> C6.5 and
  C6.6. Severity -> C6 severity (stored-record part) and C22 (inbound).
- PA-40: Samoa, Tokelau, Kwajalein, Philippines, Alaska, reform skips,
  travelers, loops, gap detection, daily jobs and partitions, yesterday,
  streaks, what to check, library iteration fix, UTC partitions,
  expected-gap fix, not-a-finding, consecutive-day escalation -> C6.4.
  86400 iteration -> C1.2. Original-calendar fix -> C6.6. Moving-device
  testing -> C25 (inbound reference). Severity -> C6 severity.
- PA-41: all coexisting calendars, personal multi-calendar use, Julian
  and Orthodox, user and device calendar choice, default-calendar APIs,
  annual events, movable feasts, Korean age, what to check, canonical
  storage, pinned Gregorian for machines, defining-calendar recurrences,
  source calendar, not-a-finding, market escalation -> C6.1. Era change
  and era data -> C6.5. Business calendars beside civil ones -> C4.3 and
  C5 (already there). Era data currency -> C6.5 with C10. Severity -> C6
  severity.
- PA-118: Roman intercalation, early Julian, lunisolar records, Delta T,
  proleptic intervals, missing uncertainty, historical-chronology fix,
  Delta T fix -> C6.6. Adoption over centuries and one-reform-date code
  -> C6.3. Year starts and double dating -> C6.5. Leap seconds since
  1972 -> C17 (inbound). Modern-range not-a-finding -> C6.6. Escalation
  -> C6.3 escalation. Severity -> C6 severity.
