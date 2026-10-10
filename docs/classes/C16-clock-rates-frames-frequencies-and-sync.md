# C16 Clock rates, frames, frequencies, and sync

(sources: PA-20, 94, 119, 120, 121, 122; inbound from C12.3, C15.1, C15.6) Approved by the user.

Scope: clocks ticking at different rates, relativistic and time-scale
effects on moving platforms, a clock's context changing during a series,
device frequencies that are fractional or variable, and synchronizing
streams and signals. Leap seconds as such are C17. Monotonic clocks,
timers, tick counting, and sleeps are C18. Offsets between client and
server clocks are C15.

- C16.1 Clocks tick at different rates.
  - Facts: every oscillator drifts (C15.3). Sync slewing and leap
    smearing stretch or shrink seconds, so a "minute" can last about 55
    to 65 real seconds during a large slew (rates and policy in C27.4).
    Guest clocks tick unevenly under host load or pauses.
  - In code: durations started on one host and ended on another, or
    measured on the client and billed on the server (C7.5). Precise
    measurements (benchmarks, SLAs, trading, metering) on a wall clock
    during a slew or smear (mixed smear sources C27.4).
  - Fix: measure each duration on one clock, preferably the authoritative
    server's, as the difference of two monotonic readings (C18). Smear
    policy and precision time sources are C27.4.
  - Not a finding: UI animation and coarse timers where small rate errors
    are acceptable.
  - Escalate: billing, metering, SLA, or timed-assessment durations
    measured across clocks, or in precision domains, without a stated
    accuracy.
- C16.2 Relativity and time scales on moving platforms.
  - Facts: a clock higher in Earth's gravity runs faster by about 1.1e-16
    per meter near the surface (optical clocks measured 33 cm, NIST
    2010); Boulder at about 1,650 m gains about 15 ns a day on sea level;
    TAI corrects contributing clocks to a reference surface. Moving clocks
    run slower. GPS satellites: about +45.7 us/day from gravity and -7.2
    from speed, net about +38.5, so satellite clocks are tuned before
    launch. ISS: net about 25 us/day slower than the ground (computed).
    Aircraft: tens of ns per day (Hafele-Keating 1971: about -59 ns
    eastward, +273 ns westward). Moon: about +56 us/day, and a 2024 US
    directive tasked NASA with a Coordinated Lunar Time. A satellite's
    rate varies around an elliptical orbit: GPS receivers apply
    `F * e * sqrt(a) * sin(E)`, about 23 ns amplitude at e = 0.01 and
    46 ns at e = 0.02 (computed from F = -4.442807633e-10 s per root
    meter). Synchronizing clocks on a rotating Earth needs a Sagnac
    correction that depends on the signal path. Scales exist for this:
    TT, TCG, TCB, TDB. Extreme cases (C15.6) follow the same rules.
  - In code: space, satellite, aviation, and precision-timing software
    treating onboard or remote seconds as ground UTC seconds with no
    correction or scale conversion. Hardcoded relativistic constants
    (a literal 38.5 us/day) instead of values computed for the orbit or
    taken from a maintained source. Timestamps from spacecraft, aircraft,
    and ground stations compared without naming each one's scale.
  - Fix: name the time scale of every timestamp (UTC, TAI, TT, GPS time,
    onboard proper time). Convert with a maintained library (SOFA/ERFA,
    Astropy `Time`) and published interface specifications, not
    hand-written approximations (new dependencies need approval).
  - Not a finding: relativistic effects in ordinary ground software,
    which are far below other error sources. Raise them only in space,
    satellite, navigation, aviation timing, or metrology code.
  - Escalate: space, satellite, aviation, telemetry, or navigation timing
    code whose time scale, relativistic handling, frame, or required
    accuracy is not stated.
- C16.3 A clock's context changes during a series.
  - Facts: for one device, the zone changes (travel, C14), the sync
    source or policy changes (smeared to unsmeared) or a step happens
    (C15.1), monotonic clocks restart at reboot (C19), a VM migrates to a
    host with another counter, and a GPS receiver switches scale when it
    gets a fix or the leap-second count (C17).
  - In code: device time series treated as one homogeneous sequence. No
    per-sample record of zone, offset, sync state, boot ID, or time scale.
    Durations or rates computed across a context change.
  - Fix: record each sample's context. Split series at context changes,
    or convert every sample to one reference (UTC instants or a named
    scale such as TAI) before comparing.
  - Not a finding: ground business software handling zone, sync, and
    reboot changes.
- C16.4 Device frequencies that are fractional or variable.
  - Facts: NTSC-derived video rates are rational: "29.97" is exactly
    30000/1001, "23.976" 24000/1001, "59.94" 60000/1001. Treating
    30000/1001 as 30 fps drifts about 107.9 frames (3.6 s) per hour
    (computed). SMPTE drop-frame timecode skips frame numbers 00 and 01 at
    each minute except every tenth. Displays run at fractional (59.94,
    119.88 Hz) or variable rates, adaptive panels change rate with content
    and power mode, and `requestAnimationFrame` can stop in background
    tabs. 24 fps on 60 Hz alternates 3 and 2 refreshes (about 50 and 33
    ms, 3:2 pulldown, computed). Phone video is often variable frame rate.
    Thermal throttling and battery savers lower frame, processing, GPS,
    and sensor rates. OSes batch sensor events. Bluetooth intervals are
    renegotiated, Wi-Fi power saving delays delivery, and networks jitter.
    Game servers drop ticks under load. Power grids run near, not at, 50
    or 60 Hz: in 2018 a continental European deficit left grid-counting
    clocks about six minutes slow. Kernel ticks are whole hertz but not
    whole milliseconds (Windows 64 Hz = 15.625 ms, Linux `HZ=300` = 3.333
    ms).
  - In code: media timestamps as `frame_count / 30` or with float 29.97.
    Drop-frame and non-drop-frame timecode mixed or hand-converted. Time
    as `sample_index * nominal_period`. Fixed `dt` per frame or sample
    (stepping detail C18). Cooldowns counted in frames. Constant-frame-rate
    media pipelines. Gaps and bursts treated as faults. Grid-cycle or tick
    counts used as clocks.
  - Fix: represent rates as exact rationals (as FFmpeg does) and derive
    times from presentation or sample timestamps, not counts. Use timecode
    libraries with drop-frame rules (BP-1). Support variable frame rate
    end to end or convert at ingest. Buffer for jitter and tolerate gaps
    and bursts. Use a real clock, not cycle counts.
  - Not a finding: rational-rate or timestamp-driven pipelines.
  - Escalate: media, broadcast, or audio products without stated
    frame-rate and timecode standards. Sensor, medical-device, or control
    systems without a stated sampling regularity.
- C16.5 Synchronizing streams and keeping them synchronized.
  - Facts: equal frequency (syntonization) is not equal time
    (synchronization): two 48 kHz streams can start apart and stay apart.
    Same-nominal-rate oscillators drift (10 ppm is 0.864 s, or 41,472
    samples at 48 kHz, per day, computed). Pipelines add different and
    changing latencies. Presentation timestamps start arbitrarily, and
    MPEG-TS 33-bit 90 kHz timestamps wrap about every 26.5 hours
    (computed). Hardware clocks from different oscillators are
    asynchronous, and crossing between them needs synchronizers or data is
    corrupted by metastability. ITU-R BT.1359 reports audio-video offsets
    detectable at about 45 ms (audio leading) and 125 ms (audio lagging).
    Same-rate sensors sample at different instants on their own clocks.
    Shared references can be lost (C27.5). Sleep, resume,
    Bluetooth reconnects, hot-plugged devices, VM migration, and thermal
    changes break alignment. Lost packets, dropped frames, and buffer
    underruns shift count-based alignment permanently. Recorders synced
    once by a clap drift apart without shared timecode.
  - In code: streams merged by sample or frame index. Offsets assumed
    zero, or measured once at start. Pipeline latency ignored. Timestamps
    compared without a common base or wrap handling. No monitoring of
    offset or lock state (C27.5). Gaps and duplicates undetected.
  - Fix: share a reference (genlock, word clock, PTP IEEE 1588, GPS PPS;
    reference handling C27.5). Timestamp at capture against it and align
    by timestamp. Measure and correct offset, latency, and drift
    continuously (servo loops, resampling). Handle wraparound explicitly
    (C19). Fill or flag gaps instead of shifting data.
  - Not a finding: pipelines aligned by capture timestamps from a shared
    reference with continuous, monitored synchronization.
  - Escalate: media, broadcast, sensor-fusion, measurement, or control
    systems without a stated synchronization tolerance, drift tolerance,
    or holdover requirement.
- Proposed severity (for the user to decide), per check: HIGH when
  billing, metering, or safety timeouts use durations across clocks;
  navigation, telemetry, or measurement mixes scales or frames; or
  broadcast timing, captions, media-duration billing, medical, safety, or
  control readings, or stream alignment on a core path drift or lose lock
  undetected. MEDIUM for analytics, device series without context,
  consumer media, games, animation, and UI timers. LOW for test-only
  code.

Point ledger for C16:
- Inbound from C12.3: smeared clocks differing by fractions -> C16.1.
- Inbound from C15.1: smear versus step across providers -> C16.1.
- Inbound from C15.6: relativistic corrections and extreme cases ->
  C16.2.
- PA-20: drift, slewing, smearing, mixed sources, virtualization,
  cross-host durations, precise measurements during slew, one-smear fix,
  PTP fix, not-a-finding (UI timers), escalation -> C16.1. Relativity
  facts, space code patterns, constants, scale naming fix, library fix,
  ground not-a-finding, space escalation -> C16.2. Leap-second minutes,
  second 60 validation, accept-60 fix -> C17 (inbound). Sleep and suspend
  monotonic clocks, throttled timers, tick counting, wrong monotonic
  clock, monotonic fixes -> C18 (inbound). Severity -> C16 severity.
- PA-94: physical frames, eccentricity, Sagnac -> C16.2. Context-frame
  changes, homogeneous series, per-sample context, split-or-convert fix,
  not-a-finding -> C16.3. Library corrections fix and escalation ->
  C16.2. Severity -> C16 severity.
- PA-119: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C16.4. Fixed `dt` stepping -> C18 by reference. Severity
  -> C16 severity.
- PA-120: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C16.4. Accumulator stepping fix -> C18 (inbound).
  Severity -> C16 severity.
- PA-121: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C16.5. Severity -> C16 severity.
- PA-122: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C16.5. Severity -> C16 severity.
