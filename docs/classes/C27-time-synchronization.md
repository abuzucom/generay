# C27 Time synchronization

(sources: PA-137 to PA-155; moved in from C15.1, C15.2, C15.3, C16.1,
C16.5, C17.2) Approved by the user. (2026-10-04; stays open for new sync
checks, each approved individually)

User decision (2026-10-04): time synchronization is its own class
(module), because more content is coming. Guiding best practice: BP-2
(never depend on a single time source; diversify across reliable sources
within reason), which C27.7, C27.10, C27.12, C27.15, C27.16, C27.17,
C27.19, and C27.22 apply. BP-3 (RTC-only as a designed last resort)
is applied by C27.24. BP-4 (Roughtime) is applied by C27.11. Scope: how hosts, devices,
containers, and applications obtain and keep correct time, and how code
should treat sync state. Clock error and its effects stay in C15. Clock
rates and smearing stay in C16. Stream and signal synchronization stays
in C16.5 unless the user moves it.

- C27.1 Time sync is best effort, not a guarantee.
  - Facts: sync may not run (this container has no daemon, and the kernel
    reports `STA_UNSYNC` with a 16 s maximum error, verified), may be
    unreachable (offline, air-gapped, UDP 123 blocked, captive portals,
    TLS broken by the wrong clock), completes only after boot or resume,
    may refuse or crawl on large offsets (C15.2), may follow wrong,
    spoofed, or mixed-smear sources, is unauthenticated unless NTS (RFC
    8915) is used, carries an error bound from asymmetric paths, rolls
    over in 2036 (C22.1), and yields UTC only, so the local date also
    needs the right zone and tz data (C9, C10). Containers inherit the
    host clock and cannot set it.
  - In code and operations: "the host runs NTP" treated as proof of
    correct time, with no sync-status check. Security or expiry decisions
    on devices that may never sync. Hand-rolled SNTP queries trusting one
    unauthenticated reply. Containers given `CAP_SYS_TIME` or a sync
    daemon. One-server configs, no `makestep` or `-g`, no NTS where
    spoofing matters. No offset monitoring (C26.3).
  - Fix: check sync state and estimated error where correctness depends
    on time (`adjtimex` status, `timedatectl show` `NTPSynchronized`,
    `chronyc tracking`) and apply plausibility bounds (C15.2). Use several
    sources, step at startup, and NTS where needed. Keep authoritative
    time on monitored servers. Use the platform sync service, not
    hand-rolled queries (new client libraries need approval). Leave clock
    setting to the host.
  - Not a finding: display-only device time. Systems that check and act
    on sync status with monitored sync.
  - Escalate: security, billing, or regulated timing on hosts or devices
    whose sync arrangement cannot be established.
  - Proposed method tag: `both` (scan: raw UDP 123 or NTP client imports,
    `CAP_SYS_TIME` in container specs, sync configs without `makestep`
    or NTS; model: whether time-dependent decisions check sync).
- C27.2 Large offsets, startup stepping, and authenticated time.
  - Facts: ntpd exits when the offset exceeds its 1,000 s panic threshold
    unless started with `-g`. chrony slews by default (about 83 ms per
    second) unless `makestep` is set, so a large offset takes a long time
    to remove. Plain NTP is unauthenticated; NTS (RFC 8915) adds
    authentication.
  - In code and configuration: sync started without `-g` or `makestep` on
    hosts that can boot far off (C15.2). No NTS where spoofing matters.
  - Fix: step large offsets at startup (`ntpd -g`, chrony `makestep`),
    then slew. Use NTS where the threat model needs authentication.
  - Proposed method tag: `heuristic` (config scan for ntpd flags, chrony
    `makestep`, and `nts`).
- C27.3 Fleet sync sources and coverage.
  - Facts: a server fleet is many clocks (C15.3), and each needs working,
    monitored sync. One upstream server is a single point of failure and
    cannot be outvoted when wrong.
  - In code and configuration: hosts or regions without sync, one-server
    configurations, fleets syncing from different upstreams with
    different policies, no offset or sync-state monitoring (C26.3).
  - Fix: run sync on every host with several sources, keep fleet policy
    uniform, and monitor offset and sync state with alerts.
  - Escalate: fleets whose sync arrangement is outside the review unit
    while correctness depends on cross-host time.
  - Proposed method tag: `both`.
- C27.4 Slewing, smearing, and precision sources.
  - Facts: sync corrects by slewing: ntpd up to 500 ppm, chrony's default
    maximum about 83,000 ppm (8.3%), so a minute can last about 55 to 65
    real seconds. Leap smearing (Google: 24 hours, noon to noon UTC; AWS
    similar) stretches each second, and mixed smeared and unsmeared
    sources disagree by fractions of a second during the smear. Providers
    smear or step differently (C15.1, C17.2).
  - In code and configuration: fleets syncing from mixed smeared and
    unsmeared sources. Precision domains (trading, metering, measurement)
    on ordinary NTP without a stated accuracy budget.
  - Fix: use one smear or step policy across every host that compares
    time. For high-precision domains, use a dedicated source (PTP, GPS-
    disciplined clocks) and a stated accuracy budget (C17.3 for regulated
    accuracy).
  - Not a finding: UI and coarse timing where small rate errors are
    acceptable.
  - Escalate: precision or regulated timing without a stated source and
    accuracy.
  - Proposed method tag: `both`.
- C27.5 Reference loss, holdover, and resynchronization.
  - Facts: references are lost (GPS, PTP grandmaster, NTP servers),
    clocks enter holdover and drift at their oscillator's rate, and
    reacquisition or failover to another reference can step the clock.
    Media and measurement systems depend on the shared reference (C16.5).
  - In code and configuration: no detection of loss of lock, no defined
    behavior on lost reference, no holdover budget, no resync after
    resume, reconnect, or failover.
  - Fix: detect loss of lock and mark affected data's sync state (C16.3).
    Specify a holdover budget, resynchronize after resume, reconnect, and
    failover, and monitor time in holdover (C26.3).
  - Escalate: systems without a stated holdover requirement or
    synchronization tolerance.
  - Proposed method tag: `llm` (depends on system design; a scan can
    flag PTP or GPS configuration only as context).
- C27.6 Sync differs by platform and environment.
  - Facts: Windows uses W32Time (domain hierarchy to the PDC emulator, or
    NTP to `time.windows.com`), historically tuned for Kerberos tolerance
    of 5 minutes, with correction limits and polling in version- and
    role-dependent registry settings. macOS uses `timed` (since 10.14).
    Linux uses systemd-timesyncd, chrony, ntpd or NTPsec, or OpenNTPD, with
    different step and slew rules (ntpd steps above 128 ms). Mobile
    devices mix carrier NITZ and NTP, and users can disable automatic
    time. Embedded devices run firmware SNTP or nothing. Hypervisors and
    clouds add layers (Hyper-V, VMware Tools, `kvm-clock`, AWS, Google,
    and Azure time services, several smearing); this guest uses `tsc`
    with `kvm-clock` available and no PTP device (verified). Containers
    share the node clock. Sync state is read differently per platform
    (`adjtimex`, `timedatectl`, `chronyc`, `ntpq`, `w32tm /query
    /status`), not at all in browsers, and not by language clock APIs.
    Setting time needs privileges apps and containers lack.
  - In code and operations: one platform's sync check or tool (`w32tm`,
    `sntp`, `ntpdate`, `timedatectl`, `hwclock`) used everywhere. One
    platform's accuracy assumed for all. Apps trying to set the clock.
    Clients assumed synced because servers are.
  - Fix: document per supported platform the sync mechanism, expected
    accuracy, and how sync state is read (or that it cannot be). Put sync
    checks behind one interface with an explicit "unknown" result. Treat
    device time as untrusted where sync state is unknown (C15.4, C15.6).
    Never set the clock from application code.
  - Not a finding: single-platform tools that document their platform.
    Server-authoritative designs.
  - Escalate: multi-platform products without stated accuracy
    requirements and per-platform sync assumptions.
  - Proposed method tag: `both` (scan: platform-specific sync commands and
    APIs, `CAP_SYS_TIME`, clock-setting calls such as `settimeofday`,
    `clock_settime`, `SetSystemTime`; model: whether other platforms are
    handled and what accuracy is assumed).
- C27.7 Public pools are not authoritative time sources.
  - User priority (2026-10-04): the user rates PA-139 as possibly one of
    the most important items in the repository, and chose:
    - Prominence: the entry sits near the top of the 32 KiB main document
      with a fuller text that condensing never trims.
    - Raised severity (user decision; overrides the C27 proposal for this
      check): CRITICAL when authoritative, regulated, or security-relevant
      time (audit trails, trading, legal records, token issuers, CAs, time
      services for other systems) relies on public pool sources, a single
      source, or unauthenticated sources with no stated accuracy or
      traceability. HIGH for hardcoded NTP server IPs in code, firmware,
      or images. MEDIUM for shipping the generic pool instead of a
      registered vendor zone, and for undocumented sources on ordinary
      systems. LOW for test-only code.
    - Dedicated eval cases (to build with the eval corpus):
      - Positive: a token issuer or audit service whose chrony or ntpd
        config uses only `pool.ntp.org`; a trading timestamp service with
        one unauthenticated server and no accuracy statement; firmware or
        a Dockerfile hardcoding an NTP IP; a product image using the
        generic pool instead of a vendor zone; an app that queries one
        pool server directly and trusts it.
      - Negative: an ordinary web server on distribution defaults issuing
        no authoritative timestamps; a timestamp issuer using several
        known-operator sources with NTS, a stated accuracy, and
        monitoring; a registered vendor zone in a consumer device.
    - Not chosen: a euler-style Blocking or Escalate tier.
  - Facts: the NTP Pool is volunteer-run; DNS returns rotating servers of
    unknown operators. Monitoring drops bad servers only after detection.
    Members are often stratum 2 or lower and may sync from other members,
    so errors propagate with no traceability. There is no default
    authentication, no service level, and no traceability to a national
    laboratory's UTC(k), which regulated timestamps can require (EU
    MiFID II RTS 25). Reputable sources can be wrong too (US Naval
    Observatory servers served time about 12 years in the past in
    November 2012, reported). Hardcoded server IPs have flooded operators
    (Netgear and the University of Wisconsin, 2003). Here, `pool.ntp.org`
    resolved to four addresses and none answered on UDP 123 (verified).
  - In code and operations: authoritative timestamp issuers (audit,
    trading, legal records, token issuers, CAs, time services for others)
    syncing only from the pool or a distribution default. Hardcoded NTP
    IP addresses. Products shipping the generic pool instead of a
    registered vendor zone. Single direct pool queries trusted (C27.1).
    "Accurate" or "traceable" claims without a stated source.
  - Fix: for authoritative, regulated, or security-relevant time, use
    sources with known operators and stated accuracy (cloud time services
    with documented behavior, national laboratory services, NTS servers
    from known operators, local GPS- or PTP-disciplined servers), and
    document traceability where required. Use several independent
    sources with one leap policy (C27.4). Ship a vendor zone, never
    hardcoded IPs. Monitor against more than one reference (C26.3).
  - Not a finding: ordinary clients and servers on pool or distribution
    defaults that issue no authoritative or regulated timestamps.
  - Escalate: systems issuing authoritative, legal, or regulated
    timestamps without a stated source, accuracy, and traceability.
  - Proposed method tag: `both` (scan: `pool.ntp.org` and `server` or
    `pool` lines, hardcoded NTP IPs, Windows `NtpServer` values; model:
    whether the component issues authoritative time).
- C27.8 An NTP reply is a measurement with an error bound.
  - Facts (RFC 5905, RFC 4330): replies report stratum, leap indicator,
    root delay, root dispersion, and reference timestamp; error is
    bounded by the root distance plus the client's path error (up to half
    the round trip, C15.3). Leap indicator 3 and stratum 16 mean
    unsynchronized; stratum 0 replies are Kiss-o'-Death codes (`RATE`,
    `DENY`), not time. Servers can serve a free-running local clock
    (ntpd `127.127.1.0` with fudged stratum, chrony `local`, orphan mode,
    Windows domain controllers announcing reliable time with no upstream)
    and keep answering confidently. Reference timestamps can be stale.
    Upstream failures propagate (GPS rollover, C15.2; leap mishandling).
    Precise is not correct (bias, smearing, C27.4). Unauthenticated
    replies can be forged, and skipping the origin-timestamp check lets
    off-path forgeries through (C27.1).
  - In code and operations: custom SNTP clients reading only the
    transmit timestamp and ignoring quality fields and Kiss-o'-Death; no
    round-trip compensation; no origin check; first reply from one server
    accepted. Servers serving an undisciplined local clock. Accuracy
    claims without a measured bound.
  - Fix: use the platform sync service or a validating client (new
    libraries need approval). Custom clients must reject leap indicator 3,
    stratum 0 or 16, stale references, and origin mismatches, honor
    Kiss-o'-Death, compensate round trip, and keep the error bound. Query
    several servers and discard outliers (C27.7). Serve time only from
    disciplined servers and alarm on local-clock fallback. State accuracy
    as a measured bound.
  - Not a finding: platform sync services with validated configuration
    where only ordinary accuracy is needed.
  - Escalate: stated accuracy requirements without a measured, reported
    error bound.
  - Proposed method tag: `both` (scan: 48-byte NTP packet handling such as
    `struct.unpack` on NTP replies, NTP client imports, `127.127.1.0`,
    chrony `local`, W32Time `AnnounceFlags`; model: whether reply fields
    are validated and the error bound is kept).
  - Eval cases (per the user's C27 eval decision): positive: an SNTP
    client trusting the transmit timestamp of one reply; a chrony server
    with `local stratum 10` serving a fleet with no upstream; a service
    claiming millisecond accuracy from public NTP. Negative: a client
    rejecting LI 3, stratum 0 and 16, and origin mismatches across
    several servers; a fleet on the platform daemon with monitoring.
- C27.9 Government and national servers: stratum is not authority.
  - Facts (RFC 5905, published service documentation): no NTP server
    serves stratum 0, which names the reference clock itself; stratum 0
    in a packet is "unspecified" (Kiss-o'-Death, C27.8), so stratum 1 is
    the best a client can get. National laboratories maintaining UTC(k)
    (NIST, PTB, NPL, NRC, others) run stratum 1 services; other agencies
    run ordinary lower-stratum servers, many countries have no public
    service, and military services have served bad time (C27.7).
    Names such as `time.nist.gov` rotate over servers at several sites
    (resolution verified here; UDP 123 blocked). NIST asks clients not to
    query a server more than about once every 4 seconds, may refuse or
    rate-limit those that do, and offers authentication only by
    registration. Outages happen. Some servers are restricted or
    unreachable. Stratum is a hop count, not accuracy: a distant stratum 1
    over an asymmetric path can be worse than a nearby stratum 2 (C15.3),
    and a stratum 1 with a failed reference can keep announcing stratum 1.
    Traceability needs a documented uncertainty chain from UTC(k) to the
    local clock.
  - In code and operations: "stratum 0" or "stratum 1 from NIST, so
    authoritative" claims without a measured bound. Low stratum treated as
    proof of accuracy, or stratum 0 replies accepted as time. A single
    government server as the only source, often hardcoded by IP (C27.7).
    Polling faster than service rules, ignoring rate-limit replies.
  - Fix: treat stratum as context, and measure and report the error bound
    (C27.8). Use several independent sources, with a national laboratory
    as one. Use the lab's authenticated service, or NTS from a known
    operator, where authentication matters. Document the uncertainty
    chain for traceable time, or use local GPS- or PTP-disciplined
    references (C27.7). Follow polling rules and honor rate limits.
  - Not a finding: national laboratory servers used as one of several
    monitored, politely polled sources without unsupported claims.
  - Escalate: regulated or legal timestamping claiming traceability via a
    government server without a documented uncertainty chain.
  - Proposed method tag: `both` (scan: `stratum 0` text, stratum
    comparisons in NTP code, government server names and IPs in configs,
    poll intervals below service limits; model: whether stratum is used as
    proof and whether traceability is claimed).
  - Eval cases: positive: a trading service configured with only
    `time.nist.gov`, documenting "stratum 1, therefore traceable"; client
    code accepting any reply with stratum <= 1; a cron job querying a
    national server every second. Negative: a fleet using two national
    labs plus NTS from known operators with monitoring and a measured
    bound.
- C27.10 Nearest and lowest latency is not best.
  - Facts: offset error from the path is bounded by half the round trip,
    but the server's own error (root distance, C27.8) adds to it, so a
    close server can be unsynced, free-running, or poorly fed. Nearest
    sources are often not independent (same operator, upstream, network),
    and NTP can outvote a falseticker only among enough independent
    sources (NTP guidance: at least four). The fastest responder can be an
    attacker: a rogue LAN server, a DHCP-supplied server (option 42,
    accepted by many clients by default), or an on-path replier.
    Geographic and network distance differ; anycast moves with routing.
    Latency changes with load, routing, and roaming, so one-time choices
    go stale. Everyone on one nearest server concentrates load (C27.7).
    Daemons already weigh delay, dispersion, and agreement continuously.
  - In code and operations: "ping and pin the lowest" scripts. Only one or
    two nearby sources from one operator. DHCP NTP accepted on untrusted
    networks by authoritative-time hosts. Server choice by client
    geolocation.
  - Fix: configure several diverse, independent sources (at least four
    where a bad one must be outvoted) and let the daemon select
    continuously. Judge sources by error bound and monitored agreement,
    not latency (C27.8). Refuse network-supplied NTP on untrusted networks
    for hosts needing correct or authoritative time, and authenticate
    where it matters (C27.2). Nearby disciplined servers are good when
    monitored and backed by independent sources (C27.7).
  - Not a finding: daemon-managed selection among several independent
    sources, nearby ones included.
  - Escalate: authoritative-time hosts whose source selection and
    independence cannot be established.
  - Proposed method tag: `both` (scan: latency-probing selection code,
    single-server or single-operator configs, DHCP NTP acceptance such as
    dhclient `ntp-servers` requests or systemd-networkd `UseNTP=`; model:
    whether the host needs authoritative time and sources are
    independent).
  - Eval cases: positive: a script that pings five servers and writes the
    fastest into `chrony.conf` as the only source; an audit host accepting
    DHCP NTP on a guest network; a config with two servers from one
    operator for a token issuer. Negative: a host with four independent
    sources including a nearby GPS-backed server, under daemon selection
    and monitoring.
- C27.11 Servers and attackers can shift time on purpose.
  - Facts: leap-smearing services serve time differing from UTC by up to
    about half a second, announced (C27.4). Anyone can run a server,
    including in the volunteer pool, and a malicious one can answer
    monitors correctly while lying to chosen clients (C27.7). On-path
    tools ("Delorean", Black Hat Europe 2014) and off-path attacks with
    spoofed Kiss-o'-Death and fragmentation (Malhotra and others, NDSS
    2016) shift unauthenticated clients (C27.1). Fake time servers leak
    into production (C25.2). Malware and insiders repoint NTP settings.
    Shifted time revives expired or revoked certificates, replays expired
    tokens, expires HSTS, breaks Kerberos and DNSSEC, empties or freezes
    caches, fires time bombs (C26.2), and corrupts logs and audit order
    (C8.1, C19.6). Not verified here (UDP 123 blocked).
  - In code and operations: certificate, token, replay, or license
    decisions trusting the local clock with no defense against a shift
    (C15.1). Unauthenticated NTP on hosts issuing or validating tokens or
    certificates. Configs accepting any jump after startup. NTP settings
    writable by unprivileged users or apps. Fake time servers reachable
    from production.
  - Fix: authenticate time on security-relevant hosts (NTS), remembering
    authentication proves the sender, not its honesty (C27.2). Use
    several independent sources (C27.10). Step only at startup and limit
    or alarm on later large corrections (chrony `maxchange`, ntpd panic
    threshold). Apply plausibility bounds to "now" (C15.2). Use
    Roughtime (BP-4) where NTP is unreachable or unreliable, to bootstrap
    devices whose wrong clock breaks TLS, or as a signed cross-check for
    security decisions: it signs every reply with a public key and lets
    chained queries prove a server lied. Use it correctly: pinned keys
    from an updatable list, several independent servers (half a dozen or
    more to establish correct time), results kept as intervals, never
    for accuracy finer than about 10 s, and the client kept current with
    the protocol (adding a client needs approval). Restrict and alarm on time configuration changes.
    Keep fake time servers out of production.
  - Roughtime findings (BP-4): security decisions on devices that cannot
    reach authenticated time and have no Roughtime or equivalent
    fallback; Roughtime with one server, unpinned or hardcoded
    unupdatable keys, results used as exact, or used as a precision
    source.
  - Not a finding: announced smearing used consistently across a fleet.
    Hosts with authenticated, diverse sources, correction limits, and
    monitoring.
  - Escalate: security-relevant hosts whose time protection cannot be
    established.
  - Proposed method tag: `both` (scan: absent `nts` on token, CA, or auth
    hosts' configs, no `maxchange` or unlimited `makestep`, world-writable
    NTP config, fake time server names or `libfaketime` in production
    images; model: which security decisions depend on time and how it is
    protected).
  - Eval cases: positive: a token issuer with one unauthenticated NTP
    server and `makestep 1 -1`; a license check trusting local time on a
    host whose NTP config is user-writable; a staging fake time server
    referenced from a production config. Negative: an auth host with NTS
    from three independent operators, `makestep` only at startup,
    `maxchange` set, and change alarms.
- C27.12 One government or operator is a single point of failure.
  - Facts: governments have degraded timing signals on purpose (US GPS
    Selective Availability, ended 2000-05-02). Funding and policy change
    services (a 2018 US budget proposal to defund NIST's WWV, WWVH, and
    WWVB stations, reported; NIST's website offline in the October 2013
    shutdown while time services ran, reported). State-attributed GNSS
    jamming and spoofing has been widely reported near conflict zones
    (Baltic, Eastern Mediterranean). Sovereign systems fail without
    intent (Galileo outage of about a week, July 2019). Access is blocked
    by network policy (UDP 123 blocked here, verified), national
    firewalls, sanctions, or export controls. Any operator can be
    compromised, compelled, misconfigured, or overloaded (C27.7, C27.11).
    The audit takes no political position; every operator is a
    dependency.
  - In code and operations: all sources from one operator or government
    domain (only `*.nist.gov`), single-constellation GNSS receivers,
    critical infrastructure with no holdover plan (C27.5), international
    products hardcoding one country's service, risk registers calling a
    government service "guaranteed".
  - Fix: diversify sources across operators and jurisdictions, and GNSS
    constellations where hardware allows (C27.10). Keep local holdover
    with a stated budget (C27.5) and detect sudden shifts (C27.11). Choose
    regional services per deployment region. Record time-source
    dependencies and failure modes without labeling any as guaranteed.
  - Not a finding: a national laboratory service as one of several
    independent, monitored sources (C27.9).
  - Escalate: critical infrastructure or regulated systems without stated
    source diversity, holdover, and loss-of-reference plans.
  - Proposed method tag: `both` (scan: all configured sources sharing one
    domain or operator, single-constellation GNSS settings, one country's
    service hardcoded; model: criticality, holdover, and deployment
    regions).
  - Eval cases: positive: a trading platform whose chrony config lists only
    NIST servers; a telecom timing design on GPS only with no holdover;
    an internationally sold device hardcoding one national service.
    Negative: sources from three operators in two jurisdictions plus a
    multi-constellation GNSS receiver with a stated holdover budget.
- C27.13 Sync must work over IPv6 and needed ports, not just IPv4.
  - Facts: IPv6-only mobile networks (NAT64 with DNS64 or 464XLAT) and
    IPv6-only cloud subnets exist, and IPv4 literals cannot be reached
    there without device-side translation. `pool.ntp.org` returned only
    IPv4 addresses, while `2.pool.ntp.org`, `time.google.com`,
    `time.cloudflare.com`, `time.nist.gov`, and `time.aws.com` returned
    both (verified 2026-10-04). Cloud link-local endpoints differ by
    family (AWS 169.254.169.123 for IPv4, a separate IPv6 address on
    Nitro). Broken IPv6 paths time out clients without fallback.
    Carrier-grade NAT puts many clients behind one IPv4 address, so
    per-address rate limits hit innocent clients (C27.8). NTS key
    exchange uses TCP 4460 (RFC 8915), and PTP uses other ports or
    Ethernet. ntpd needs separate `restrict -6` rules, and firewalls can
    differ by family.
  - In code and operations: custom clients hardcoding `AF_INET` or
    resolving only A records; validators accepting only dotted quads;
    hardcoded IPv4 time or link-local addresses (C27.7); `ntpd -4` or
    `chronyd -4` on hosts that may be IPv6-only; firewall rules for UDP
    123 on IPv4 only, or no TCP 4460 where NTS is used; IPv4-only
    `restrict` rules.
  - Fix: use hostnames and dual-stack sources (IPv6-capable pool zones
    such as `2.pool.ntp.org`, or vendor zones). Support both families
    with fallback in custom clients. Use the cloud endpoint documented for
    each family. Write firewall and ACL rules for both families and open
    TCP 4460 for NTS. Test on IPv4-only, IPv6-only, and dual-stack
    networks.
  - Not a finding: deployments documented and enforced as IPv4-only,
    using hostnames.
  - Escalate: products on customer or mobile networks without stated
    address-family support.
  - Proposed method tag: `heuristic` (scan: `AF_INET` in NTP code, A-only
    resolution, IPv4-only validators, literal IPv4 time addresses,
    `-4` daemon flags, IPv4-only `restrict` lines, firewall rules for UDP
    123 without IPv6 or without TCP 4460 next to NTS configs).
  - Eval cases: positive: a mobile app's SNTP client using `AF_INET` and a
    literal IPv4 server; an IPv6-only Kubernetes node pool configured with
    `pool.ntp.org`; an ntpd server with `restrict default ignore` but no
    `restrict -6` rule; NTS enabled with only UDP 123 allowed. Negative: a
    dual-stack fleet using hostnames with A and AAAA records, family-wide
    ACLs, and TCP 4460 open for NTS.
- C27.14 Servers stay silent, refuse, and rate-limit.
  - Facts: servers send Kiss-o'-Death (`RATE` to slow down, `DENY` or
    `RSTR` to stop), drop queries through access rules (ntpd `restrict`
    with `ignore`, `limited`, `kod`), and enforce service polling rules
    (C27.9). Networks block UDP 123 (no reply from this host, verified),
    and some providers filter or limit NTP since the 2013-2014 `monlist`
    amplification attacks (CVE-2013-5211). Shared IPv4 addresses trip
    limits meant for others (C27.13). Servers go down, overload, or leave
    the pool (C27.7). Client fleets cause overload with fast default
    polling or synchronized schedules. NTP's normal minimum poll interval
    is 64 seconds (ntpd `minpoll 6`).
  - In code and operations: blocking queries without timeouts at boot or
    in request paths; tight retries without backoff; Kiss-o'-Death ignored
    or parsed as time (C27.8); failed queries turned into a time value
    (offset 0, local clock, or epoch); polling every few seconds or fleets
    polling in lockstep; no failover and no defined no-time behavior
    (C27.1).
  - Fix: use the platform daemon (BP-1). In custom clients, set timeouts,
    back off exponentially with jitter, honor `RATE`, drop servers on
    `DENY` or `RSTR`, and fail over. Never turn a failed query into a time
    value; report "no time" and apply the stated policy (C27.1). Keep
    polling within normal intervals and service rules, spread fleet
    schedules with jitter, and monitor failures and Kiss-o'-Death counts
    (C26.3).
  - Not a finding: platform daemons with several sources and default
    polling.
  - Escalate: devices or fleets without stated behavior when no time
    source answers.
  - Proposed method tag: `both` (scan: socket calls without timeouts in
    time code, retry loops without sleep or backoff, poll intervals under
    64 s, fleet-wide cron schedules on fixed seconds for time sync, no
    handling of stratum-0 replies; model: what happens with no reply).
  - Eval cases: positive: a boot script calling a time query with no
    timeout before starting services; firmware retrying every second on
    failure; a client returning `0` offset when the query fails; IoT
    devices syncing at 00:00:00 every day with no jitter. Negative: a
    client with a 2 s timeout, exponential backoff with jitter,
    Kiss-o'-Death handling, failover across four servers, and a "no time"
    state.
- C27.15 One or two sources cannot vote.
  - Facts: one source cannot be checked; two that disagree cannot say
    which is right; three can outvote one bad source only while all
    answer; NTP guidance recommends at least four so one can fail and one
    can be wrong while a majority agrees. NTP's selection finds a majority
    of agreeing sources (intersection of confidence intervals). Daemons
    sync to one source by default (chrony `minsources` and ntpd
    `tos minsane` default to 1); chrony `pool` takes up to four sources
    (`maxsources 4`), a `server` line one. Configured count is not live
    count (C27.14). Count without independence is not diversity (C27.10,
    C27.12). Averaging moves halfway toward a bad source instead of
    rejecting it.
  - In code and operations: one or two `server` lines on hosts needing
    correct or authoritative time; `minsources 1` or `tos minsane 1` there;
    custom clients taking the first reply or averaging two; no monitoring
    of reachable and selected source counts.
  - Fix: configure at least four independent sources where a wrong one
    must be outvoted, more where some may be unreachable. On
    authoritative hosts require a minimum of agreeing sources before
    adjusting the clock (`minsources`, `tos minsane`) and alarm when
    unmet. Combine by agreement (intersection, or median with outlier
    rejection), or use the daemon (BP-1). Monitor source counts (C26.3).
  - Not a finding: ordinary clients syncing to a local, monitored server
    that itself uses several independent sources.
  - Escalate: authoritative-time hosts whose live source count and
    independence cannot be established.
  - Proposed method tag: `both` (scan: count of `server` and `pool` lines,
    `minsources` and `tos minsane` values, custom clients averaging or
    returning the first reply; model: whether the host needs authoritative
    time and whether sources are independent).
  - Eval cases: positive: a CA host with two `server` lines and default
    `minsources`; a client averaging replies from two servers; a token
    service with four servers configured but monitoring showing one
    reachable for days. Negative: an authoritative host with five
    independent sources, `minsources 3`, and alarms on source count.
- C27.16 NTP does not replace the RTC, GNSS, or other sources.
  - Facts: the RTC carries time across power loss and boot, and stays
    correct only if updated from synced time (Linux "11-minute mode" while
    synchronized, chrony `rtcsync`, or `hwclock --systohc`); this
    container has no RTC device and the kernel reports unsynchronized, so
    that mode is off here (verified). RTC and build time give a floor for
    rejecting suspicious NTP results (C15.2, C27.11). GNSS and PPS give
    microseconds locally against milliseconds over the internet, with GPS
    time 18 s ahead of UTC (C17.5). Independent sources cross-check each
    other (NTP exposes GNSS spoofing, GNSS exposes shifted NTP). Remaining
    sources provide holdover when NTP is lost (C27.5). PTP, hypervisor
    time (C27.6), cellular NITZ, and radio time (WWVB, DCF77, MSF) exist.
    Two mechanisms disciplining one clock fight (hypervisor periodic sync
    plus an NTP daemon, or two daemons). NTP disciplines the wall clock;
    elapsed time still comes from monotonic clocks (C18.1).
  - In code and operations: no RTC update (`rtcsync`, `hwclock`), so
    reboots start stale; GNSS or PPS hardware unused, or used without UTC
    conversion; hypervisor periodic sync and NTP both active, or two
    daemons; no cross-check on authoritative hosts; no fallback when NTP
    is lost (C27.1, C27.14).
  - Fix: keep the RTC updated and use it with build time as a floor. Use
    local GNSS, PPS, or PTP references where accuracy needs them, with
    correct conversion, alongside independent network sources (C27.7).
    Let exactly one mechanism discipline each clock and feed or check it
    from the others. Define holdover and fallback order (C27.5).
  - Not a finding: one discipline using several references with RTC
    updates enabled. Containers relying on the host clock by design
    (C27.1).
  - Escalate: authoritative or measurement systems with local references
    available but no stated source hierarchy and holdover plan.
  - Proposed method tag: `both` (scan: chrony or ntpd configs without
    `rtcsync`, `hwclock` usage, refclock and PPS lines, VMware Tools
    `time.synchronize` settings or Hyper-V time sync alongside an NTP
    daemon, two sync daemons enabled; model: source hierarchy and
    holdover).
  - Eval cases: positive: an embedded device with chrony and no `rtcsync`
    that issues timestamps right after boot; a VMware VM with Tools
    periodic sync and chronyd both enabled; a trading host with a GPS PPS
    card not configured as a reference. Negative: chrony with `rtcsync`,
    a PPS refclock plus three network sources, hypervisor periodic sync
    disabled, and a stated holdover budget.
- C27.17 Time distribution needs a hierarchy, not every node on its own.
  - Facts: systems need consistent time between nodes, often more than
    absolute accuracy, and nodes syncing independently to different
    sources, paths, and smear policies disagree more than nodes sharing an
    internal hierarchy (C15.3, C27.4). Designed hierarchies exist (Windows
    domain members to domain controllers and the PDC emulator, C27.6;
    internal stratum tiers; cloud in-region time services; PTP from a
    grandmaster). Every node going to the internet multiplies public load
    (C27.14), needs outbound UDP 123 everywhere, and widens the attack
    surface (C27.11). Many nodes cannot sync at all (browsers, sandboxed
    apps, containers, offline devices; C27.1, C27.6). Decision authority
    is a role held by designated servers; a synced client clock is still
    untrusted (C15.4, C15.6, C19.6). One internal server without
    redundancy is the opposite failure (C27.15).
  - In code and operations: every host image pointing at public servers
    with no internal tier in large fleets; outbound UDP 123 from every
    host; client device time used for system decisions because "it syncs
    NTP"; mixed smeared and unsmeared sources in one system; a single
    unmonitored internal time server.
  - Fix: design a redundant internal tier (or the cloud in-region service)
    synced to several independent upstreams (C27.7, C27.15), with other
    nodes syncing to it. Use one leap policy (C27.4). Keep decision
    authority on designated servers and treat client time as untrusted.
    Restrict outbound time traffic to the tier, and monitor the tier and
    node offsets against it (C26.3).
  - Not a finding: small systems or standalone devices that do not depend
    on cross-node agreement. Offline-capable edge devices that defer to
    server time when connected.
  - Escalate: distributed systems without a stated time distribution
    design and cross-node skew requirement.
  - Proposed method tag: `both` (scan: infrastructure-as-code or images
    where many host configs list public servers and no internal tier,
    egress rules allowing UDP 123 broadly, mixed smear sources across
    configs; model: the system's design and which node is authoritative).
  - Eval cases: positive: a 500-node Terraform fleet whose base image uses
    `pool.ntp.org` and allows UDP 123 egress everywhere; a mobile app
    sending device time as the authoritative order timestamp; one
    internal time server with no peers. Negative: three internal servers
    on independent upstreams, all nodes syncing to them, egress limited to
    the tier, and skew monitoring.
- C27.18 External UTC is not the right clock for every job.
  - Facts: externally meaningful records (audit, legal, billing, logs)
    need UTC traceable to external time, while internal mechanics need
    stability and consistency: monotonic clocks for durations and
    timeouts (C18.1), logical, vector, or hybrid clocks or consensus terms
    for ordering (C19.6), and media or sample clocks for media and control
    (C16.5). Steering mechanics by external time breaks them (steps fire
    or stall timers, break leases, reorder logs; NTP-slaved media clocks
    glitch). Distributed systems bound inter-node skew (CockroachDB stops
    nodes beyond a configured maximum offset, 500 ms by default; Spanner
    TrueTime exposes uncertainty). Isolated clusters can deliberately run
    on agreed internal time (orphan mode), unlike an undisciplined server
    passed off as accurate (C27.8). Requiring external time to run is an
    availability risk (C27.1, C27.12); holdover keeps service running
    (C27.5). Rejoining after a long gap may need a slow slew or a planned
    step.
  - In code and operations: timeouts, leases, rate limits, or consensus on
    the wall clock because it is "accurate"; media or control loops slaved
    to NTP; services that halt without external time and have no holdover
    mode; clusters that step at any moment with no skew bound; one clock
    serving records and mechanics with no stated mapping.
  - Fix: classify each time use and pick its clock (external UTC for
    records, monotonic for durations, logical or hybrid for ordering,
    media clocks for media, bounded cluster time for coordination).
    Bridge domains explicitly (record UTC plus a logical or monotonic
    value) and document the mapping. Design holdover with degrading
    accuracy claims and planned rejoin. Bound and monitor inter-node skew,
    and fence nodes that exceed it.
  - Legacy clocks that cannot be changed (user scenario): a decades-old,
    poorly documented server that must stay up runs the wrong time and
    cannot be synced, fixed, or updated without unacceptable downtime.
    Do not correct it in place; unknown dependencies on its current time
    may break (C15.1, C19.3). Treat its time as a separate domain: measure
    its offset and drift from outside against a trusted reference, record
    measurements with dates, and convert its timestamps to UTC at the
    boundary with the correction and uncertainty recorded beside the raw
    value (C8.1, C16.3). Never sync other systems from it or let its raw
    timestamps decide ordering, expiry, billing, or audit elsewhere
    (C19.6, C27.17). Protect it from accidental correction (new NTP
    settings, hypervisor time sync, migrations) with a documented "do not
    sync" note, reason, and owner. Watch range limits and certificate
    validity, which it reaches at unexpected real dates (C22.1, C15.2).
    Put it in the risk register with a replacement or controlled
    correction plan.
    - Finding: consumers using its raw timestamps as UTC; others syncing
      from it; plans or automation that would correct it live without
      the owners' consent; no measured offset.
    - Not a finding: leaving its clock unchanged by documented decision,
      with boundary translation and monitoring in place.
    - Escalate: whether its uncorrected timestamps are acceptable for
      audit or legal records, and the correction or replacement plan.
  - Not a finding: external UTC for records with internal clocks for
    mechanics, each documented.
  - Escalate: systems without stated time domains, skew bounds, and
    behavior on loss of external time.
  - Proposed method tag: `llm` (depends on design; scan hits for wall-clock
    durations come from C18.1 and feed this check as context).
  - Eval cases: positive: a lease manager using wall-clock time "because
    it is NTP-synced" that double-grants after a step; an audio pipeline
    adjusting its sample clock to NTP; a payment service that refuses all
    requests when NTP is unreachable. Negative: a cluster using HLC with a
    500 ms offset bound and fencing, UTC stamps on records, monotonic
    timeouts, and documented holdover.
  - Legacy eval cases: positive: an ETL job loading a legacy server's
    timestamps as UTC though the server runs 7 hours 12 minutes off;
    configuration management adding an NTP server to that box in a
    routine rollout; other hosts using it as their time source.
    Negative: the box left untouched by documented decision, a gateway
    converting its timestamps with a measured, dated offset and drift
    model, and monitoring of that offset.
- C27.19 GPS is not always available or right.
  - Facts: receivers need sky view (indoors, data-center halls,
    basements, tunnels, urban canyons block it; cloud and leased hosting
    rarely allow antennas). Antennas, cables, amplifiers, and lightning
    arrestors fail. A cold receiver can take minutes to output time.
    Signals are jammed (illegal vehicle jammers, announced military tests,
    state jamming and spoofing, C27.12) and degraded by space weather.
    The system itself errs: in January 2016 a ground-segment error made
    some satellites broadcast UTC data about 13 microseconds wrong
    (reported). Receivers have mishandled week rollovers (1999, 2019; next
    2038-11-21) and leap seconds (C15.2, C17.2), and unsupported firmware
    cannot be fixed. GPS time runs 18 s ahead of UTC (C17.5).
    Distributing GPS time is another chain that can fail (C27.17). No
    GNSS hardware exists in this container to verify against.
  - In code and operations: GPS or PPS as the sole source with no network
    sources or holdover oscillator; designs assuming time at power-on
    before a fix; no monitoring of fix status, satellites, signal, or
    receiver alarms; hosts following a receiver that lost its fix;
    firmware without an update path before known rollover dates.
  - Fix: combine GPS with independent network sources and a holdover
    oscillator with a stated budget (C27.5, C27.16), with
    multi-constellation receivers where possible (C27.12). Define behavior
    before the first fix and on loss of fix (hold over, fall back, mark
    data quality). Monitor fix, satellites, signal, and jamming or
    spoofing indicators. Keep firmware supported, and test rollover and
    leap-second handling ahead of time (C25.3).
  - Not a finding: GPS as one of several monitored references with
    holdover.
  - Escalate: critical timing on GPS without a stated loss-of-signal plan
    and holdover requirement.
  - Proposed method tag: `both` (scan: time configs whose only reference is
    a GPS or PPS refclock or gpsd shared memory, no network `server` or
    `pool` lines, no receiver-status monitoring; model: criticality and
    loss-of-fix behavior).
  - Eval cases: positive: a chrony config with only a PPS refclock on a
    substation controller; firmware that blocks startup until GPS time
    arrives; a host that keeps following a receiver reporting no fix.
    Negative: a PPS refclock plus three network sources, an OCXO holdover
    budget, and alarms on fix loss.
- C27.20 GPS hardware does not mean GPS sets the clock.
  - Facts: phones usually set time from carrier NITZ and NTP; Android's
    automatic-time service ranks sources by a device-configurable list
    whose defaults favor telephony and network, with GNSS an optional,
    often disabled origin; iOS uses the carrier and Apple's servers; users
    can turn automatic time off. The GNSS receiver often sits in a modem
    or baseband subsystem that does not discipline the OS clock; apps see
    GNSS time only as fix time (Android `Location.getTime`), which can
    differ from `System.currentTimeMillis`. GPS is often off or without a
    fix (C27.19). On Linux, GPS affects the clock only if gpsd feeds the
    time daemon; NMEA time is late and jittery (tens to hundreds of ms),
    and precision needs PPS. The RTC sets time at boot (C27.16). Vehicles,
    trackers, and gateways mix sources by undocumented vendor rules.
    Receiver bugs make GNSS time wrong (C15.2). Not verifiable here.
  - In code and operations: device time treated as GPS-accurate because
    the device has GPS; fix times and system-clock times mixed in one
    comparison, duration, or ordering; gpsd not connected to the time
    daemon, or NMEA time used where PPS precision is needed; fleet logic
    assuming every device uses the same source.
  - Fix: document each device type's source priority and treat device
    time as untrusted for decisions (C15.4, C15.6). Use fix time only as
    fix time, and measure the offset before combining it with the system
    clock. Connect gpsd with PPS where Linux devices should use GPS, with
    network cross-checks (C27.16). Record each device's time source and
    quality with its data (C16.3).
  - Not a finding: apps treating device time as untrusted and using
    server time for decisions.
  - Escalate: tracking, fleet, or measurement products without documented
    device time sources.
  - Proposed method tag: `both` (scan: `Location.getTime` or GNSS
    timestamps compared or subtracted with `System.currentTimeMillis` or
    `Date.now()`, gpsd present without a refclock or SHM source in the
    time daemon, NMEA time parsing in precision paths; model: whether
    device time drives decisions).
  - Eval cases: positive: a fleet app computing trip duration as fix time
    minus `System.currentTimeMillis`; a tracker trusting device time as
    "GPS time" for evidence logs; a Linux gateway with gpsd running but no
    chrony refclock. Negative: an app sending fix time and device time as
    separate labeled fields, with the server assigning authoritative
    time.
- C27.21 A GPS fix can still give the wrong time.
  - Facts: GPS time runs 18 s ahead of UTC, and receivers convert using
    navigation-message UTC parameters that repeat only every 12.5
    minutes, so a cold receiver can output time off by the leap-second
    count, and some output GPS time by default (C17.5). Dates come from a
    wrapping week number (10-bit wraps every 1,024 weeks) with the era
    inferred from firmware (C15.2). NMEA `RMC` has a status field (`A`
    valid, `V` void), and receivers keep outputting time while
    free-running. Pairing PPS with the right NMEA second is
    vendor-specific, and mistakes give whole-second errors. Cable delay
    (roughly 4 to 5 ns per metre of coax), receiver delays, survey error
    in timing mode (about 3.3 ns per metre), PPS sawtooth quantization,
    multipath, and ionosphere add bias that matters below a microsecond.
    Spoofing yields attacker time with a valid-looking fix (University of
    Texas yacht experiment, 2013) (C27.11). The system and receivers have
    broadcast or applied wrong data (C27.19, C17.2). Not verifiable here.
  - In code and operations: NMEA time read without checking `RMC` status
    or fix quality; GPS time used as UTC, or a hardcoded 18 s instead of
    broadcast parameters; week numbers modulo 1,024 without an era rule;
    PPS paired with NMEA by assumption; precision timing without delay
    compensation; no spoofing or jump detection.
  - Fix: use gpsd or a maintained vendor library rather than hand parsing
    (new dependencies need approval), and accept time only from valid
    fixes with UTC parameters received. Take the GPS-UTC offset from
    broadcast data. Keep firmware supported and test rollover and
    leap-second handling ahead (C27.19). Calibrate delays and survey the
    antenna where precision matters. Cross-check GNSS against independent
    network sources and alarm on disagreement, jumps, and whole-second
    errors (C27.16).
  - Not a finding: library-handled receivers whose time is cross-checked
    and monitored.
  - Escalate: precision or regulated GNSS timing without a stated error
    budget, calibration, and spoofing defense.
  - Proposed method tag: `both` (scan: NMEA `$GPRMC`/`$GNRMC` parsing
    without status checks, `% 1024` week handling, literal 18-second
    GPS-UTC offsets, PPS refclocks without network cross-check sources;
    model: precision requirements and spoofing exposure).
  - Eval cases: positive: a parser taking the time field from `RMC` lines
    marked `V`; code subtracting a literal 18 s from GPS time; firmware
    computing dates as week modulo 1,024 with a fixed 1980 era; a PPS
    setup with no check for whole-second errors. Negative: gpsd feeding
    chrony with PPS, validity checks, broadcast UTC offset, calibrated
    cable delay, and network cross-checks with alarms.
- C27.22 No single source should always win, including GPS.
  - Facts: fixed-priority arbitration lets one faulty or spoofed source
    override several that agree (spoofed fix, whole-second PPS error,
    stale leap offset; C27.11, C27.21). Daemons select by agreement and
    quality, discarding sources outside the majority; chrony `trust`
    exempts a source from rejection and `prefer` biases toward it, so
    marking GPS both makes it unchallengeable. GPS is best only while
    healthy and agreeing; otherwise holdover or network sources are
    better (C27.5, C27.19). Elapsed time, ordering, media, and decision
    authority do not come from GPS (C27.18), and app fix time must not
    override server-assigned time (C15.4, C27.20). Legal or regulated
    time may be defined by an authority or contract, so GPS-derived UTC
    needs documented traceability there (C27.7, C27.9). GPS gives UTC,
    not local time (C14, C10).
  - In code and operations: GPS refclock marked `trust` (often with
    `prefer`); code setting the system clock from GPS whenever a fix
    exists, without comparison; apps replacing server or device time with
    fix time unconditionally; local time derived from GPS without a zone
    source.
  - Fix: arbitrate by health and agreement, preferring GPS for precision
    only while valid and consistent with independent sources (C27.16).
    Never let one source be unchallengeable; use `prefer` only with enough
    independent sources to reject it. Keep decision authority on servers
    and separate clocks per job (C27.18). Document the hierarchy, health
    criteria, and traceability.
  - Not a finding: GPS preferred inside agreement-based selection where
    independent sources can reject it.
  - Escalate: critical systems without a stated source arbitration
    policy.
  - Proposed method tag: `both` (scan: `trust` or `prefer` on GPS, PPS, or
    SHM refclocks, code calling `settimeofday` or `clock_settime` from
    NMEA or GNSS data, fix time assigned to authoritative fields; model:
    the arbitration policy and its fallbacks).
  - Eval cases: positive: chrony with `refclock SHM 0 trust prefer` and two
    network sources that can never reject it; firmware that sets the clock
    from every NMEA fix; an app overwriting the server's order timestamp
    with fix time. Negative: a PPS refclock marked `prefer` with four
    independent network sources, no `trust`, and alarms on disagreement.
- C27.23 Time services are attack surface and must be secured.
  - Facts: ntpd `monlist` (CVE-2013-5211) enabled amplification attacks,
    with US-CERT TA14-013A reporting factors in the hundreds, and open
    control queries (modes 6 and 7) leak version, peers, and config.
    Daemons have had remote buffer overflows (ntpd before 4.2.8,
    CVE-2014-9295). chrony's command port (UDP 323) belongs on localhost
    with narrow `cmdallow`; ntpd needs `restrict ... noquery nomodify`.
    Private servers end up internet-facing through broad UDP 123 rules or
    `allow` all. Setting the clock needs root or `CAP_SYS_TIME`; daemons
    should keep only that capability (chrony `-u`). Linux time namespaces
    cover only the monotonic and boot-time clocks, so a container with
    `CAP_SYS_TIME` or privileged mode can change the host's clock for
    every workload. Legacy NTP symmetric keys often use MD5, which RFC
    8573 replaced with AES-CMAC; MD5 in security-sensitive use is a
    finding under the user's Rule 7, and readable key files expose keys.
    NTS servers need certificate renewal or clients stop syncing (C27.1).
    PTP usually relies on network isolation; anyone on a reachable PTP
    network can become grandmaster (IEEE 1588-2019 has an optional
    security annex). Not exercised from this container.
  - In code and operations: ntpd without `noquery nomodify` or
    `disable monitor`; chrony `bindcmdaddress 0.0.0.0`, broad `cmdallow`,
    or `allow` all on hosts not meant to serve; inbound UDP 123 from
    anywhere; root or unpatched daemons on exposed hosts; containers with
    `CAP_SYS_TIME` or `privileged: true`; MD5 entries in NTP `keys` files,
    or world-readable key files; unrenewed NTS certificates; PTP on shared
    networks.
  - Fix: serve only where intended and restrict queries and control
    (`noquery`, `nomodify`, localhost command ports), blocking inbound UDP
    123 elsewhere for both families (C27.13). Patch daemons; switching
    implementations needs approval. Run daemons unprivileged with only
    `CAP_SYS_TIME`, and never grant it or privileged mode to containers.
    Replace MD5 keys with AES-CMAC or use NTS, with restricted key files.
    Automate NTS certificate renewal and monitor expiry (C26.3). Isolate
    PTP networks or use its security features.
  - Not a finding: hardened, patched internal time servers serving only
    intended networks with restricted control.
  - Escalate: time servers whose exposure, patch level, or configuration
    is outside the review unit.
  - Proposed method tag: `heuristic` (scan: ntp.conf `restrict` and
    `monitor` lines, chrony `bindcmdaddress`, `cmdallow`, `allow`,
    security-group or firewall rules for UDP 123 from 0.0.0.0/0 or ::/0,
    `CAP_SYS_TIME` or `privileged: true` in container specs, MD5 in NTP
    `keys` files, key file modes, daemon user settings; the model confirms
    each hit).
  - Eval cases: positive: an ntp.conf with no `restrict` lines on an
    internet-facing host; a Kubernetes pod spec adding `SYS_TIME` to run
    chronyd; a `keys` file with `1 MD5 secret`; chrony `bindcmdaddress
    0.0.0.0`; a security group opening UDP 123 to the world on an app
    server. Negative: an internal chrony server with `allow` limited to
    its subnets, command port on localhost, running as `chrony`, NTS with
    automated renewal.
- C27.24 RTC-only operation must be designed (from BP-3, approved by the
  user).
  - Facts: an RTC alone is an acceptable last resort, but its time
    degrades: about 1.7 s a day at 20 ppm and about 0.17 s a day at 2 ppm
    (computed from typical ratings), varying with temperature and age.
    Power or battery loss resets it (C15.2). Many RTCs count whole
    seconds, have limited year registers or leap logic only to 2099
    (C2.1, C22.1), ignore leap seconds and DST, and hold local time on
    Windows (C15.1).
  - In code and operations: devices or hosts that can fall back to RTC
    time with no error bound, no RTC-only data marking, no reset
    detection, no drift calibration, no limits on decisions made on RTC
    time, or an unplanned jump when a source returns; local time stored
    in the RTC; no battery replacement plan.
  - Fix: keep UTC in the RTC. Track time since last good sync and expose
    an error bound (drift times elapsed). Mark RTC-era data with its
    source and bound (C16.3, C8.1). Calibrate drift when a reference is
    available (chrony `rtcfile` and `rtcautotrim`, or `/etc/adjtime` with
    `hwclock --adjust`) and keep the RTC updated (C27.16). Detect resets
    with a floor and ceiling and battery signals (C15.2). Widen
    tolerances or defer decisions needing more accuracy than the bound.
    Keep durations monotonic and ordering sequence-based (C18.1, C19.2).
    Rejoin by slew or planned step and record corrections (C27.18). Plan
    batteries and check RTC range limits for the service life (C25.3).
  - Not a finding: offline devices with a documented, designed RTC-only
    mode as above.
  - Escalate: devices expected to run offline for long periods without a
    stated RTC-only accuracy requirement and behavior.
  - Proposed method tag: `both` (scan: `/dev/rtc`, `hwclock`, RTC driver
    use, `rtcfile` and `rtcsync` settings, missing drift files, RTC
    written in local time; model: whether the RTC-only mode meets the
    design requirements).
  - Eval cases: positive: a field logger that runs months offline on its
    RTC and stamps records as exact UTC with no bound or source marking;
    a device that accepts 1970 from a reset RTC and issues tokens; a
    gateway stepping hours of correction into live data when the network
    returns. Negative: a device recording "rtc-only, +/- 40 s" with each
    sample, calibrating drift when online, refusing token issuance beyond
    its bound, and slewing back on reconnect.
- Proposed severity (for the user to decide; C27.7 is the user's own
  decision, recorded in C27.7), by check:
  - CRITICAL:
    - C27.1: authorization, token validity, or payment relies on
      unchecked, unauthenticated, or possibly absent sync on an
      attacker-reachable or client-controlled path.
    - C27.8: authoritative, regulated, or security-relevant time accepts
      replies without validating synchronization status or origin.
    - C27.9: such time rests on a single government server or on stratum
      as proof of accuracy.
    - C27.10: such time follows a single nearest source, or accepts
      network-supplied NTP servers on untrusted networks.
    - C27.11: certificate, token, replay, or license decisions rely on
      time an attacker can shift.
    - C27.12: authoritative, regulated, safety, or critical-infrastructure
      time depends on one government or operator with no holdover or
      alternative.
    - C27.15: such time follows one or two sources with no agreement
      requirement.
    - C27.19: safety, critical-infrastructure, regulated, or
      security-relevant time depends on GPS alone with no holdover or
      alternative.
    - C27.21: safety, regulated, or security-relevant time accepts GNSS
      time without validity checks or independent cross-checks.
    - C27.22: such time lets GPS override agreeing sources by rule.
    - C27.23: a container or untrusted workload can set a shared host's
      clock (`CAP_SYS_TIME` or privileged), or a time daemon with known
      remote-code-execution flaws is exposed.
  - HIGH:
    - C27.1: expiry, retention, or scheduling on a core path assumes sync
      without checking.
    - C27.3: a fleet compares time without monitored sync.
    - C27.4: precision or regulated timing lacks a suitable source.
    - C27.5: lost lock corrupts measurements, control, or broadcast output
      undetected.
    - C27.6: a decision assumes another platform's sync behavior or
      accuracy.
    - C27.8: custom clients ignore reply quality fields; servers serve an
      undisciplined local clock to others.
    - C27.9: code accepts stratum 0 replies as time or treats stratum as
      accuracy on a core path.
    - C27.10: pinned lowest-latency single-source selection on a core
      path.
    - C27.11: unauthenticated sync on security-relevant hosts; fake time
      servers reachable from production.
    - C27.12: single-constellation GNSS timing on core paths; one country's
      service hardcoded in international products.
    - C27.13: hosts that cannot sync on IPv6-only networks; time-server
      ACLs open on one address family; NTS blocked on security-relevant
      hosts.
    - C27.14: silent or refusing servers hang startup or core requests;
      failed queries become time values; fleet polling can overload
      third-party services.
    - C27.15: custom clients averaging or taking the first reply on a core
      path.
    - C27.16: conflicting clock disciplines; reboots starting from stale
      time on devices that act before syncing; authoritative hosts
      ignoring available independent references.
    - C27.17: cross-node ordering, leases, or expiry relying on
      independently synced nodes; client device time treated as
      authoritative.
    - C27.18: external time steering breaks leases, consensus, timeouts,
      media, or control on a core path; loss of external time halts a
      core service with no holdover; raw timestamps from a legacy box with
      a known-wrong clock used as UTC on a core path; automation that
      would correct such a box live without its owners' consent.
    - C27.19: core systems cannot start or keep correct time without a
      fix, or follow a receiver that has lost its fix.
    - C27.20: tracking, billing, evidence, or safety decisions on a core
      path assume device time is GPS time, or mix fix time and system
      time.
    - C27.21: GPS time used as UTC, invalid-fix time accepted, or
      unhandled week rollover on a core path.
    - C27.22: apps replacing authoritative server time with fix time on a
      core path; `trust` on a GPS refclock on core systems.
    - C27.23: amplification-capable or remotely controllable time
      servers; MD5 NTP keys in security-relevant use (user Rule 7); open
      serving on hosts not meant to serve.
    - C27.24: RTC-only time used for security, billing, or deadline
      decisions on a core path without an error bound or reset
      detection.
  - MEDIUM: missing sync monitoring (C27.1, C27.3); weak sync
    configuration (C27.2); mixed smear policies (C27.4);
    platform-specific scripts (C27.6); polling beyond service rules
    (C27.9, C27.14); low source diversity and stale one-time selection
    (C27.10); missing alarms on time configuration changes (C27.11);
    undocumented time-source dependencies (C27.12); IPv4-only clients and
    validators in products that may need IPv6 (C27.13); missing backoff,
    jitter, or failover (C27.14); missing source-count monitoring
    (C27.15); missing RTC updates and fallback plans (C27.16); fleets
    without an internal tier and an unredundant internal server (C27.17);
    undocumented time-domain mapping and missing inter-node skew bounds
    (C27.18); missing receiver monitoring and unsupported firmware
    (C27.19); unconnected gpsd setups and undocumented device time
    sources (C27.20); missing delay calibration where precision is
    stated, and missing GNSS jump alarms (C27.21); undocumented source
    arbitration policy (C27.22); time daemons running as root, readable
    key files, and unmonitored NTS certificate expiry (C27.23); RTC-only
    data without source and bound marking, no drift calibration, and no
    battery plan (C27.24).
  - LOW: test-only code.

Point ledger for C27:
- BP-4 (best practice): Roughtime uses, correct use, and findings ->
  C27.11 (user decision: fold into C27.11).
- BP-3 (best practice, not a PA): design requirements for RTC-only
  operation -> C27.24 (user-approved new check). Floors -> C15.2.
  Holdover -> C27.5. RTC updates -> C27.16. Rejoin -> C27.18.
- PA-155: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.23. Per-family ACLs -> C27.13. NTS
  expiry stopping sync -> C27.1. Monitoring -> C26.3. MD5 keys also tie
  to the user's Rule 7. Severity -> C27 severity.
- PA-154: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.22. Combining sources -> C27.16.
  Clock per job -> C27.18. GPS faults -> C27.19 and C27.21. Zones ->
  C14 and C10. Severity -> C27 severity.
- PA-153: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.21. GPS-UTC offset -> C17.5.
  Rollover -> C15.2. Spoofing -> C27.11. System errors -> C27.19.
  Cross-checks -> C27.16. Severity -> C27 severity.
- PA-152: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.20. Availability -> C27.19. RTC and
  cross-checks -> C27.16. Untrusted device time -> C15.4 and C15.6.
  Per-sample context -> C16.3. Severity -> C27 severity.
- PA-151: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.19. Rollovers -> C15.2. Leap seconds
  -> C17.2. GPS-UTC offset -> C17.5. Constellations and jamming ->
  C27.12. Holdover -> C27.5. Distribution -> C27.17. Tests -> C25.3.
  Severity -> C27 severity.
- PA-150: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation, and the user's legacy-server scenario ->
  C27.18. Monotonic durations -> C18.1.
  Ordering -> C19.6. Media clocks -> C16.5. Holdover -> C27.5. Severity
  -> C27 severity.
- PA-149: all facts, code and operations patterns, checks, fixes,
  not-a-findings, escalation -> C27.17. Server authority -> C15.4 and
  C15.6. Ordering -> C19.6. Redundancy and source counts -> C27.15.
  Severity -> C27 severity.
- PA-148: all facts, code and operations patterns, checks, fixes,
  not-a-findings, escalation -> C27.16. RTC failures and floors ->
  C15.2. GPS-UTC offset -> C17.5. Holdover -> C27.5. Hypervisor time ->
  C27.6. Monotonic clocks -> C18.1. Severity -> C27 severity.
- PA-147: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.15. Independence -> C27.10 and C27.12.
  Live count -> C27.14. Monitoring -> C26.3. Severity -> C27 severity.
- PA-146: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.14. Kiss-o'-Death fields -> C27.8.
  Polling rules -> C27.9. Shared IPv4 -> C27.13. No-time policy ->
  C27.1. Monitoring -> C26.3. Severity -> C27 severity.
- PA-145: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.13. Hardcoded IPs and pool zones ->
  C27.7. Rate limiting behind CGNAT -> C27.8. Severity -> C27 severity.
- PA-144: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.12. Holdover -> C27.5. Diversity ->
  C27.10. Shift detection -> C27.11. National services -> C27.9.
  Severity -> C27 severity.
- PA-143: all facts, code and operations patterns, checks, fixes,
  not-a-findings, escalation -> C27.11. Smearing -> C27.4. Pool members
  -> C27.7. Spoofing and authentication -> C27.1 and C27.2. Fake time
  servers -> C25.2. Time bombs -> C26.2. Plausibility bounds -> C15.2.
  Severity -> C27 severity.
- PA-142: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.10. Error bound -> C27.8.
  Authentication -> C27.2. Load spreading and disciplined local servers
  -> C27.7. Severity -> C27 severity.
- PA-141: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.9. Kiss-o'-Death stratum 0 -> C27.8.
  Path asymmetry -> C15.3 by reference. Traceability and multiple
  sources -> C27.7. Severity -> C27 severity.
- PA-140: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.8. Round-trip error -> C15.3 by
  reference. GPS rollover -> C15.2 by reference. Severity -> C27
  severity.
- PA-139: all facts, code and operations patterns, checks, fixes,
  not-a-finding, escalation -> C27.7. Direct single queries -> C27.1.
  Mixed leap policies -> C27.4. Monitoring -> C26.3 by reference.
  Severity -> C27 severity.
- PA-138: all facts, code and operations patterns, checks, fixes,
  not-a-findings, escalation -> C27.6. Device time untrusted -> C15.4
  and C15.6 by reference. Windows local-time RTC -> C15.1 (already there
  via PA-11). Leap-second handling differences -> C27.4 and C17. Severity
  -> C27 severity.
- Moved from C15.1 (approved class): "run time sync and monitor offset"
  fix -> C27.1 and C27.3; C15.1 keeps a reference.
- Moved from C15.2: ntpd panic threshold and `-g`, chrony slew and
  `makestep`, step-at-startup fix, NTS -> C27.2; C15.2 keeps a reference.
- Moved from C15.3: keep fleet clocks synced and monitored -> C27.3;
  C15.3 keeps a reference.
- Moved from C16.1: slew rates, leap smearing and providers, mixed smear
  sources, one-smear-policy fix, dedicated precision sources -> C27.4;
  C16.1 keeps the rate effect and a reference.
- Moved from C16.5: lost references, holdover, stepping on reacquisition,
  loss-of-lock detection, holdover budget, resync after resume,
  reconnect, and failover -> C27.5; C16.5 keeps stream alignment and a
  reference.
- Moved from C17.2: one smear or step policy across the fleet -> C27.4
  reference.
- Referenced from C26.3: offset, sync-state, and holdover monitoring
  stays in the C26.3 monitoring list and points to C27.
- PA-137: all facts, code and operations patterns, checks, fixes,
  not-a-findings, escalation -> C27.1. Large-offset refusal -> C15.2 by
  reference. 2036 rollover -> C22.1 by reference. UTC-only and local
  date -> C9 and C10 by reference. Monitoring -> C26.3 by reference.
  Severity -> C27 severity.
