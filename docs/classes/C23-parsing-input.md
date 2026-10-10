# C23 Parsing input

(sources: PA-27, 28, 71, 83, 84, 86, 108, 130; inbound from PA-19,
PA-24, PA-57, C2.3, C12.3, C13.3, C20.1, C21.1, C22.5) Approved by the
user.

Scope: reading time values from text and numbers at every input
boundary: declared formats, variation within a source, field order,
two-digit years, parsing mechanics, hours of 24 and above, duration and
partial-date grammars, and automatic type inference. Second 60 is C17.1.
Year ranges and width are C22. Display strings and native digits are
C24.

- C23.1 Declare the format and unit of every input.
  - Facts (verified where marked): bare numbers are ambiguous:
    `1339972628` as seconds is 2012-06-17 22:37:08 UTC, while the 12-digit
    `133997262837` is 1974-03-31 as ms, 1970-01-02 as us, and year 6216 as
    seconds. Text formats differ: ISO 8601 and RFC 3339 with or without
    offset or fraction; RFC 5322 email dates; HTTP IMF-fixdate plus the
    obsolete RFC 850 and asctime forms recipients must accept (RFC 9110);
    locale formats; X.509 `UTCTime` (50 to 99 mean 19xx) and
    `GeneralizedTime`; BSD syslog (RFC 3164) with no year or zone.
    Encodings: Protobuf `Timestamp`, MongoDB Extended JSON `{"$date":...}`,
    ASP.NET `/Date(...)/`, Excel serials, FILETIME, .NET ticks, Apple
    reference dates, Julian dates, GPS week plus seconds. JS
    `parseInt("2026-07-01T09:00:00Z")` is 2026. JS `Date.parse` is
    specified only for ISO; V8 reads `"01/02/2026"` as January 2 and
    `"2026-07-01 09:00"` as local time. Python `strptime("%b")` and Java
    `MMM` use the current locale by default.
  - In code: units guessed from magnitude or digit count (`if ts > 1e12`).
    Numeric parsing applied to text. `Date.parse` or `new Date(string)`
    on non-ISO input. Parsing without an explicit format and locale.
    Syslog lines given the current year, so December entries read in
    January land in the wrong year.
  - Fix: declare each interface's wire format, preferring RFC 3339 with
    offset for text and named epoch and unit for numbers (C20.1). Parse
    strictly with an explicit format and fixed locale (`Locale.ROOT`,
    POSIX). Use library parsers for HTTP, email, and X.509 dates. Attach
    missing year or zone from known context by a documented rule. Validate
    in the schema (OpenAPI `format: date-time`).
  - Not a finding: one documented numeric format with a named unit,
    validated at the boundary.
  - Escalate: partner feeds or imported files whose format or unit cannot
    be established.
- C23.2 One source, many shapes, and strings compared as dates.
  - Facts (verified where marked): valid RFC 3339 / ISO 8601 shapes vary:
    fraction present or absent with any digits; `Z`, `+00:00`, `+0000`,
    `-00:00` (meaning C8.5); `T`, `t`, or space; basic format, week dates,
    ordinal dates, reduced precision. Python `isoformat()` omits zero
    microseconds. Python `fromisoformat` accepts `Z` only from 3.11.
    Library upgrades and serializer changes alter output. Several app
    versions, partners, and legacy rows write one field. Schemaless stores
    mix BSON dates and strings, or strings and numbers. Spreadsheets
    rewrite dates on save. `2026-07-01T09:00:00.5Z` sorts before
    `...09:00:00Z` as text (verified), and offsets, fraction lengths, and
    signed or variable-width years (C22.5) break text order too.
  - In code: one strict pattern on a field whose valid values vary,
    dropping valid records or crashing imports. Lenient parsing that
    misreads some variants. Timestamps sorted, compared, or deduplicated
    as text, or kept in string columns. Parse failures swallowed.
  - Fix: parse at the boundary into typed values and compare only typed
    values. Accept the full declared profile with a library parser.
    Normalize on write to one canonical form. Store typed columns, and
    enforce types in schemaless stores. Version producer contracts and add
    contract tests. Migrate legacy rows. Reject unparseable values loudly
    and count them (C26).
  - Not a finding: text sorting where a canonical fixed-width UTC form is
    enforced on every write.
  - Escalate: legacy datasets whose mix of formats cannot be established.
- C23.3 Numeric field order.
  - Facts: month-day-year (US), day-month-year (most of the world), and
    year-month-day (East Asia, ISO, several European countries) are all in
    use, and Canada uses all three. `03/04/2026` is March 4 or April 3, and
    `03/04/26` adds more readings. Whenever day and month are both 12 or
    less and differ, both readings are valid: 132 dates a year, about 36%
    (computed). Separators do not settle order. JS reads `03/04/2026` as
    March 4 and rejects `13/04/2026` (verified). `dateutil` assumes month
    first unless `dayfirst=True`. SQL Server follows `SET DATEFORMAT` or
    session language, Postgres `DateStyle`. Spreadsheets apply the system
    locale to CSV.
  - In code: CSV imports, free-text fields, and feeds with numeric dates
    and no declared order. SQL literals in numeric formats. Validation that
    accepts anything that parses, so swaps pass silently.
  - Fix: use ISO 8601 for machine exchange and SQL literals. Use pickers or
    separate fields for human input (C24). Declare each source's order and
    parse strictly. When order is unknown, reject ambiguous values. Set
    database date styles explicitly or avoid relying on them.
  - Not a finding: numeric dates with a declared, enforced order from one
    source.
  - Escalate: imported numeric dates whose source order cannot be
    established.
- C23.4 Two-digit years.
  - Facts (verified where marked): Python `%y`: 69 to 99 become 1969 to
    1999, 00 to 68 become 2000 to 2068. V8: 49 is 2049, 50 is 1950. Java
    `DateTimeFormatter` `yy`: always 2000 to 2099. Java `SimpleDateFormat`:
    a sliding window 80 years back and 20 ahead (in October 2026, 46 is
    2046 and 47 is 1947), so results change over time. .NET
    `TwoDigitYearMax` (commonly 2049, changeable in Windows regional
    settings). MySQL: 70 to 99 are 19xx. X.509 `UTCTime`: 50 to 99 are
    19xx. Domains need other windows: centenarians' birth years (Python
    turns "25" into 2025), near-future card expiries, historical records,
    leases past 2099. One string can become different years in different
    layers.
  - In code: `%y`, `yy`, or default two-digit parsing with no explicit
    pivot. Several tools expanding one field. Birth or historical dates
    with two-digit years.
  - Fix: require four-digit years at input and in every stored or
    exchanged format. Where unavoidable, apply one explicit
    domain-specific rule in one place and check plausibility. Apply the
    rule a format's standard defines (X.509). Never rely on library
    pivots.
  - Not a finding: two-digit years displayed for convenience where
    four-digit values are stored and never re-parsed.
  - Escalate: legacy data or feeds with two-digit years whose century
    cannot be established.
- C23.5 Parsing mechanics.
  - Facts (verified where marked): compact formats are ambiguous: Python
    `strptime('2026111', '%Y%m%d')` returns 2026-11-01 though 2026-01-11
    fits, and `'202611'` returns 2026-01-01. Unpadded fields end only at
    the next separator. ISO forms look alike until a field ends (`2026-11`,
    `2026-307`, `2026-W45-3`, `2026W453`); Python 3.11 `fromisoformat`
    accepts both week forms and rejects `2026-307`. Fractions vary in
    length, and JS drops digits past milliseconds while Java
    `SimpleDateFormat` `SSS` reads `.123456` as 123,456 ms (09:00:00.123456
    becomes 09:02:03.456). Offsets appear as `Z`, `+05`, `+0530`, `+05:30`,
    and historically `+HH:MM:SS` (C12.3). Month names vary in length and
    share prefixes and depend on locale. Later tokens change earlier
    fields: `12:30 AM` is 00:30 (Python), and trailing offsets or zone
    names change the instant (abbreviations C13.3). Java needs adjacent
    value parsing for `yyyyMMddHHmm`. Java strict parsing with `yyyy`
    (year of era) and no era field fails even for modern dates, so `uuuu`
    is required (verified).
  - In code: hand-written character parsers or greedy regexes such as
    `(\d{1,2})(\d{1,2})`. Compact variable-width input accepted. Trailing
    tokens ignored, or partial matches leaving text unread. 12 AM and 12 PM
    mishandled. `SSS` with `SimpleDateFormat`. Parsers accepting only
    `+HH:MM`. Strict Java parsing with `yyyy`.
  - Fix: parse with library parsers and explicit formats in strict mode,
    matching the whole string. Require separators or fixed-width
    zero-padded fields. Use ISO parsers for fractions
    (`DateTimeFormatter.ISO_INSTANT`, `appendFraction`). Use `uuuu` in Java
    strict parsing. Accept `+HH:MM:SS` where historical data is in scope.
    Test 12:00 AM, 12:00 PM, every allowed offset form, and long fractions.
  - Not a finding: library parsing of a strict, fixed-width, documented
    format.
  - Escalate: compact or unpadded inputs whose field widths are not
    documented.
- C23.6 Hours of 24 and above, and durations in time-of-day types.
  - Facts (verified where marked): GTFS `stop_times` allow `24:12:34` and
    later on the same service day, measured from noon minus 12 hours on
    the service date (C3.5). East Asian business hours and TV listings
    use `25:30` or `26:00`. ISO 8601 editions differed on `24:00` (in
    2004, dropped in 2019, revisited), and RFC 3339 allows 00 to 23.
    Durations such as `24:12:34` or `100:00:00` are valid, spreadsheets
    use `[h]:mm:ss`, MySQL `TIME` holds -838:59:59 to 838:59:59, and
    Postgres `time` accepts `24:00:00`. JS accepts `T24:00:00Z` as next
    midnight but rejects `T24:12:34Z`; Python `%H` and Java
    `LocalDateTime.parse` reject both.
  - In code: validators limiting hours to 00 to 23 on service-day times or
    durations. GTFS or schedule imports rejecting or wrapping `24:xx` onto
    the same date. Durations stored in time-of-day types, losing anything
    over 24 hours. `24:00` accepted by one layer and rejected by the next.
  - Fix: model durations as duration types (`PT24H12M34S`, Java
    `Duration`, integer seconds). Parse domain formats by their specs (GTFS
    from noon minus 12 hours, extended-hour listings by their cutoff).
    Decide whether `24:00` is accepted, normalize it at the boundary to the
    next day's 00:00, and apply the same rule in every layer.
  - Not a finding: strict 00 to 23 validation on documented RFC 3339
    times of day.
  - Escalate: imported time fields whose meaning (time of day, service-day
    time, or duration) is not documented.
- C23.7 Duration, partial-date, and interval grammars.
  - Facts (verified where marked): XML Schema partial dates are in use:
    `gDay` (`---12Z`), `gMonth` (`--12`), `gMonthDay` (`--12-25`),
    `gYearMonth`, `gYear`. ISO 8601 durations need not be normalized
    (`P12Y34M56DT78H90M12.345S` is valid): months normalize into years,
    days do not normalize into months, and hours do not normalize into
    days without a zone. Other forms: `P2W`, alternative format
    `P0003-06-04T12:30:05`, negative XML Schema durations (`-P1D`),
    intervals (`2026-01-01/2026-02-01`, `.../P1M`, `P1M/...`), repeating
    intervals (`R5/.../P1D`). Users: iCalendar `DURATION` (RFC 5545,
    `P15DT5H0M20S`, `P7W`), HTML `<time>`, JSON Schema `duration` (RFC
    3339 Appendix A), OData `Edm.Duration`, XML and SOAP services, media
    APIs (`PT1H2M3S`). Support is partial: Java `Duration.parse` and
    `Period.parse` both reject the long example (`Duration` takes days and
    time parts, `Period` date parts), `Duration` normalizes
    `PT78H90M12.345S` to `PT79H30M12.345S`, and `Period.normalized()`
    turns `P12Y34M56D` into `P14Y10M56D`; Python's standard library has no
    ISO duration parser; Node 22 has no built-in `Temporal`. Go (`1h30m`),
    Prometheus (`5m`), and systemd (`1h 30min`) use their own syntaxes.
  - In code: hand-written duration regexes accepting only normalized or
    `PT...` forms. Durations converted to seconds with fixed month and day
    lengths. Partial dates rejected or forced into full dates with an
    invented year. Different duration syntaxes mixed in config and APIs.
  - Fix: identify each interface's grammar (XML Schema, ISO 8601 profile,
    RFC 5545, RFC 3339 Appendix A) and parse with a library that supports
    it (new dependencies need approval). Keep calendar parts separate from
    exact time parts and apply them with calendar arithmetic in a zone
    (C7.1, C7.7). Model partial dates as their own types. Reject
    unsupported forms loudly.
  - Not a finding: interfaces documenting and validating a narrow
    duration profile.
  - Escalate: interfaces exchanging durations without documented grammar
    and calendar semantics.
- C23.8 Type inference that creates or destroys dates.
  - Facts (verified where marked): spreadsheets turned gene symbols such as
    `SEPT2` and `MARCH1` into dates often enough that HGNC renamed those
    genes in 2020 (`SEPTIN1`, `MARCHF1`), and convert part numbers (`1-2`),
    fractions (`1/2`), and versions (`2026.10`). 10-digit IDs and phone
    numbers fit the epoch-seconds range. PyYAML (YAML 1.1) loads unquoted
    `2026-10-03` as a `date`, `22:22` as 1342, and `1:30:00` as 5400,
    while quoted values stay strings (verified with PyYAML 6.0.1).
    Elasticsearch dynamic mapping detects dates by default, so the first
    value fixes a field as `date` and later non-dates fail to index.
    Json.NET converts ISO-like strings to `DateTime` by default
    (`DateParseHandling.DateTime`), which can change offset or text.
    Data-frame readers and CSV importers infer date columns. Natural
    language parsers find dates in "may", "march", "second", "sun".
  - In code: automatic type inference on imports, config, logs, or search
    indexes. Spreadsheets in data pipelines. JSON or YAML loaded with
    default date conversion. Heuristic "is this a date?" checks.
  - Fix: declare types by schema: explicit column types, index mappings,
    and serializer settings. Turn off date detection where values are not
    declared dates (Elasticsearch `date_detection: false`, Json.NET
    `DateParseHandling.None`). Quote YAML dates and times or use a YAML 1.2
    loader without implicit timestamps. Keep spreadsheets out of machine
    pipelines, or import columns as text.
  - Not a finding: schema-declared date fields parsed strictly.
  - Escalate: data sets whose field types are undocumented and inferred
    on import.
- Proposed severity (for the user to decide), per check: HIGH when
  misread, swapped, wrongly expanded, ambiguously split, shifted,
  misparsed, or inferred values store wrong dates or durations, drop or
  reject valid records, reorder, deduplicate, or filter wrongly, or
  corrupt identifiers, configuration, or indexed data on a core path
  (imports, payments, bookings, contracts, medical records, schedules,
  transit, timesheets, expiry). MEDIUM for logs, analytics imports,
  configuration, and cross-layer inconsistency. LOW for test-only code.

Point ledger for C23:
- Inbound from PA-19: Java strict parse with `yyyy` and no era -> C23.5.
- Inbound from PA-24: JS dropping fraction digits, `SimpleDateFormat`
  `SSS`, ISO-parser fix -> C23.5.
- Inbound from PA-57: parsers rejecting `24:00` or `25:30`, GTFS times as
  clock times, GTFS parsing fix -> C23.6.
- Inbound from C2.3: impossible-date validation by a rejecting API in
  parsing -> C23.5 (strict library parsing).
- Inbound from C12.3: parsers accepting only `+HH:MM` -> C23.5.
- Inbound from C13.3: abbreviations parsed from input -> C23.5 by
  reference (rules stay in C13.3).
- Inbound from C20.1: unit detection by magnitude -> C23.1.
- Inbound from C21.1: ISO 8601 durations at interfaces -> C23.7.
- Inbound from C22.5: text sorting of signed or variable-width years ->
  C23.2.
- PA-27: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C23.1. Locale order and `dateutil` order -> C23.3.
  Two-digit years and X.509 pivot -> C23.4. Abbreviations -> C13.3.
  Severity -> C23 severity.
- PA-28: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C23.2. Zero-offset meaning -> C8.5 by reference.
  Severity -> C23 severity.
- PA-71: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C23.6. Severity -> C23 severity.
- PA-83: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C23.4. Severity -> C23 severity.
- PA-84: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C23.5. Two-digit years -> C23.4. Format variants ->
  C23.2. Severity -> C23 severity.
- PA-86: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C23.7. Severity -> C23 severity.
- PA-108: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C23.8. Severity -> C23 severity.
- PA-130: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C23.3. Severity -> C23 severity.
