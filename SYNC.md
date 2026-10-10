# SYNC.md

Generay's time synchronization module. Load it with `TIME.md`, which defines modes, detection, severity, verdicts,
reporting, and prohibitions. This module adds check class C27. Full detail and the point ledger live in
`docs/classes/C27-time-synchronization.md`.

## Guiding Practices

- **BP-2. Never depend on a single source of time.** Diversify across reliable, independent sources within reason:
  operator and upstream, jurisdiction, technology (NTP or NTS, GNSS with PPS, PTP, radio, disciplined RTC or holdover
  oscillator), constellation, network path and address family, under one leap policy. Combine by agreement, never by
  a fixed winner. Correlated or unhealthy sources add count, not safety. Where a wrong source must be outvoted, use
  at least four independent sources. Ordinary clients get diversity through an internal tier.
- **BP-3. An RTC alone is a last resort that must be designed for.** See C27.24.
- **BP-4. Roughtime is an option** when NTP is unreachable or unreliable, or operationally better. See C27.11.

## Severity in This Module

`TIME.md` section 4 applies. Approved CRITICAL exceptions: where authoritative, regulated, or security-relevant time
(audit trails, trading, legal records, token issuers, certificate authorities, time services for others) depends on
the conditions named CRITICAL below, rate CRITICAL even without an attacker, payment, or safety effect.

## Checks

### C27.7 Public pools are not authoritative time sources (both)

Priority check. The NTP Pool is volunteer-run. DNS returns rotating servers of unknown operators. Monitoring drops
bad servers only after detection, members often sync from each other with no traceability, and replies are
unauthenticated by default with no service level and no traceability to a national laboratory's UTC(k).
- Flag: audit, trading, legal, token, CA, or time-service hosts syncing only from the pool or a distribution default;
  hardcoded NTP server IPs in code, firmware, or images; products shipping the generic pool instead of a registered
  vendor zone; one direct pool query trusted; "accurate" or "traceable" claims without a stated source and bound.
- Not a finding: ordinary hosts on pool or distribution defaults that issue no authoritative or regulated times.
- Escalate: authoritative, legal, or regulated timestamps without a stated source, accuracy, and traceability.
- Severity (maintainer decision): CRITICAL when authoritative, regulated, or security-relevant time relies on pool
  sources, a single source, or unauthenticated sources with no stated accuracy or traceability. HIGH for hardcoded
  NTP IPs. MEDIUM for generic pool instead of a vendor zone, and undocumented sources. LOW for test-only code.

### C27.1 Time sync is best effort, not a guarantee (both)

- Flag: "the host runs NTP" treated as proof of correct time with no sync-state check (`adjtimex`, `timedatectl show`,
  `chronyc tracking`); security or expiry decisions on devices that may never sync; hand-rolled SNTP trusting one
  reply; containers given `CAP_SYS_TIME` or a sync daemon (they share the host clock); no defined behavior with no
  time source.
- Not a finding: display-only device time; systems that check and act on sync state.
- Severity: CRITICAL when authorization, tokens, or payment rely on unchecked or absent sync on an attacker-reachable
  path. HIGH when expiry, retention, or scheduling assume sync without checking.

### C27.2 Large offsets, startup stepping, authentication (heuristic)

- Flag: ntpd without `-g` or chrony without `makestep` on hosts that can boot far off; no NTS where spoofing matters.
- Fix: step at startup, then slew; NTS (RFC 8915) where authentication matters.

### C27.3 Fleet sync sources and coverage (both)

- Flag: hosts or regions without sync; one-server configs; mixed fleet policies; no offset or sync-state monitoring.
- Severity: HIGH when a fleet compares time without monitored sync.

### C27.4 Slewing, smearing, and precision sources (both)

- Flag: mixed smeared and unsmeared sources in one system; precision domains on ordinary NTP without an accuracy
  budget. Slews can stretch a minute to about 55 to 65 s.
- Fix: one leap policy per system; PTP or GNSS-disciplined sources with a stated budget where precision matters.

### C27.5 Reference loss, holdover, resynchronization (llm)

- Flag: no loss-of-lock detection, no holdover budget, no resync after resume, reconnect, or failover.
- Severity: HIGH when lost lock corrupts measurements, control, or broadcast output undetected.

### C27.6 Sync differs by platform and environment (both)

- Flag: one platform's sync check or tool (`w32tm`, `timedatectl`, `sntp`, `hwclock`) used everywhere; one platform's
  accuracy assumed for all; apps setting the clock; clients assumed synced because servers are. Browsers expose no
  sync state.
- Fix: per-platform sync documentation and one check interface with an explicit "unknown" result.

### C27.8 An NTP reply is a measurement with an error bound (both)

- Flag: clients reading only the transmit timestamp; ignoring leap indicator 3, stratum 0 or 16, stale reference
  time, root distance, Kiss-o'-Death, or origin mismatch; no round-trip compensation; servers serving an
  undisciplined local clock (`127.127.1.0`, chrony `local`); accuracy claims without a measured bound.
- Severity: CRITICAL when authoritative or security time accepts unvalidated replies. HIGH for ignored quality
  fields and undisciplined servers.

### C27.9 Government servers: stratum is not authority (both)

- Flag: "stratum 1 from NIST, so authoritative" claims; stratum 0 replies accepted (stratum 0 is never served time);
  stratum treated as accuracy; one government server as the only source; polling faster than service rules (NIST:
  about once per 4 s at most).
- Severity: CRITICAL when authoritative time rests on one government server or stratum as proof.

### C27.10 Nearest and lowest latency is not best (both)

- Flag: ping-and-pin scripts; one or two nearby sources from one operator; DHCP-supplied NTP accepted on untrusted
  networks by authoritative hosts; server choice by geolocation.
- Severity: CRITICAL when authoritative time follows one nearest source or untrusted network-supplied servers.

### C27.11 Servers and attackers can shift time on purpose (both)

- Flag: certificate, token, replay, or license decisions with no defense against shifted time; unauthenticated NTP on
  token or CA hosts; unlimited corrections after startup (no `maxchange`); writable NTP configuration; fake time
  servers reachable from production.
- Roughtime (BP-4): signs every reply with a public key, and chained queries prove a server lied. Use it to bootstrap
  devices whose wrong clock breaks TLS, as a signed cross-check, or when NTP is unreachable. Correct use: pinned,
  updatable keys; half a dozen or more independent servers to establish the time; results as intervals; never for
  accuracy finer than about 10 s. Flag single-server or unpinned use and precision use.
- Severity: CRITICAL when security decisions rely on time an attacker can shift.

### C27.12 One government or operator is a single point of failure (both)

- Flag: all sources from one operator or domain (for example only `*.nist.gov`); single-constellation GNSS; critical
  timing without holdover; one country's service hardcoded in products sold abroad.
- Severity: CRITICAL for authoritative, safety, or critical-infrastructure time with no alternative or holdover.

### C27.13 Sync must work over IPv6 and needed ports (heuristic)

- Flag: `AF_INET`-only clients or A-only resolution; IPv4-only validators; literal IPv4 servers; `-4` daemon flags;
  `restrict` or firewall rules for one family; TCP 4460 closed where NTS is used. `pool.ntp.org` has no AAAA records;
  `2.pool.ntp.org` does.

### C27.14 Servers stay silent, refuse, and rate-limit (both)

- Flag: time queries without timeouts at boot or in request paths; retries without backoff or jitter; Kiss-o'-Death
  ignored; failed queries turned into a time value (offset 0, local clock, epoch); fleets polling in lockstep; no
  failover. Normal minimum poll interval is 64 s.

### C27.15 One or two sources cannot vote (both)

- Flag: one or two sources on hosts needing correct time; `minsources 1` or `tos minsane 1` there; clients averaging
  or taking the first reply; no monitoring of reachable and selected source counts.
- Severity: CRITICAL when authoritative time follows one or two sources with no agreement requirement.

### C27.16 NTP does not replace the RTC, GNSS, or other sources (both)

- Flag: no RTC update (`rtcsync`, `hwclock --systohc`); unused GNSS or PPS references; hypervisor periodic sync and an
  NTP daemon both disciplining one clock; no cross-check or fallback order.

### C27.17 Time distribution needs a hierarchy (both)

- Flag: large fleets on public servers with no internal tier; UDP 123 egress from every host; device time used as
  authoritative; mixed leap policies; one unredundant internal server.

### C27.18 External UTC is not the right clock for every job (llm)

- Flag: leases, timeouts, or consensus on the wall clock; media clocks slaved to NTP; services halting without external
  time; no inter-node skew bound; one clock for records and mechanics with no mapping.
- Legacy clocks that cannot change: measure offset and drift from outside, convert at the boundary with the correction
  recorded, never sync others from the box, protect it from accidental correction, and plan replacement. Flag raw
  timestamps used as UTC, others syncing from it, and automation correcting it without the owners' consent.

### C27.19 GPS is not always available or right (both)

- Flag: GPS or PPS as the sole source with no network sources or holdover; designs needing a fix at power-on; no
  receiver monitoring; following a receiver that lost its fix; firmware without support before rollover dates
  (next 10-bit week rollover 2038-11-21).
- Severity: CRITICAL for safety, regulated, or security time on GPS alone with no holdover or alternative.

### C27.20 GPS hardware does not mean GPS sets the clock (both)

- Flag: device time trusted as GPS time; fix time (for example Android `Location.getTime`) mixed with the system clock;
  gpsd not connected to the time daemon; NMEA time where PPS precision is needed.

### C27.21 A GPS fix can still give the wrong time (both)

- Flag: NMEA time read without `RMC` status (`A` or `V`) or fix checks; GPS time used as UTC or a hardcoded 18 s
  offset; week numbers modulo 1024 without an era rule; PPS paired with NMEA by assumption; no delay calibration where
  precision is stated; no spoofing or jump detection.
- Severity: CRITICAL when safety, regulated, or security time accepts unchecked GNSS time.

### C27.22 No single source should always win (both)

- Flag: GPS refclocks marked `trust` (often with `prefer`); clocks set from every fix; fix time overriding server time;
  local time derived from GPS without a zone source.
- Severity: CRITICAL when such time lets GPS override agreeing sources by rule.

### C27.23 Time services are attack surface (heuristic)

- Flag: ntpd without `restrict ... noquery nomodify` or with `monitor` (CVE-2013-5211 amplification); chrony
  `bindcmdaddress 0.0.0.0` or broad `cmdallow`; UDP 123 open to the world; root or unpatched daemons; containers with
  `CAP_SYS_TIME` or `privileged: true` (they can set the shared host clock); MD5 NTP keys; readable key files;
  unrenewed NTS certificates; PTP on shared networks.
- Severity: CRITICAL when an untrusted workload can set a shared host clock or an exposed daemon has known remote code
  execution flaws. HIGH for amplification-capable or remotely controllable servers and MD5 keys.

### C27.24 RTC-only operation must be designed (both)

- An RTC drifts about 1.7 s a day at 20 ppm and about 0.17 s a day at 2 ppm, and resets on power or battery loss.
- Flag: RTC-only time with no error bound, no source marking on data, no reset detection (floor and ceiling), no
  drift calibration, local time in the RTC, accuracy-sensitive decisions on RTC-only time, or an unplanned jump on
  rejoin.
- Severity: HIGH when security, billing, or deadline decisions use RTC-only time without a bound or reset detection.
