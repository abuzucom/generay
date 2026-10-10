# C13 Zone names, abbreviations, and GMT

(sources: PA-66, 67, 128; PA-109 moved to C14; inbound from PA-8, C8.2, C11.5) Approved by the user.

Scope: how zones are named and labeled: GMT versus UTC, sign
conventions in zone strings, silent fallbacks on unknown IDs, UK and
British-territory zones, and abbreviations. Which zone applies to a
location is C14 (PA-109 moves there because it is about locations, not
names). Fixed offsets for DST places are C11.5.

- C13.1 GMT is not UTC, and the UK is not on GMT.
  - Facts (tzdata 2026b and Java, verified): UTC is an atomic scale kept
    within 0.9 s of rotation time by leap seconds. GMT historically meant
    mean solar time at Greenwich (close to UT1), and is now used loosely
    for UTC+00:00. People also use "GMT" for UK civil time:
    `Europe/London` is GMT in winter and BST (+01:00) in summer, 210 days
    of 2026. "15:00 GMT" in July is ambiguous. History: +01:00 all year
    1968 to 1971, wartime +01:00 winters and +02:00 summers. British
    jurisdictions span many zones (July 2026: Jersey +01:00, Gibraltar
    +02:00, Falklands -03:00, Bermuda -03:00, Chagos +06:00). Ireland
    (`Europe/Dublin`) is IST in summer and GMT in winter. The UK has
    debated changes. Only `UTC`/`Etc/UTC` (and `Etc/GMT`) are fixed at
    +00:00. Protocols require the literal "GMT" to mean UTC: HTTP dates
    (RFC 9110) and cookie `Expires` (Python `formatdate(usegmt=True)`,
    verified). JS `toString()` labels offsets as `GMT-0400`.
  - In code: UK users or offices assigned `GMT`, UTC, or +00:00. Country
    `GB` mapped to one zone, missing territories and Crown dependencies.
    HTTP or cookie dates written with `UTC` or numeric offsets.
    Requirements or UI text using bare "GMT".
  - Fix: use `UTC` for UTC and `Europe/London` for UK time, with the
    specific IANA ID for each territory. Generate HTTP and email dates
    with library formatters that emit `GMT`. Label user-facing times
    "UTC" or with the named zone.
  - Not a finding: the literal `GMT` in HTTP or email date formats.
  - Escalate: requirements, contracts, or schedules stated in "GMT" where
    UTC versus UK civil time cannot be established.
- C13.2 Zone strings with inverted signs and silent fallbacks.
  - Facts (verified): `Etc/GMT+5` means UTC-05:00, following POSIX `TZ`
    sign rules, and `TZ=UTC+3` and `TZ=Etc/GMT+3` both give UTC-03:00.
    Java legacy `TimeZone.getTimeZone("GMT+5")` gives +05:00 while
    `ZoneId.of("Etc/GMT+5")` gives -05:00. Java legacy
    `TimeZone.getTimeZone` returns GMT for an unknown or misspelled ID
    (`Europe/Lodnon`), while `ZoneId.of` throws.
  - In code: UI labels like "GMT+3" mapped to `Etc/GMT+3`. POSIX `TZ`
    strings written with the intuitive sign. Legacy Java lookups on user
    or config input.
  - Fix: avoid `Etc/GMT+/-N` and POSIX offset strings, or document the
    inverted sign beside them. Validate zone IDs with APIs that reject
    unknown IDs (`ZoneId.of`).
- C13.3 Abbreviations are not identifiers.
  - Facts (tzdata 2026b and Java, verified): CST is US Central (-06:00),
    China (+08:00), and Cuba (-05:00). IST is India (+05:30), Israel
    (+02:00 in winter), and Irish summer time (+01:00). BST is British
    Summer Time and Bangladesh Standard Time. Abbreviations name a DST
    state, not a zone (EST and EDT), and people write "EST" all year.
    Abbreviations change (Australian EST to AEST and AEDT; tzdata now
    uses numeric forms such as `+06` for Dhaka). Parsers disagree: JS
    `Date.parse` accepts CST (-06:00) and EST (-05:00) but returns `NaN`
    for IST, BST, and AEST; Python `strptime` `%Z` accepts UTC and rejects
    CST and IST; Java `ZoneId.SHORT_IDS` maps EST to fixed -05:00, MST to
    -07:00, HST to -10:00, CST to `America/Chicago`, IST to
    `Asia/Kolkata`, and BST to `Asia/Dhaka`, and legacy
    `TimeZone.getTimeZone("BST")` gives +06:00.
  - In code: abbreviations parsed from input, emails, logs, or feeds into
    offsets or zones (parsing detail C23). Abbreviations stored as the
    zone identifier. Java `SHORT_IDS` or three-letter legacy IDs used for
    lookup. Displays printing a stored abbreviation.
  - Fix: accept and store IANA IDs or numeric offsets, never
    abbreviations. Generate abbreviations for display only, from the zone
    and instant, and add the city or region where ambiguity matters.
    Where input must contain abbreviations, resolve them with an
    explicit context-specific table and reject unknown or ambiguous ones.
  - Not a finding: abbreviations computed for display from a stored zone
    ID.
  - Escalate: inputs or partner feeds that supply only abbreviations.
- Proposed severity (for the user to decide), per check: HIGH when UK,
  territory, abbreviation-parsed, sign-inverted, or fallback-to-GMT
  times or deadlines on a core path are off by an hour or more. MEDIUM for
  labels, display, territory coverage, and HTTP header formatting. LOW
  for test-only code.

Point ledger for C13:
- Inbound from PA-8: "GMT" in common use means London time, only
  `Etc/GMT`/`UTC` fixed -> C13.1.
- Inbound from C8.2: abbreviation ambiguity of a moment -> C13.3.
- Inbound from C11.5: Java short ID "EST" -> C13.3. `Etc/GMT+5` -> C13.2.
- PA-66: UTC versus GMT definitions, UK civil time, protocol literal, JS
  label, UK users on GMT, HTTP dates with UTC, bare "GMT" text, UTC and
  London fix, protocol formatter fix, labeling fix, not-a-finding,
  escalation -> C13.1. Inverted signs, POSIX strings, Java legacy sign
  and fallback, UI label mapping, legacy lookups, sign-documentation fix,
  rejecting-API fix -> C13.2. Severity -> C13 severity.
- PA-67: BST days in 2026, history, territories, Ireland, possible rule
  change, UK assigned GMT, `GB` single zone, territory-ID fix,
  `zone1970.tab` country mapping -> C13.1 (country-to-zone mapping detail
  -> C14 by reference). BST and IST collisions, Java `SHORT_IDS`, tzdata
  numeric Dhaka label, abbreviation parsing, no-SHORT_IDS fix,
  display-only not-a-finding, abbreviation-feed escalation -> C13.3.
  Severity -> C13 severity.
- PA-109: moved whole to C14 (inbound). Reason: it concerns which zones
  apply to a location.
- PA-128: all facts, parser table, code patterns, checks, fixes,
  not-a-finding, escalation -> C13.3. Severity -> C13 severity.
