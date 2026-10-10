# C14 Determining the governing zone

(sources: PA-17, 89, 97, 98, 99, 100, 101, 126; inbound from PA-109,
PA-67, C3.3, C4.1, C8.3, C8.4, C10.2, C12.4) Approved by the user.

Scope: which zone and calendar govern each decision, how a user's zone is
captured, and why zones cannot be inferred from clocks, offsets,
addresses, networks, phone numbers, states, or proximity. Zone rules are
C10. Offsets as data are C8.4. Privacy of location data is out of scope
(abuzucom/havel).

- C14.1 Values crossing the client-server boundary.
  - Facts: users are spread across zones while servers run in UTC or the
    operator's zone. Users travel. A VPN changes apparent location but not
    device zone. Firefox `privacy.resistFingerprinting` and Tor Browser
    report UTC. Profile and device zones can differ. Server fleets can
    differ from each other (C9.2). Verified examples: a date picked as
    2026-07-01 in Tokyo and sent with `toISOString()` arrives as
    2026-06-30T15:00Z and is stored as June 30; a server date
    "2026-07-01" shown in Los Angeles displays as 6/30/2026.
  - In code: date-times sent without an offset in either direction.
    Date-only values sent as instants (C8.3). "Today" and day boundaries
    computed in the server zone for user-facing logic (streaks, "due
    today", daily limits resetting at server midnight). Server rendering
    in the server zone and client hydration in the client zone, so output
    flickers or hydration fails. Zone-less inputs (`datetime-local`,
    pickers) interpreted in the server zone. Emails, notifications, and
    exports rendered in the server zone without a label. Report filters
    from the client's local date applied to UTC days.
  - Fix: send instants with an offset or `Z`, dates as `YYYY-MM-DD`, and
    local intent as local date-time plus IANA ID. Compute user-facing day
    boundaries in the user's zone on the server. Render server output in
    the user's stored zone with a label, or defer formatting to the
    client.
  - Not a finding: service-to-service traffic that is UTC by explicit
    contract.
- C14.2 Capturing the user's zone.
  - Facts (verified): an offset does not identify a zone (19 zones at
    -07:00 in January 2026, 16 in July). Client clocks can be wrong by any
    amount, and right wall time with the wrong zone setting gives offsets
    off by whole hours (C15). Client-server comparison includes delay and
    skew, so rounding can pick the wrong offset, especially for non-hour
    zones. JS `getTimezoneOffset()` has an inverted sign and varies by
    date (New York 240 in July, 300 in January). Privacy modes report
    UTC. Users may want a zone other than the device's.
  - In code: `clientNow - serverNow` rounded to an offset and stored as
    the user's zone. Today's `getTimezoneOffset()` sent and used for
    every date, or mapped to an arbitrary zone. Sign errors. Offsets
    stored instead of zone IDs.
  - Fix: read the IANA zone from the platform
    (`Intl.DateTimeFormat().resolvedOptions().timeZone`, OS settings) as
    a default, confirm it with the user, store the ID, and let the user
    override it. Ask when the platform reports UTC from a privacy mode.
    Compute offsets per date from the zone ID. Never infer zones from
    clock differences.
  - Not a finding: an offset taken for one instant to display that
    instant, with the zone ID stored separately.
- C14.3 Zones from addresses, regions, and official status.
  - Facts (tzdata `zone1970.tab` and 2026b, verified): zones per country
    code: US 29, Russia 27, Canada 23, Brazil 16, Australia 13, Mexico
    12, Argentina 12, Kazakhstan 7, Indonesia, Greenland, and Chile 4.
    Overseas and island regions span distant zones (France, UK, Denmark,
    Spain, Portugal, Chile, Ecuador). States and provinces split:
    Indiana 8 zones (6 Eastern, 2 Central); Kentucky, Michigan, North
    Dakota (three county-specific Central zones), Idaho and Oregon,
    Alaska (7 zones, Adak an hour behind), Arizona with Navajo and Hopi,
    Florida, Tennessee, Texas, Kansas, Nebraska, South Dakota; Ontario,
    British Columbia, Nunavut, Saskatchewan; Broken Hill in New South
    Wales on South Australian time. Towns differ (Creston BC on
    `America/Phoenix`, Fort Nelson its own zone, Atikokan on
    `America/Panama`, Lloydminster straddling two provinces, Ciudad
    Juarez split in 2022). County assignments change (Indiana 2006 and
    2007, North Dakota 2003 and 2010). City names repeat. Postal codes
    are delivery routes that cross county, state, and zone lines, PO
    boxes sit away from residences, APO/FPO codes carry no location, and
    codes change. Some locations have competing official times: Crimea
    (`Europe/Simferopol` +03:00 versus `Europe/Kyiv` +02:00 in January),
    the West Bank (`Asia/Hebron` versus `Asia/Jerusalem`, differing
    around 2026-03-27 and 2026-10-24). Official and practiced time differ
    (Xinjiang, Phenix City). Some places have no official zone: ships on
    the high seas, Antarctic stations choosing a base's time (McMurdo and
    South Pole on New Zealand time), the ISS on UTC. Ethiopia's everyday
    hour count starts about 06:00 under one official zone. People do not
    always keep their address's zone.
  - In code: country-to-zone, state-to-zone (`{"IN":
    "America/Indiana/Indianapolis"}`, `{"FL": "America/New_York"}`), or
    ZIP-to-zone tables with one entry each. Zone from a billing or
    mailing address used for deadlines. Historical records assigned
    today's county rules. Location-to-zone functions returning exactly
    one zone with no ambiguity. Disputed regions fixed in code without a
    product decision. Community time mapped by coordinates alone. Ships,
    stations, and craft assigned a zone by position.
  - Fix: use the user's or site's stored IANA ID, confirmed by the user,
    and offer every valid zone for a location. When location must decide,
    use coordinates with a maintained boundary dataset at the date in
    question, as a default to confirm. Use `zone1970.tab` for country
    lists, never one-to-one. Make zone choices for disputed regions an
    explicit, documented product decision reviewed with legal or policy
    owners. Store the zone a ship, station, or craft declares.
  - Not a finding: location-derived defaults the user confirms or can
    change. User-selected zones from the full IANA list.
  - Escalate: deadlines or legal windows tied to an address or state
    without a stated governing-zone rule. Products serving disputed
    regions or communities with competing official times without a zone
    policy.
- C14.4 Zones from networks and phone numbers.
  - Facts (2026b, verified): IP geolocation is an estimate, better at
    country than city level, stale as addresses move, and published with
    accuracy radii. Traffic exits far from users: VPNs, proxies, Tor,
    corporate gateways, carrier-grade NAT, satellite internet, in-flight
    and shipboard links, privacy relays, cloud and data-center sources.
    ISP names say nothing about zone. Calling codes span zones: +1 from
    American Samoa (-11:00) to Guam (+10:00); +7 from Kaliningrad (+02:00)
    to Kamchatka (+12:00); +61 from Sydney (+11:00 in January) to
    Christmas Island (+07:00) and Cocos (+06:30); shared codes such as
    +262. Area codes span zones (850 Eastern and Central, 308 Central and
    Mountain). Numbers move with people and roam. Toll-free, VoIP, and
    global codes (+881, +882) carry no location. libphonenumber's
    time-zone mapper returns a list of zero or more zones. US
    telemarketing rules (TCPA, 47 CFR 64.1200) bar solicitation calls
    before 08:00 or after 21:00 at the called party's location, with
    narrower state windows.
  - In code: GeoIP or ISP lookups used as the user's zone for deadlines,
    notifications, billing, or server rendering, cached and never
    revisited. Area-code or country-code tables returning one zone. Call
    or SMS quiet hours and notification schedules keyed on phone
    prefixes.
  - Fix: use the device's IANA zone and the user's confirmed setting as
    the authority. Use IP-derived zones only as a fallback default with
    accuracy information, never for legal or financial deadlines. Where
    only a number is known, treat every possible zone as possible and
    send only when all allow it. Use maintained numbering metadata
    through a library (new dependencies need approval). Re-check when the
    device zone changes.
  - Not a finding: IP- or phone-derived pre-filled defaults the user
    confirms.
  - Escalate: features relying on IP location for time decisions without
    a stated accuracy. Contact-time compliance where the location source
    and rules are not stated.
- C14.5 Nearby places and service areas.
  - Facts (verified): Apia and Pago Pago are about 78 miles apart
    (computed) and 24 hours apart: at 12:00 UTC on 2026-01-15 both read
    01:00, on different dates. The Diomede Islands, about 2.4 miles apart
    (commonly cited), are 21 hours apart (`America/Nome` versus
    `Asia/Anadyr`). Across any one-hour boundary nearby places are on
    different dates for an hour a day. Same-zone places can differ in DST
    (Arizona and the Navajo Nation).
  - In code: radius searches ("open now near you", "events today within
    50 miles") evaluated in the searcher's zone. Same-day cutoffs applied
    to a whole service radius with one zone. Geofenced notifications
    timed in one zone. Distance clusters assumed to share a zone.
  - Fix: store an IANA zone with each place, venue, or user. Evaluate
    "open now", "today", and cutoffs in each place's zone. Show the
    place's local time, and the viewer's where they differ.
  - Not a finding: radius features whose service area is documented and
    validated as one zone.
  - Escalate: service areas crossing zone boundaries or the date line
    without a stated rule for "today".
- C14.6 Which party's zone governs each decision.
  - Facts: courts (US federal electronic filing ends at midnight in the
    court's zone, FRCP 6(a)(4)(A)), regulators and tax authorities,
    contracts (governing law, notice provisions), merchants (store hours,
    warehouse shipping cutoffs, support hours, maintenance windows),
    venues, markets and banks (exchange hours, settlement, accrual and
    payment cutoffs), recipients (telemarketing, C14.4), reporting
    entities, and multi-party events (organizer or agreed zone) each set
    their own. "The customer" may have several zones (profile, device,
    current location, billing, shipping), and business accounts span
    zones. Some rules are not zones at all (business days, holidays,
    fiscal years, calendars).
  - In code: one `customer.timezone` used for every decision. Legal,
    contractual, or regulatory deadlines in the customer's zone where the
    rule names another. Merchant cutoffs and venue times enforced in the
    viewer's zone. Periods (day, month, year, weekday) derived from a UTC
    instant for something whose period is local (C3.3, C4.1).
  - Fix: keep a decision table naming the governing zone and calendar
    for each time-dependent decision, reviewed with product and legal
    owners. Store each relevant zone as an IANA ID (customer, account,
    merchant, venue, warehouse, jurisdiction). Compute each rule in its
    own zone, and show users both the governing time and their own when
    they differ.
  - Not a finding: decisions documented as governed by the customer's
    zone.
  - Escalate: legal, contractual, regulatory, or business boundaries
    ("daily limit resets at midnight", "order by end of day", effective
    dates) whose governing zone is not stated.
- Proposed severity (for the user to decide), per check: HIGH when a
  wrong, inferred, imposed, or single-party zone drives deadlines,
  bookings, birthdays, due dates, delivery windows, regulated contact
  times, billing, or notifications on a core path, or takes a political
  position the product did not decide. MEDIUM for display defaults,
  rendering mismatches, search results, reminders, and reports. LOW for
  test-only code.

Point ledger for C14:
- Inbound from PA-109: all facts, code patterns, checks, fixes,
  not-a-finding, escalation -> C14.3. Severity -> C14 severity.
- Inbound from PA-67: country-to-zone mapping with several zones per
  country -> C14.3.
- Inbound from C3.3: which zone defines a period -> C14.6.
- Inbound from C4.1: which zone governs a weekday -> C14.6.
- Inbound from C8.3: governing zone for dates and effective dates ->
  C14.6 escalation.
- Inbound from C8.4: offsets mapped back to zones -> C14.2.
- Inbound from C10.2: governing party for a commitment -> C14.6.
- Inbound from C12.4: coordinates and boundary dataset -> C14.3.
- PA-17: user spread, travel, VPN, privacy UTC, profile versus device,
  fleets, verified Tokyo and Los Angeles examples, all code patterns,
  checks, offset and date wire fixes, server-side boundary fix, rendering
  fix, not-a-finding -> C14.1. Capture user zone fix -> C14.2. Whose-zone
  escalation -> C14.6. Date-only details -> C8.3 by reference. Severity
  -> C14 severity.
- PA-89: all facts, code patterns, checks, fixes, not-a-finding -> C14.2.
  Governing-zone escalation -> C14.6. Severity -> C14 severity.
- PA-97: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C14.3. Severity -> C14 severity.
- PA-98: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C14.4. Privacy-law note -> scope line (havel). Severity
  -> C14 severity.
- PA-99: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C14.4. Severity -> C14 severity.
- PA-100: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C14.3. Compliance-window fix -> C14.4. Severity -> C14
  severity.
- PA-101: Apia and Pago Pago, Diomede, one-hour boundaries, DST
  observance, all code patterns, checks, fixes, not-a-finding,
  escalation -> C14.5. China and Afghanistan -> C12.4. Phenix City ->
  C14.3. Severity -> C14 severity.
- PA-126: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C14.6. Severity -> C14 severity.
