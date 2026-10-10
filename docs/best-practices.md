# Best practices

User-supplied best practices (BP), recorded as summaries. Each names the checks
that apply it.

- BP-1: When a trusted time library exists, prefer it over rolling your
  own time handling.
  - The check must not guess which library is trusted. It reads a
    maintained favored-library registry, keyed by language and
    architecture (keys below).
  - JavaScript: Luxon (`moment/luxon`) is preferred. Day.js
    (`iamkun/dayjs`) is a named alternative.
  - Not a finding: using a listed alternative instead of the preferred
    library.
  - Not a finding: using a library absent from the registry.
  - Findings: (a) hand-rolled time handling where a trusted library
    exists; (b) misuse of a library, for example Day.js timezone code
    without the `utc`/`timezone` plugins loaded.
  - Registry keys: language, plus architecture. Architecture covers
    runtime/platform (Node vs browser, JVM vs Android, iOS, .NET),
    system layer (frontend, backend API, database, queue, scheduler,
    CLI), and framework (Django, Spring, Rails, Next.js).

- BP-2: Never depend on a single source of time; diversify across as many
  reliable sources as is reasonable.
  - What it means:
    - No clock, server, operator, or technology is the only thing a
      system's time rests on.
    - Diversity has several dimensions, and each removes a shared
      failure:
      - operator and upstream (C27.10, C27.15)
      - jurisdiction and government (C27.12)
      - technology: network NTP or NTS, GNSS with PPS, PTP, radio time,
        a disciplined RTC or holdover oscillator (C27.16)
      - GNSS constellation (C27.12, C27.19)
      - network path and address family (C27.13)
      - leap-second policy (one policy, but several sources using it)
        (C27.4)
    - Sources are combined by agreement, not by a fixed winner (C27.22),
      and their live count and agreement are monitored (C27.15, C26.3).
    - Applications apply the same idea: keep server time, device time,
      and GNSS fix time as separate labeled values instead of trusting
      one (C15.4, C27.20).
  - What "reliable" excludes:
    - Sources that are correlated with each other (same operator, same
      upstream) add count, not independence (C27.10).
    - Unvetted or unhealthy sources can hurt: NTP's selection only works
      while correct sources outnumber wrong ones, so adding several bad
      sources can make a wrong majority (C27.8, C27.15).
    - Sources that cannot be reached from the deployment, or that the
      operator restricts, do not count (C27.9, C27.14).
  - What "within reason" means:
    - Where a wrong source must be outvoted, at least four independent
      sources (C27.15); more where some may be unreachable.
    - Ordinary clients get diversity through an internal tier that holds
      the diverse upstreams, instead of each client querying many public
      servers (C27.17, C27.14).
    - Stay within operators' polling rules and do not add public load
      without need (C27.9, C27.14).
    - Precision references (GNSS, PPS, PTP) only where accuracy needs
      them, but always with an independent cross-check (C27.4, C27.21).
  - Findings this practice supports (not new checks; the checks already
    exist): single-source configurations, single-operator or
    single-government dependence, GPS-only timing, one source that always
    wins, no holdover, unmonitored source counts (C27.7, C27.10, C27.12,
    C27.15, C27.16, C27.17, C27.19, C27.22).
  - Not a finding: a standalone device or small system whose time does
    not drive decisions, using the platform's default multi-source sync.
  - Method: `both`. Scans count sources, operators, domains, refclocks,
    and `trust` flags in configs; the model judges independence,
    reliability, and what the system needs.
  - Coverage: no new check needed; BP-2 is the shared principle behind
    the checks listed above, and the main document's time-sync module
    should state it first (user priority on time sync).

- BP-3: When every other source fails, an RTC alone is an acceptable
  last resort, but only if the system is designed for RTC-only
  operation.
  - What RTC-only time is like (drift computed here; part ratings from
    datasheets, not verified):
    - Drift: a plain 32.768 kHz crystal rated around 20 ppm drifts about
      1.7 s a day, 52 s in 30 days, and 10.5 minutes a year; at 100 ppm,
      about 8.6 s a day and 53 minutes a year. A temperature-compensated
      RTC rated around 2 ppm drifts about 0.17 s a day and 1.1 minutes a
      year (computed from the ratings).
    - Drift changes with temperature and age, so a fixed correction
      decays (PA-13).
    - Power loss or a dead backup battery resets it to the epoch, a
      firmware default, or garbage (PA-12).
    - Many RTCs count whole seconds, have limited year registers or leap
      logic valid only to 2099 (C2.1, C22.1), know nothing of leap
      seconds or DST, and on Windows hold local time by default (C15.1).
  - Design requirements:
    - Keep UTC in the RTC, never local time (C9, C15.1).
    - Track time since the last good sync and compute an error bound
      (rated or measured drift times elapsed time), and expose it with
      the time.
    - Mark data produced on RTC-only time with its source and bound, so
      it can be corrected later (C16.3, C8.1).
    - Calibrate when a reference is available: measure drift and apply
      it (for example chrony `rtcfile` and `rtcautotrim`, or the drift
      record in `/etc/adjtime` with `hwclock --adjust`), and keep the RTC
      updated from synced time (C27.16).
    - Detect resets and nonsense: a floor (build time or persisted last
      known good time) and a ceiling, battery-low signals, and refusal to
      act on implausible time (C15.2).
    - Limit what RTC-only time may decide: use wider tolerances or defer
      decisions whose required accuracy exceeds the bound (certificate
      and token validity, deadlines, billing), and say so to users or
      operators.
    - Keep elapsed time on monotonic clocks and order events with
      sequences, since RTC time can repeat after a reset or correction
      (C18.1, C19.2, C19.4).
    - Rejoin carefully: when a source returns, slew or step at a planned
      point, and record the correction applied to RTC-era data (C27.18).
    - Plan battery replacement, and know the RTC's range and leap-year
      limits for the device's service life (C25.3).
  - Findings this practice supports: systems that can fall back to
    RTC-only time but compute no error bound, mark no data quality,
    detect no reset, never calibrate, or let RTC-only time decide
    accuracy-sensitive outcomes. Related checks: C15.2, C27.5, C27.16,
    C27.18, C22.1.
  - Not a finding: offline devices whose RTC-only behavior is designed as
    above and documented.
  - Method: `both`. Scans find RTC access (`/dev/rtc`, `hwclock`, RTC chip
    drivers, `rtcfile`, `rtcsync`) and the absence of drift files; the
    model judges whether the design meets the requirements above.
  - Coverage: implemented by the new check C27.24 "RTC-only operation
    must be designed" (user-approved), with related parts in C15.2,
    C27.5, C27.16, C27.18, and C22.1.

- BP-4: Roughtime is an option when NTP is unreachable or unreliable, or
  when Roughtime is operationally the better fit
  (https://roughtime.googlesource.com/roughtime).
  - Source: the project page text supplied by the user in this session
    (the page itself and the IETF draft page are blocked by this
    container's egress proxy, verified). Facts marked "(source)" come from
    that text; others are not verified here.
  - What Roughtime is:
    - A protocol for rough time synchronization that is secure, does not
      depend on any one server, and leaves clients with cryptographic
      proof when a server misbehaves (source).
    - "Rough" means within about 10 seconds of correct time; the page
      says serious needs should use NTP or PTP (source).
    - Its motivating case: about a quarter of certificate errors Chrome
      showed appeared to come from bad local clocks, which needs little
      precision to fix (source).
    - Every reply carries a public-key signature, unlike secure NTP
      schemes that negotiate a symmetric key; anyone can verify a
      public-key signature, so replies work as timestamps and servers can
      check each other (source).
    - The client sends a random nonce; the reply contains the time, the
      nonce, and a signature over both, proving freshness and origin
      (source).
    - Chaining: the next request's nonce is a hash of the previous reply
      with a random value, proving it was made later. If a later reply
      shows an earlier time, the client holds proof of misbehavior
      (source).
    - Two servers can prove something is wrong but not which time is
      right; half a dozen or more independent servers give chains of proof
      and enough good replies to establish the correct time (source).
    - Not verified here: the signature algorithm (Ed25519 in published
      descriptions), the reply's uncertainty radius, the IETF draft's
      current version, and which operators run public servers.
  - When it is the better option:
    - Bootstrapping a device with no trustworthy clock: Roughtime's
      signatures rely on pinned public keys, not on certificate validity
      dates, so it avoids the problem where a wrong clock breaks TLS and
      blocks fetching the right time (PA-12, PA-137).
    - When NTP is blocked, unreliable, or unauthenticated, and roughly
      correct, authenticated time is enough (PA-137, PA-146).
    - As an independent cross-check on NTP or GNSS for security decisions
      (certificate and token validity), adding technology diversity
      (BP-2, PA-148).
    - Giving RTC-only devices a secure way to correct and floor their
      clock when briefly online (BP-3).
  - Using it correctly:
    - Pin server public keys from a trusted, updatable list, and query
      several independent servers (half a dozen or more where the correct
      time must be established, per the source) from different operators
      (BP-2).
    - Treat the result as an interval: use the reply's uncertainty where
      the protocol version provides it, and keep it with the time
      (PA-140).
    - Do not use it where better than about 10 s is needed; pair it with
      NTP, PTP, or GNSS for precision (source; PA-150).
    - Track protocol versions, and keep the client maintained as the
      draft evolves.
    - Keep and act on the signed evidence when servers disagree (PA-143).
    - Adding a Roughtime client is a new dependency and needs user
      approval.
  - Findings this practice supports: security decisions on devices that
    cannot reach authenticated time, with no Roughtime or equivalent
    fallback (C27.1, C27.11); Roughtime used with a single server,
    unpinned keys, ignored radius, or as a precision source.
  - Not a finding: systems with authenticated, diverse NTP or NTS that do
    not need Roughtime; not using Roughtime is never a finding by itself.
  - Method: `both`. Scans find Roughtime client use, key lists, server
    counts, and radius handling; the model judges whether the use fits the
    need.
  - Coverage (user decision): folded into C27.11, not a separate check.
