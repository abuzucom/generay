# C15 Clock accuracy and client-server skew

(sources: PA-11, 12, 13, 14, 15, 16, 103; inbound from C7.5, C14.2) Approved by the user.

Scope: wall clocks that are wrong, jump, or drift; the damage from large
errors; client and server clocks disagreeing; estimating offsets; and
the server staying correct whatever client time does. Clock rates,
relativity, and synchronization of signals are C16. Leap seconds and
time-scale offsets are C17. Elapsed-time measurement, timers, and
monotonic clocks are C18. Ordering, IDs, and monotonic timestamps are
C19. Ranges of representable times are C22.

- C15.1 Clocks are wrong and jump.
  - Facts: quartz drifts by seconds a day without sync. NTP can be
    absent, blocked, or misconfigured, and often completes only after
    boot. VMs drift or jump after pause, snapshot restore, or live
    migration, and containers inherit the host clock. Boards without a
    battery-backed clock, and dead CMOS batteries, boot at the epoch or a
    stale time. Users set clocks by hand, wrongly or to cheat (trials,
    games). Dual-boot machines keep the RTC in local time (Windows) or
    UTC (Linux) and end up hours off. Sync steps the clock either way, and
    providers smear or step leap seconds differently (C16, C17).
  - In code: client- or device-supplied timestamps trusted for ordering,
    expiry, audit, trials, or rate limits. Token and certificate checks
    (`exp`, `nbf`, `iat`) with no skew leeway, or leeway so large it
    defeats the check. Licensing or trial logic trusting the local clock.
    Timestamps from different machines compared as one clock. No sanity
    bounds, so dates before the software existed or far in the future are
    stored. (Wall-clock durations are C18; ID generators are C19.)
  - Fix: assign authoritative timestamps on the server and keep client
    time as a separate, untrusted field. Allow a small, explicit leeway in
    token checks. Check sync state and monitor offset (C27). Reject or flag
    timestamps outside sane bounds.
  - Not a finding: a user's own device time shown for their reference.
    Client time recorded as a labeled, untrusted extra field.
  - Escalate: security or billing decisions on a clock whose sync status
    cannot be established.
- C15.2 Large clock errors and destructive actions.
  - Facts: devices without a working RTC start at the epoch, a firmware
    default such as 2000-01-01, or the build date. Bad RTC reads give
    dates decades off. GPS week numbers wrap every 1,024 weeks (1999-08-22,
    2019-04-07, next 2038-11-21), and affected receivers jumped back
    nearly 20 years. VM restores set the clock back weeks. Typed or
    forgotten test dates persist. Sync daemons can refuse or crawl on
    large offsets (C27.2).
  - In code: retention or cleanup deleting everything when the clock is
    far ahead. Mass expiry of sessions, tokens, licenses, and caches, or
    nothing expiring when it is behind. Catch-up schedulers running every
    missed occurrence after a forward jump (job storms, duplicate billing;
    C18). Sync cursors and watermarks set from a far-future clock, so
    later records sort below them forever (C19). Far-future time-based
    IDs (C19). TLS failing, so the device cannot reach an HTTPS time
    source. Tokens signed with a wrong clock already expired or valid for
    decades.
  - Fix: check "now" against a floor (build time, or a persisted last
    known good time) and a ceiling, and never accept a clock below the
    floor. Refuse, or cap per run, destructive time-based actions when the
    clock is implausible or just jumped. Bound catch-up by policy. Use
    sequence numbers or logical clocks for cursors. Configure sync to step
    large offsets at startup and authenticate it where needed (C27.2).
  - Not a finding: offline tools where a wrong clock affects only
    display. Test harnesses with a deliberate fake clock.
  - Escalate: destructive, financial, or security actions driven by a
    clock on hosts or devices whose sync cannot be established.
- C15.3 Clock error changes over time.
  - Facts: drift rate varies with temperature, age, and load. Steps,
    slews, and frequency corrections change error and rate. Sleep,
    suspend, VM pause, and migration add jumps. Smearing shifts a
    smeared clock against an unsmeared one. Each machine drifts
    differently, so skew between two machines changes. Either side of a
    client-server pair changes: user edits mid-session, network changes
    switching time source, app backgrounding, laptop suspend. "The server"
    is a fleet, so each request can hit a different clock. A CDN or HTTP
    cache serves a stored `Date` header, off by the response's `Age`.
    Measured offsets include variable, often asymmetric network delay.
  - In code: a client-server offset (`serverTime - Date.now()`) measured
    once at login or startup and reused for the session, or persisted (for
    example in `localStorage`) across sessions. No re-measurement on
    resume, visibility change, or network change. Offsets from cacheable
    responses without `Age`. One offset assumed for every server in a
    fleet. Each new sample accepted as-is, so offsets swing. Offsets
    measured without round-trip timing. Countdowns, auctions, and game
    timers driven by a one-time offset. Logs corrected with one global
    offset. Leases, locks, or consensus timeouts assuming a fixed skew
    instead of a bounded drift rate (lease safety under pauses is C18).
  - Fix: re-measure periodically and on resume, visibility, and network
    changes, and never persist offsets across sessions. Measure against
    an uncacheable endpoint (`Cache-Control: no-store`) or subtract
    `Age`. Estimate with round-trip timing (NTP-style midpoint), filter by
    lowest round-trip samples, and keep an error bound. Keep fleet clocks
    synced and monitored (C27.3). Enforce deadlines on the server, with client
    offsets for display only. Design leases for bounded drift with
    explicit uncertainty. Correct logs per segment between sync points.
  - Not a finding: display-only offsets refreshed on resume, with server
    enforcement.
  - Escalate: distributed correctness (leases, locks, leader election)
    depending on unstated skew bounds. Client features (auctions, timed
    exams, trading cutoffs) whose fairness depends on unstated offset
    accuracy.
- C15.4 Comparing client and server times.
  - Facts: client and server clocks are independent, users set devices
    by hand, and the two usually sit in different zones (C14.1).
  - In code: clients comparing a server-issued absolute expiry (`exp`,
    session end) with the local clock, causing early logout, refresh
    loops, or no refresh. Absolute expiry sent where a relative one works
    (cookie `Expires` instead of `Max-Age`, HTTP `Expires` instead of
    `Cache-Control: max-age`). Signed requests with client time checked
    for freshness (AWS S3 rejects with `RequestTimeTooSkewed` beyond 15
    minutes). TOTP codes rejected by device clock error. Client
    `createdAt` stored as authoritative, so chats sort out of order.
    Last-write-wins on client timestamps (ordering detail C19). Clients
    sending absolute filters (`since = Date.now() - 1h`). The same "must
    be in the future" rule giving different results on client and server.
    Relative labels ("5 minutes ago") showing negative or future values.
  - Fix: send relative durations (`expires_in`, `Max-Age`, `max-age`)
    and track them on the client with a monotonic clock (C18). Keep the
    server authoritative for ordering, expiry, and validation. Send
    server time in each response (HTTP `Date`) and estimate offset with an
    error bound (C15.3). Allow explicit skew windows in signing and TOTP,
    and use SDK skew correction. Clamp relative labels at zero.
  - Not a finding: purely local apps, and reminders in device time.
  - Escalate: offline-first apps where the client clock is the only time
    source for records that later sync (ordering design, such as hybrid
    logical clocks, needs a decision; C19).
- C15.5 Large client skew and recovery.
  - Facts: client clocks can be hours, days, or years off, users change
    them on purpose, and the right wall time with the wrong zone setting
    puts the UTC instant whole hours (or 30 or 45 minutes) off. Devices
    offline for long periods sync late or never.
  - In code: fixed skew tolerances (for example 5 minutes) with no
    recovery path or explanation. Offset estimation that clamps or drops
    large measurements as outliers. Clients scheduling server-relevant
    actions at absolute local times. Client caches holding absolute server
    expiries that never expire or always look expired (request storms).
    Client UUIDv7 values or timestamps far in the past or future accepted
    and indexed. Client timestamps from 1970 or decades ahead corrupting
    analytics, ordering, and retention. Offline queues replayed with
    far-off client times. Rate limits or replay windows keyed on client
    time.
  - Fix: detect large skew explicitly (compare with the HTTP `Date`
    header). Show an actionable error ("device clock is about 3 hours
    off") or correct automatically with SDK skew correction. Bound client
    timestamps on the server and always store the server receive time
    alongside. Never clamp or drop a large offset without handling it.
  - Not a finding: narrow security windows (signing, replay protection)
    whose failure path informs the user or corrects skew.
  - Escalate: security windows where widening tolerance for skewed
    clients weakens replay protection.
- C15.6 Staying correct when client time is illogical.
  - Facts: client time can look impossible: frozen (suspension,
    throttling, long offline periods), racing or crawling (speed hacks,
    simulations, broken hardware, extreme slewing), backward, impossible
    order (replies stamped before requests, "sent" after "received"), out
    of range (decades off, 1970), flipping zone between requests, or
    contradictory (retries with different times, several devices per
    account). Physics allows extremes: near a non-rotating black hole a
    stationary clock runs at `sqrt(1 - rs/r)` of a distant one (about
    0.95 at 10 rs, 0.71 at 2 rs, 0.30 at 1.1 rs, 0.10 at 1.01 rs,
    computed), and Earth-Mars one-way light time ranges from about 3.0 to
    22.3 minutes (computed), so deep-space links use delay-tolerant
    networking (Bundle Protocol, RFC 9171). Everyday suspension and speed
    hacks produce the same effect. (Relativistic corrections are C16.)
  - In code: protocols assuming a peer answers within a bounded time or
    shares the server's elapsed time. Sessions, leases, and tokens judged
    by client elapsed time. Clients resuming after long freezes and acting
    on stale state. Sync protocols assuming short offline periods.
  - Fix: treat every client time as untrusted input: validate
    plausibility, record it beside the server receive time, and never let
    it alone decide authorization, ordering, expiry, or billing. Decide
    expiry, leases, and deadlines on the server clock. Revalidate tokens,
    versions, and deadlines on reconnect. Merge long-absent peers with
    version vectors or logical clocks (C19). Make operations idempotent
    and resumable, and use delay-tolerant protocols where latency is
    unbounded. Detect illogical client time (backward steps, impossible
    order, out-of-range values, sudden rate changes) and apply a stated
    policy: accept and flag, correct from server time, or reject with an
    actionable message, never crash or corrupt data. Test clients whose
    clocks freeze, race, crawl, jump backward, jump years, and change zone
    mid-session.
  - Not a finding: server-authoritative designs that validate client
    times and revalidate on reconnect, even without space-specific
    handling.
  - Escalate: products without a stated policy for illogical client time.
- Proposed severity (for the user to decide), per check: CRITICAL when a
  client-controlled or illogical clock decides authorization, payment, or
  token validity, or a clock jump can trigger mass deletion, mass expiry,
  or an authorization bypass. HIGH for refresh loops, TOTP lockouts,
  lockouts with no recovery, last-write-wins data loss, deadline or lock
  safety on a one-time or fixed offset, sync cursors, catch-up billing,
  far-off timestamps corrupting core data, and crashes on illogical
  time. MEDIUM for countdowns, caches, scheduling, labels, filters, sync
  conflicts, logs, and analytics. LOW for test-only code.

Point ledger for C15:
- Inbound from C7.5: cross-system durations measured on one
  authoritative clock -> C15.4.
- Inbound from C14.2: client clock error and wrong zone setting -> C15.5.
- PA-11: drift, sync, virtualization, hardware, users, dual boot, steps,
  client trust, token leeway, licensing, cross-machine comparison,
  sanity bounds, what to check (client decisions, leeway, sync config),
  server-timestamp fix, leeway fix, sync and bounds fix, not-a-findings,
  escalation -> C15.1. Wall-clock durations and monotonic fix -> C18
  (inbound). ID generators and backward-jump fix -> C19 (inbound). Smear
  versus step -> C16 and C17 by reference. Severity -> C15 severity.
- PA-12: boot defaults, bad RTC, GPS rollover, VM restore, manual and
  test dates, ntpd and chrony behavior, retention, expiry sweeps, TLS,
  wrongly signed tokens, floor and ceiling fix, destructive-action fix,
  sync-step fix, NTS, not-a-findings, escalation -> C15.2. Catch-up
  schedulers and bounded catch-up -> C15.2 with C18. Sync cursors and
  far-future IDs -> C15.2 with C19. Severity -> C15 severity.
- PA-13: drift variability, sync effects, suspend jumps, smearing,
  per-machine drift, network delay, one-time offset, countdowns,
  round-trip estimation, log correction, fixed-skew leases, refresh fix,
  server-enforcement fix, bounded-drift fix, segment correction,
  not-a-finding, escalation -> C15.3. Hardcoded TAI-UTC and GPS-UTC
  offsets, leap-second-table fix, TAI-GPS not-a-finding -> C17 (inbound).
  Monotonic-clock fix for leases -> C18. Severity -> C15 severity.
- PA-14: independent clocks, manual setting, zone difference, all code
  patterns, checks, relative-duration fix, server-authority fix, `Date`
  header fix, skew windows, label clamp, not-a-findings, offline-first
  escalation -> C15.4. Last-write-wins ordering detail -> C19 by
  reference. Severity -> C15 severity.
- PA-15: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C15.5. Severity -> C15 severity.
- PA-16: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C15.3. Severity -> C15 severity.
- PA-103: illogical-time catalog, black-hole and Mars figures,
  delay-tolerant networking, everyday equivalents, code patterns,
  checks, server-authority fix, reconnect fix, idempotency, untrusted
  input fix, detection policy, simulated-client tests, not-a-finding,
  escalation -> C15.6. Version vectors -> C15.6 with C19. Relativistic
  corrections -> C16 (inbound reference). Severity -> C15 severity.
