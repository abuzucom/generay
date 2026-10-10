# C18 Elapsed time, timers, sleeps, and pauses

(sources: PA-21, 22, 54, 55, 62, 63, 117; inbound from PA-11, PA-12,
PA-13, PA-20, PA-119, PA-120, C9.2, C11.5, C11.6, C15.4, C17.3) Approved
by the user.

Scope: measuring elapsed and CPU time, timers and tick counting, pauses
and long gaps between steps, sleep semantics, scheduling at target times,
and deliberate timer interference. Wall-clock error is C15. Clock rates
are C16. Reading "now" and ordering are C19. Duration units and negative
durations are C21. Fake clocks and testability are C25.

- C18.1 Measuring elapsed and CPU time.
  - Facts: wall clocks step, slew, and smear (C15, C16), so wall-clock
    differences are not elapsed time and can be negative. Monotonic clocks
    differ on suspend: Linux `CLOCK_MONOTONIC` excludes it,
    `CLOCK_BOOTTIME` includes it, and macOS `mach_absolute_time` stops
    during sleep. CPU time differs from elapsed time: `sleep(1)` used 0.0
    s CPU over 1.0 s elapsed, and three busy processes used about 3 s of
    user CPU in 1 s elapsed (verified). Container CPU limits stretch
    elapsed time for the same work.
  - In code: durations, timeouts, retries, and rate limits from wall
    clocks (Python `time.time()`, JS `Date.now()`, Java
    `System.currentTimeMillis()`, .NET `DateTime.Now`/`UtcNow`
    subtraction), so backward jumps give negative durations or timeouts
    that never fire and forward jumps fire them at once. A monotonic clock
    with the wrong suspend behavior (a session timeout that should count
    laptop sleep uses one that pauses, or the reverse). CPU and elapsed
    time used interchangeably in throughput, billing, quotas, or ETAs.
    `RLIMIT_CPU` on I/O-bound work, or elapsed limits where CPU budgets
    were meant.
  - Fix: measure elapsed time as the difference of two readings of one
    monotonic clock (Python `time.monotonic()` or `perf_counter()`, JS
    `performance.now()`, Java `System.nanoTime()`, Go `time.Since`, .NET
    `Stopwatch`), choosing whether suspension counts (`CLOCK_BOOTTIME`
    where it must). Measure CPU time with CPU-time APIs
    (`time.process_time()`, `getrusage`,
    `clock_gettime(CLOCK_PROCESS_CPUTIME_ID)`). Record wall-clock start
    and end separately for audit. Track client expiries relative to a
    monotonic clock (C15.4).
  - Not a finding: monotonic elapsed measurement where elapsed time is
    the requirement.
  - Escalate: billing or quota rules stated as "runtime" without CPU or
    elapsed.
- C18.2 Timers and tick counts are not clocks.
  - Facts: timers fire late under load, GC, and scheduling, and are
    throttled on purpose: browsers limit background tabs to about once a
    second, and Chrome to about once a minute for long-hidden pages, a
    60-fold slowdown for tick-counted seconds. Mobile OSes suspend
    background apps. Deliberate scaling exists (simulations, backtests,
    games, speed hacks). Faulty hardware and unsynchronized TSC counters
    across cores on older systems distort rates. Variable frame and sample
    rates (C16.4).
  - In code: clocks built by counting (`seconds += 1` per
    `setInterval(..., 1000)` or per `sleep(1)` loop). Code after
    `setTimeout(fn, 60000)` assuming exactly 60 s passed. Physics,
    animation, or simulation stepped by a fixed `dt` per frame. Client
    timing trusted for game rules, timed exams, or cooldowns.
  - Fix: read a monotonic clock in each callback and act on measured
    elapsed time. Step simulations by measured time clamped to a maximum,
    or use a fixed step with an accumulator driven by measured time. Keep
    outcome-deciding timing on the server.
  - Not a finding: UI timers and animations where a stall only delays
    display. Simulations that scale time on purpose and document it.
- C18.3 Pauses and long gaps between steps.
  - Facts: stop-the-world GC, CPU starvation and throttling, swapping, and
    blocked event loops delay steps arbitrarily. Laptops close for a
    weekend, apps background for weeks, processes get `SIGSTOP` or a
    paused debugger, VMs and CRIU checkpoints resume months later, and
    serverless platforms freeze environments between invocations with
    module state intact. Long batch jobs run across midnights and
    month-ends. On resume the wall clock jumps while a sleep-excluding
    monotonic clock shows almost nothing.
  - In code: distributed locks and leases checked before a pause and acted
    on after it, so two holders write (Kleppmann's 2016 Redlock analysis).
    Heartbeats treating any missed beat as death, or a resumed process as
    healthy. "Now" cached at module scope (`const now = Date.now()`),
    especially in serverless handlers. Deadlines or tokens checked before
    a long `await`, sleep, or suspension and acted on after. "Today"
    computed once at the start of a job that runs past midnight. In-memory
    TTL caches assuming frequent checks. Overflows: Node `setTimeout` with
    2^31 ms or more fires after 1 ms (verified); Windows `GetTickCount`
    wraps every 49.7 days (wrap-safe comparison is C19); nanosecond
    durations truncated into 32-bit milliseconds. Rates divided by elapsed
    time that can be huge or zero.
  - Fix: protect lease-guarded writes with fencing tokens and recheck
    validity immediately before any side effect. Detect pauses (gaps
    between monotonic readings larger than expected) and recheck sessions,
    leases, and deadlines on resume and on visibility or power events.
    Read the clock again after every suspension point, and per serverless
    invocation. In long jobs, recompute day boundaries as the job runs or
    fix one documented as-of time. Saturate or clamp large elapsed values,
    use 64-bit counters, and chain or persist long delays below platform
    maximums. Guard division by elapsed time. Use a sleep-including clock
    where real elapsed time matters.
  - Not a finding: one as-of time fixed on purpose and documented.
  - Escalate: locks or leases without fencing where the tolerated pause is
    not stated. Long jobs crossing a period boundary where start date
    versus current date is not stated.
- C18.4 Sleeps return late, early, or on another clock.
  - Facts (verified, host-dependent): `Thread.sleep(1000)` took 1000.6
    ms, and the worst of 200 `Thread.sleep(1)` calls 1.6 ms. Windows'
    default timer granularity is about 15.6 ms. Java `Thread.sleep` throws
    `InterruptedException` (a 1000 ms sleep interrupted at 200 ms returned
    after 200.6 ms). POSIX `sleep` and `nanosleep` return early on
    signals. Python retries after a handler returns (PEP 475) unless it
    raises. `Object.wait` and condition variables wake spuriously. Node
    fired 3 of 200 `setTimeout(fn, 10)` calls in under 10 ms (shortest
    9.165 ms). Browsers clamp nested timeouts to at least 4 ms. Linux
    relative sleeps follow a monotonic clock that excludes suspend, and
    absolute `CLOCK_REALTIME` sleeps move with wall-clock changes.
    `CLOCK_MONOTONIC` is slewed, `CLOCK_MONOTONIC_RAW` is not. Guarantees
    differ: Go and Python document "at least", Java only timer precision,
    JS no strict minimum. Fake timers complete sleeps instantly (C25).
  - In code: elapsed time assumed equal to the requested sleep.
    `InterruptedException` swallowed, losing interrupt status. Rate
    limiters, retries, protocol timings, debounce windows, cooldowns, or
    safety interlocks relying on a sleep's exact or minimum length. Sleep
    loops used as clocks. Tests using sleeps to synchronize, or asserting
    `elapsed >= requested`.
  - Fix: re-read a monotonic clock after every sleep. Sleep until a
    deadline in a loop (compute remaining, sleep, repeat). Enforce minimum
    gaps with a clock check, measured on the clock the requirement uses.
    Restore Java interrupt status or stop the work. Use synchronization
    primitives, futures, or schedulers for coordination. Use hardware
    timers or real-time facilities for safety-critical delays. Use
    tolerances or fake clocks in timing tests.
  - Not a finding: sleeps for coarse pacing where no logic depends on the
    length.
  - Escalate: real-time, safety, or protocol timing without stated
    tolerances or minimum-delay guarantees.
- C18.5 Scheduling at a target time.
  - Facts: polling samples drift and skip seconds; timers are delayed or
    paused; clocks step past or back over targets; local targets fall in
    DST gaps or repeat in overlaps (C11.6); leap seconds and smears affect
    the target second. Schedulers differ: Vixie and ISC cron run jobs
    skipped by clock changes under 3 hours right after the change and run
    repeated jobs once. Forward clock jumps trigger catch-up (C15.2).
    Host-zone and UTC schedules move against local time (C9.2, C11.5).
  - In code: `while now().strftime("%H:%M:%S") != "09:00:00": sleep(1)`
    or `if now.minute == 0 and now.second == 0`. Hand-written schedulers
    with `setInterval` and equality. No record of fired occurrences, so
    repeats fire twice. No missed-run policy, or catch-up running every
    missed occurrence (job storms, duplicate billing).
  - Fix: compute each occurrence's target instant in its zone with a
    stated gap and overlap rule. Fire when `now >= target` and the
    occurrence has not fired, recording each run so it happens once. Sleep
    until the target and re-check on wake. Define a missed-run policy (run
    once late, skip, or coalesce) and bound catch-up. Prefer an
    established scheduler with an explicit zone and missed-run handling,
    and verify its DST behavior (new dependencies need approval).
  - Not a finding: `>=` polling with a recorded fired state.
  - Escalate: jobs at local times inside gaps or overlaps without a stated
    skip, once, or twice rule.
- C18.6 Deliberate timer interference.
  - Facts: platforms delay timers on purpose (browser throttling and
    clamps, coarsened `performance.now()`, macOS App Nap, Windows power
    throttling, Linux timer slack, Android Doze and App Standby, which
    limited idle-allowed alarms to about once per nine minutes per app,
    iOS suspension, serverless freezing). Services slow responses on
    purpose (rate limiting, `Retry-After`, tarpitting, backoff jitter).
    Security code adds or removes timing (constant-time comparisons,
    random delays). Tools fake time (fake timers, `libfaketime`,
    debuggers). Users accelerate time (speed hacks). Malware sleeps to
    outlast sandboxes and sandboxes accelerate sleeps (MITRE ATT&CK
    T1497.003).
  - In code: correctness or security relying on client timers firing on
    time. Mobile reminders, payments, or alarms on timers the OS can defer.
    Fake-timer setup in shared code that can load in production (C25).
    Sleeps delaying security-relevant actions on the assumption nobody can
    skip them.
  - Fix: enforce time-dependent rules on the server. On mobile, use
    platform APIs for exact or user-visible alarms within platform rules,
    and recheck the clock when work runs. Keep fake timers out of
    production builds. Design for late, skipped, and accelerated timers,
    and make actions idempotent.
  - Not a finding: client timers for user experience only, with server
    enforcement.
  - Escalate: time-critical mobile or embedded features without stated
    timing guarantees.
- Proposed severity (for the user to decide), per check: HIGH when a
  pause can break lock or lease safety and let two writers corrupt data
  (user decision: not a CRITICAL exception). HIGH also when billing,
  quotas, safety timeouts, control loops, rate limits,
  protocol timing, interlocks, client-side game, exam, or billing
  outcomes, expiry, authorization, or financial, legal, or safety jobs on
  a core path rely on wall-clock or tick-counted durations, exact or
  minimum sleeps, swallowed interrupts, stale "now", overflowed timers,
  equality polling, or timers that can be deliberately delayed,
  skipped, or accelerated. MEDIUM for retries, backoff, debounce,
  watchdogs, simulations, caches, metrics, reports, reminders, ETAs, and
  maintenance tasks. LOW for test-only code.

Point ledger for C18:
- Inbound from PA-11: wall-clock durations, timeouts, retries, rate
  limits, wall-clock API list, monotonic fix -> C18.1.
- Inbound from PA-12: catch-up schedulers and bounded catch-up -> C18.5.
- Inbound from PA-13: monotonic clocks for leases -> C18.3.
- Inbound from PA-20: suspend behavior of monotonic clocks, wrong
  monotonic clock, `CLOCK_BOOTTIME` fix -> C18.1. Throttled timers, tick
  counting, tick fix -> C18.2.
- Inbound from PA-119: fixed `dt` per frame -> C18.2.
- Inbound from PA-120: fixed step with accumulator -> C18.2.
- Inbound from C9.2: scheduler zone -> C18.5.
- Inbound from C11.5: zoned scheduler for local-time schedules -> C18.5.
- Inbound from C11.6: jobs inside gaps and overlaps -> C18.5.
- Inbound from C15.4: monotonic tracking of relative expiries -> C18.1.
- Inbound from C17.3: monotonic durations -> C18.1.
- PA-21: slews and stopped clocks -> C18.1. Throttling, scaling, speed
  hacks, hardware, timers assumed on time, fixed `dt`, client timing,
  measured-time fixes, server timing fix, not-a-findings -> C18.2.
  Process pauses, leases and Redlock, heartbeats, fencing and pause
  detection fixes, lease escalation -> C18.3. Real-sleep tests -> C18.4
  with C25. Severity -> C18 severity.
- PA-22: all suspension, snapshot, serverless, long-job facts, stale
  "now", check-then-act, "today" in long jobs, TTL caches, overflow
  examples, division guard, all fixes, not-a-finding, escalation ->
  C18.3. Tick-counter wrap comparison -> C19 by reference. Severity ->
  C18 severity.
- PA-54: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C18.5. Severity -> C18 severity.
- PA-55: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C18.1. Severity -> C18 severity.
- PA-62: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C18.4. Sleep loops as schedulers -> C18.5 by reference.
  Severity -> C18 severity.
- PA-63: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C18.4. Severity -> C18 severity.
- PA-117: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C18.6. Fake timers in production -> C18.6 with C25.
  Severity -> C18 severity.
