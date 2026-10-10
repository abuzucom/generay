# C10 Zone rules over time and tz data

(sources: PA-9, 34, 35, 52, 93, 133; inbound from PA-19, C6.5, C8.2, C8.4, C9.4) Approved by the user.

Scope: zone rules and identifiers changing over time, storing future
local commitments so rule changes apply correctly, the copies of tz data
in a system and how fast they update, hand-maintained zone data, and
historical zone data. DST mechanics are C11. Differences between zones
are C12. Abbreviations and GMT are C13. Choosing a user's or entity's
zone is C14. Leap-second lists are C17.

- C10.1 Zone rules and offsets change.
  - Facts (tzdata 2026b, verified): DST rules change (Mexico City dropped
    DST in 2022 to 2023; Egypt restored it in 2023). Standard offsets
    change: Pyongyang +09:00 to +08:30 (2015) and back (2018); Caracas
    -04:00 to -04:30 (2007) and back (2016); Moscow +03:00 to +04:00
    all year (2011) and back (2014); Istanbul +03:00 all year from 2016;
    Whitehorse -07:00 all year from 2020; Samoa -11:00 to +13:00 (2011);
    Nuuk -03:00 to -02:00 (2023); Almaty +06:00 to +05:00 (2024-03-01);
    Asuncion permanent -03:00 (late 2024). The zone a program serves
    changes (expansion, relocation, region moves), and a user's zone
    changes (travel, relocation, device auto-update mid-session). "The
    standard offset" is not well defined: tzdata models Ireland's winter
    and Morocco's Ramadan time as negative DST, other builds do not, and
    this host reads Morocco's offset-minus-DST as +00:00 in both February
    and July (verified).
  - In code: hardcoded offsets for named places (`-05:00` for New York),
    hand-written DST rules (C11), a global `APP_TZ` for every user and
    entity, standard offsets stored or reused for all dates, "standard"
    computed as offset minus DST and treated as fixed, historical
    conversions with today's offset, user zone read once at signup and
    never refreshed, long-lived caches of offsets or UTC conversions.
  - Fix: store IANA zone IDs, not offsets or abbreviations. Make the zone
    an attribute of the user, location, or entity. Ask the library for
    the full offset at each instant, never splitting it into standard and
    DST parts for business logic (BP-1).
  - Not a finding: protocols or contracts defined in UTC or a fixed
    offset by design. Full-offset library handling with canonical IDs.
- C10.2 Future local commitments and their anchors.
  - Facts: a future local time is fixed only when it happens. Notice can
    be days (C10.3). Pending legislation could change rules at short
    notice (EU 2019 Parliament vote not adopted by the Council; US
    Sunshine Protection Act passed the Senate in 2022, not enacted).
    iCalendar invites can embed `VTIMEZONE` rules that go stale against
    the recipient's tzdata. Commitments are anchored differently: local
    wall time in one zone (a clinic appointment), a fixed instant (global
    launch, broadcast, satellite pass), another party's zone (organizer's
    meeting; only one local time can stay fixed across zones), an elapsed
    duration ("24 hours after purchase"), a jurisdiction's rule, or an
    astronomical event. RFC 5545 distinguishes `DTSTART` with `TZID`
    (local anchor) from a `Z` value (instant anchor). A rule change can
    make a stored local time nonexistent or ambiguous.
  - In code: future local events converted to UTC once at write time, so
    they do not move when rules change. All future events stored as local
    time plus zone and recomputed after every tz update, moving
    instant-anchored events. Cross-zone conversions for future dates
    computed once and stored (each attendee's local time at booking).
    Long-range schedules materialized with today's rules (timetables,
    broadcasts, billing runs) and never regenerated. Future offsets in
    columns or static tables in apps and bundles. Contracts or configs
    written as paired local times ("14:00 London = 09:00 New York").
    Embedded `VTIMEZONE` trusted over the IANA zone it names. Recomputed
    times with no participant notification or gap handling. Tests
    asserting future offsets as literals (they break on tz updates, and
    editing the literal is the tempting wrong fix).
  - Fix: model the anchor explicitly per commitment type. Store past
    events as UTC instants (optionally with the offset in effect). Store
    local-anchored future events as local date-time plus zone ID and
    resolve at use. After a tz update, recompute only commitments whose
    anchor depends on the changed zone, apply the gap and overlap policy
    (C11), keep previous values for audit, and notify participants with
    old and new times. Regenerate materialized schedules on tz updates.
    Prefer current tzdata over embedded `VTIMEZONE` when `TZID` names an
    IANA zone, where the product allows. Derive expected future offsets
    in tests from the library, or pin the tzdata version.
  - Not a finding: past events stored as UTC instants. Future events
    whose requirement is a fixed instant. Commitment models with explicit
    anchors and a tested rule-change process.
  - Escalate: future events with legal or financial effect stored only as
    UTC instants. Commitment types whose anchor is not stated (especially
    multi-zone meetings and legal deadlines). Pending legislation
    affecting served zones. Long-lived contracts or schedules written as
    paired cross-zone local times.
- C10.3 tz data copies and update latency.
  - Facts: notice can be days (Egypt cancelled DST in 2016 days ahead;
    Lebanon reversed a 2023 postponement within days). The tz maintainers
    ask for a year of notice and often get less. Official and practiced
    time can differ (parts of Xinjiang keep UTC+6; tzdata `Asia/Urumqi`
    uses +06). Each layer carries its own copy and update path: OS
    `/usr/share/zoneinfo`; Java runtime tzdb (JDK release or TZUpdater);
    Python `zoneinfo` (system data or the `tzdata` package) and pytz (own
    copy); Node and browsers (bundled ICU); Android (OS, and system
    updates since Android 10) and iOS (OS); MySQL zone tables loaded once
    by `mysql_tzinfo_to_sql`; Postgres (compiled-in or system); container
    images and pinned packages (until rebuilt); embedded firmware (maybe
    never); bundled library data (moment-timezone data files, Noda Time
    TZDB file), whereas Luxon and date-fns-tz use platform `Intl` data.
    Mobile apps wait for store review. Layers on different versions
    disagree about the same instant. Era data needs updates too (Reiwa,
    C6.5).
  - In code and operations: tz data updated only with long-cycle
    application releases. Bundled data pinned in bundles, packages, or
    lockfiles with no owner. No emergency path to correct a region.
    Reminders and schedules computed far ahead and never recomputed.
  - Fix: treat tz data like a security patch, with a fast path
    independent of feature releases. Inventory every copy, its version,
    and owner, and alert on IANA `tz-announce` releases. Prefer platform
    data that updates automatically over bundled copies, or give bundled
    copies an update pipeline. Keep versions aligned across layers.
    Provide an audited operator override for emergencies. Recompute
    dependent schedules after updates (C10.2).
  - Not a finding: a documented, tested fast tz update process.
  - Escalate: products serving regions with a history of short-notice
    changes and no fast update path.
- C10.4 Zone identifiers change.
  - Facts: zones split (`America/Ciudad_Juarez`, 2022), are renamed
    (`Europe/Kiev` to `Europe/Kyiv`, 2022; `Asia/Calcutta` to
    `Asia/Kolkata`), and become links. In 2022 tzdata merged zones whose
    data matched since 1970 into links and moved older history to the
    optional `backzone` file, so builds differ in historical data (this
    host still returns Amsterdam's own 1930 offset). Backward links are
    not shipped everywhere: this host cannot load `Europe/Kiev` or
    `Asia/Calcutta` (verified).
  - In code: stored legacy zone names failing to load after an upgrade or
    on a minimal image. Zone lists missing newly split zones.
  - Fix: canonicalize zone IDs on input and migrate stored legacy names.
    Ship backward links where legacy data exists. Add a check (for
    example in CI) that every listed or stored ID loads and is canonical.
  - Escalate: stored zone IDs or offsets whose meaning for past dates
    cannot be established.
- C10.5 Hand-maintained zone data.
  - Facts: tzdata changes often (Debian changelog on this host,
    approximate releases per year: 2020: 6, 2021: 5, 2022: 7, 2023: 4,
    2024: 2, 2025: 3, 2026 so far: 2). Each zone carries a full
    transition history. Display names and translations come from CLDR,
    including metazone names such as "Pacific Time". Mappings to Windows
    IDs and countries change too.
  - In code: arrays such as `{"(GMT-05:00) Eastern Time", -5}`. Database
    zone tables with a fixed offset and a DST flag. Custom DST rule
    tables. Hand-maintained country-to-zone or Windows-to-IANA maps.
    Lists with stale offsets (Kazakhstan at +06:00 after 2024).
  - Fix: generate zone lists, offsets, rules, and names from tzdata and
    CLDR through the platform or a library. Curated subsets store only
    IANA IDs and derive everything else at run time. Track tz releases.
  - Not a finding: curated IANA ID lists with library-computed offsets
    and names.
  - Escalate: zone lists that are contractual or regulatory, with no
    stated update process.
- C10.6 Historical zone data.
  - Facts: before standard time, places used local mean time
    (`America/New_York` before 1883-11-18 is -04:56:02, verified). tzdata
    is reliable mainly from 1970, and pre-1970 data depends on the build
    (C10.4). Passing a pytz zone as `tzinfo=` to the `datetime`
    constructor attaches the zone's first (LMT) offset, a library misuse
    under BP-1. (Offsets with seconds are C12.)
  - In code: historical local times converted with modern rules or
    today's offset, or with LMT offsets nobody expected. pytz zones
    passed to `tzinfo=`.
  - Fix: use `zoneinfo` or pytz `localize`. Note tzdata's limits before
    1970 and keep original historical text (C6.6).
  - Escalate: historical data where the source's zone handling cannot be
    established.
- Proposed severity (for the user to decide), per check: HIGH when future
  appointments, deadlines, billing, broadcasts, travel, or expiries
  shift or fail to shift after a rule change; a hardcoded or stale offset
  or rule is wrong on a core path; core scheduling depends on tz data
  that cannot be updated quickly; or unloadable zone IDs reject stored
  times. MEDIUM for stale tz data without an update process, missing
  notifications, missing zones and names, static offset tables in
  display, and historical display. LOW for test-only code.

Point ledger for C10:
- Inbound from PA-19: LMT and New York 1883, tzdata reliable from 1970,
  pytz `tzinfo=` misuse, historical local times with modern rules ->
  C10.6. Future rules are projections -> C10.2.
- Inbound from C6.5: era data currency -> C10.3.
- Inbound from C8.2: future local time fixed only when it happens ->
  C10.2.
- Inbound from C8.4: user, location, and future values stored as offsets
  -> C10.1 and C10.2.
- Inbound from C9.4: storage of future local events -> C10.2.
- PA-9: served zone and user zone change, rule-change examples,
  hardcoded offsets, global constant, abbreviations or offsets stored,
  cached offsets, user zone read once, zone-ID fix, entity-attribute fix,
  library fix, UTC-by-design not-a-finding -> C10.1. Short notice ->
  C10.3. Future events converted once, past and future storage fixes,
  fixed-instant not-a-findings, legal escalation, wall-time-versus-instant
  escalation -> C10.2. Stale layers list, version disagreement,
  operational-dependency fix -> C10.3. Hand-written DST rules -> C11
  (inbound reference). Severity -> C10 severity.
- PA-34: rule changes, pending legislation, `VTIMEZONE`, stored future
  conversions, materialized schedules, stored offsets and static tables,
  paired local times, embedded rules trusted, literal future-offset
  tests, all fixes, not-a-finding, both escalations -> C10.2. Different
  systems updating at different times -> C10.3. Severity -> C10 severity.
- PA-35: notice, Xinjiang, update latency per layer, bundled versus
  platform libraries, long-cycle updates, pinned data, no emergency
  path, all fixes, not-a-finding, escalation -> C10.3. Recompute far-ahead
  reminders -> C10.2 and C10.3. Severity -> C10 severity.
- PA-52: standard-offset change examples, standard-offset ambiguity,
  stored standard offsets, offset-minus-DST code, historical conversions
  with today's offset, full-offset fix -> C10.1. Zone ID splits and
  renames, unloadable names, missing new zones, canonicalize and
  backward-link fixes, escalation -> C10.4. Refresh zone lists -> C10.5.
  Severity -> C10 severity.
- PA-93: release counts, transition histories, CLDR names, mappings,
  hardcoded arrays, offset-and-flag tables, custom rule tables, maps,
  stale lists, generate fix, curated-subset fix, tracking,
  not-a-finding, escalation -> C10.5. Structure changes, backzone,
  Amsterdam build check, CI load check -> C10.4. Custom DST tables -> C11
  by reference. Severity -> C10 severity.
- PA-133: all anchor types, RFC 5545 anchors, rule-change gaps, both
  storage failure modes, missing notification, missing gap handling,
  anchor fix, selective recompute fix, notification fix, not-a-finding,
  escalation -> C10.2. Governing party -> C14 by reference. Severity ->
  C10 severity.
