# C12 Offsets and differences between zones

(sources: PA-33, 49, 51, 87, 88; inbound from C10.6) Approved by the user.

Scope: how far apart zones are and how that changes, the range and
granularity of offsets, how many zones and offsets exist, and the
representations that cannot hold real offsets. Rule changes are C10.
DST mechanics are C11. Choosing a zone from location or offset is C14.

- C12.1 Differences between zones vary.
  - Facts (tzdata 2026b, verified): DST dates differ, so London minus
    New York is 5 hours most of the year and 4 around 2026-03-20 and
    2026-10-30. Hemispheres differ: Sydney minus London is 11 hours in
    January, 9 in April, 10 for a few weeks in October. Some zones skip
    DST: Los Angeles and Phoenix match in summer and differ by 1 hour in
    winter. Kathmandu minus Kolkata is 15 minutes. Lord Howe and Troll
    change differences by 30 minutes and 2 hours. Morocco moves to +00:00
    during Ramadan. Rule changes alter differences permanently (C10).
  - In code: hardcoded differences (`london = new_york + 5`, "the
    customer is 8 hours behind"). Conversion by a difference computed
    once and reused for other dates. Recurring cross-zone events
    (meetings, market opens, batch windows) with one fixed difference.
    Static zone-to-offset tables. Pickers storing the displayed offset
    ("(GMT-05:00) Eastern Time") instead of the ID. Business-hours,
    cutoff, or SLA logic for another region by a fixed difference.
  - Fix: convert through the instant for each specific date (local A to
    UTC to local B) with the library. Never store or reuse a difference.
    Anchor recurring cross-zone events to one owner zone and convert each
    occurrence (C10.2). Store IANA IDs from pickers and compute the label
    for the relevant date. Test the weeks between zones' transitions and
    non-whole-hour zones.
  - Not a finding: differences between fixed-offset zones by design (UTC,
    `Etc/GMT` zones).
  - Escalate: recurring cross-zone events that do not say whose local
    time anchors them.
- C12.2 Offsets that are not whole hours.
  - Facts (January and July 2026, verified): +05:30 (India, Sri Lanka),
    +03:30 (Iran), +04:30 (Afghanistan), +06:30 (Myanmar), +05:45
    (Nepal), -03:30 and -02:30 (Newfoundland), +10:30 and +09:30
    (Adelaide), +09:30 (Darwin), +08:45 (Eucla), -09:30 (Marquesas),
    +13:45 and +12:45 (Chatham). India alone has well over a billion
    people.
  - In code: offsets stored or passed as integer hours. JS
    `getTimezoneOffset() / 60` truncated. Conversion by adding the offset
    to the hour field only. Hourly jobs, reports, partitions, rate
    limits, or billing aligned to UTC hours and labeled as local hours
    (UTC 09:00 is 14:30 in Kolkata, verified). Pickers and validators
    offering whole hours only.
  - Fix: store zone IDs, or offsets in minutes or seconds, and convert
    with the library. Align hourly buckets to local hour boundaries per
    zone where local hours matter, or label them UTC (C1.1). Test +05:30,
    +05:45, -03:30, and +12:45.
  - Not a finding: UTC-only hourly processing labeled as UTC.
  - Escalate: hourly billing, quotas, or reports for non-hour zones where
    the intended hour boundary is not stated.
- C12.3 Offsets with seconds and representation limits.
  - Facts (Python `zoneinfo`, verified): historical offsets have seconds
    (New York LMT -04:56:02, Dublin Mean Time -00:25:21 until 1916,
    Monrovia -00:44:30 until 1972). Amsterdam was UTC+00:19:32.13 until
    1937, and tzdata stores +00:19:32. UTC differs from UT1 by under
    0.9 s, and smeared clocks differ by fractions during a smear (C16).
    Representations lose these (verified where marked): RFC 3339 offsets
    in common use carry hours and minutes, and Python `isoformat()` emits
    `-04:56:02`, which many parsers reject; JS `getTimezoneOffset()`
    returns 296 and `toString()` shows `GMT-0456` for New York 1880; .NET
    `DateTimeOffset` requires whole minutes within +/-14 hours and
    throws; SQL Server `datetimeoffset` stores minutes; Python before 3.7
    required whole minutes.
  - In code: offsets stored as integer hours, half hours, quarter hours,
    or minutes. Offsets formatted as `+HH:MM`, so historical values lose
    seconds (display round trip C24). Parsers accepting only `+HH:MM`
    (C23). Historical conversions crashing in .NET or truncating in JS.
  - Fix: store IANA zone IDs and UTC instants, and recompute offsets.
    Where offsets must be stored, use seconds (Java `ZoneOffset` supports
    seconds up to +/-18 hours). Accept `+HH:MM:SS` where historical data
    is in scope. Document truncation where a platform cannot represent
    the offset.
  - Not a finding: modern-date systems whose zones all have whole-minute
    offsets, with a documented range.
  - Escalate: historical, genealogical, or archival products on platforms
    limited to whole-minute offsets.
- C12.4 Offset range, zone count, and geography.
  - Facts (verified where marked): this host's tz data lists 498 zone
    names (installations differ). 40 distinct offsets were in use across
    January and July 2026, from -12:00 to +14:00 (a 26-hour span). A zone
    is a region with a history of offsets, not an offset: Phoenix and
    Denver share -07:00 in winter only. Windows uses its own IDs (about
    140, such as "Pacific Standard Time" covering summer too), mapped to
    IANA through CLDR `windowsZones` or the platform (.NET 6+
    `TimeZoneInfo.TryConvertWindowsIdToIanaId`). Idealized 24 one-hour
    bands exist only in nautical time and military letter zones. Civil
    zones follow borders, not longitude: China uses +08:00 throughout
    and borders Afghanistan (+04:30, 3.5 hours), Pakistan and Kazakhstan
    (+05:00), India (+05:30), and Nepal (+05:45); Samoa (+13:00) and
    American Samoa (-11:00) are 24 hours apart, as are Kiribati's Line
    Islands (+14:00) and Hawaii (-10:00); Norway and Murmansk differ by
    2 hours in winter; Spain uses Central European Time while Portugal
    uses UTC+0; zones nest (Hopi inside Navajo inside Arizona).
  - In code: offset validation limited to -12 to +12 or to whole hours.
    Enums, tables, or pickers with 24 zones. Zone guessed from longitude
    (`round(longitude / 15)`). Travel, logistics, or ETA logic assuming a
    border changes the clock by at most one hour. Fallback to a "nearby"
    offset when the zone is unknown. Offsets used as zone identity. Ad hoc
    Windows-to-IANA maps.
  - Fix: accept the full range and minute-level offsets, and store IANA
    IDs. Generate zone lists from tz data and offer pickers by region and
    city with computed offset labels (C10.5). Derive zones from
    coordinates only with a maintained boundary dataset through a library
    (new dependencies need approval) (C14). Convert per zone through
    instants for every crossing. Map Windows IDs with CLDR data or the
    platform converter. Ask the user when the zone is unknown.
  - Not a finding: nautical or military systems using their documented
    schemes by design. IANA IDs with library conversion.
  - Escalate: integrations exchanging zones in a non-IANA scheme without
    a documented mapping. Location-based zone assignment without a stated
    boundary source.
- Proposed severity (for the user to decide), per check: HIGH when a
  fixed difference, whole-hour assumption, truncated offset, small-range
  validator, 24-zone model, or longitude guess assigns wrong times or
  drives scheduling, trading windows, logistics, billing cutoffs, SLAs,
  or hourly billing on a core path, or historical conversions crash or
  corrupt stored values. MEDIUM for pickers, display, reports, and
  round-trip loss. LOW for test-only code.

Point ledger for C12:
- Inbound from C10.6: offsets with seconds -> C12.3.
- PA-33: all difference facts, hardcoded differences, reused
  differences, recurring events, static tables, pickers, regional
  business hours, what to check, instant fix, no-stored-difference fix,
  owner-zone fix, picker fix, tests, not-a-finding, escalation -> C12.1.
  Rule changes -> C10.1. Severity -> C12 severity.
- PA-49: China and neighbors, date-line neighbors, Norway and Murmansk,
  Spain and Portugal, nesting, 26-hour range, non-hour values, -12 to
  +12 validation, 24-zone lists, longitude guess, border logic, nearby
  fallback, what to check, full-range fix, boundary-dataset fix,
  crossing fix, ask-user fix, not-a-finding, boundary escalation ->
  C12.4. Severity -> C12 severity.
- PA-51: historical second-level offsets, Amsterdam fraction, DUT1 and
  smearing, representation limits, storage and formatting patterns,
  parser limit, historical crashes, zone-ID fix, seconds fix, input fix,
  documentation fix, not-a-finding, escalation -> C12.3. Display round
  trip -> C24 and parsing -> C23 by reference. Severity -> C12 severity.
- PA-87: 498 names, 40 offsets, zone versus offset, Windows IDs, nautical
  and military schemes, enums and pickers, integer offsets, offsets as
  identity, Windows maps, generate fix, picker fix, mapping fix,
  not-a-finding, escalation -> C12.4. Severity -> C12 severity.
- PA-88: all non-hour offsets, integer-hour code, hour-field conversion,
  UTC-aligned buckets, whole-hour pickers, zone-ID fix, local-bucket fix,
  tests, not-a-finding, escalation -> C12.2. Second-level offsets ->
  C12.3. DST hour addition -> C11.2. Severity -> C12 severity.
