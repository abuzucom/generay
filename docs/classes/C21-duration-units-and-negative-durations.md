# C21 Duration units and negative durations

(sources: PA-114, 115; inbound from PA-64, C19.3) Approved by the user.

Scope: the unit of a numeric duration, decimal-hour versus clock-style
durations, and what negative or zero durations mean. Duration string
grammars are C23. Elapsed versus calendar meaning is C7.1.

- C21.1 Units of numeric durations.
  - Facts: units differ, often within one stack. Milliseconds: JS
    `setTimeout`, Java `Thread.sleep`, many client timeouts, Redis
    `PEXPIRE`, Kafka `.ms` settings, Postgres `statement_timeout` without
    a unit. Seconds: Python `time.sleep`, `Cache-Control: max-age`,
    `Retry-After` (or an HTTP date), cookie `Max-Age`, JWT claims, Redis
    `EXPIRE`, MySQL `wait_timeout`, Kubernetes probes. Microseconds: POSIX
    `usleep`. Nanoseconds: Go `time.Duration`, where the integer 30 is
    `30ns` and `30 * time.Second` is `30s` (verified), so
    `time.Sleep(timeout)` with a bare integer sleeps nanoseconds. 100 ns
    ticks: .NET `new TimeSpan(10)` is one microsecond. Minutes, hours, or
    days: cron, certificate validity, password expiry. Platform units:
    jiffies, frames, samples.
  - In code: unitless config keys (`timeout = 30`) read with another
    unit. Milliseconds to a seconds API (1,000 times too long) or the
    reverse. Go durations from bare integers. JSON durations with no unit
    in name or schema.
  - Fix: use typed durations inside code (Go `time.Duration` with unit
    constants, Java `Duration`, Python `timedelta`, .NET
    `TimeSpan.FromSeconds`). Put units in names (`timeout_ms`) or suffixes
    (`30s`), and validate plausible ranges so 1,000-fold errors fail fast.
    Use ISO 8601 durations or documented units at interfaces (C23).
  - Not a finding: durations whose unit is in the name, schema, or type
    and matches the consumer.
  - Escalate: interfaces exchanging numeric durations with no documented
    unit.
- C21.2 Decimal hours versus clock-style durations.
  - Facts: timesheets and payroll often record decimal hours: 1.30 hours
    is 1 hour 18 minutes, not 1 hour 30 minutes.
  - In code: decimal hours and `h:mm` values mixed in calculations or
    displays.
  - Fix: store durations in one unit and convert decimal hours explicitly
    at the edges, with labels.
  - Escalate: payroll or billing inputs whose duration format (decimal
    hours or `h:mm`) is not stated.
- C21.3 Negative and zero durations.
  - Facts: meanings differ. Wait forever: `poll()` and `epoll_wait()`
    with -1, Kafka `retention.ms = -1` (unlimited), Windows `INFINITE`
    (`0xFFFFFFFF`, -1 as signed 32-bit). Status codes: Redis `TTL` -1 (no
    expiry) and -2 (missing key). Already expired: cookie `Max-Age` of
    zero or less (RFC 6265), Go `context.WithTimeout` with a negative
    duration. Do it now: JS `setTimeout(fn, -1000)`, Go `time.Sleep`
    negative. Error: Python `time.sleep(-1)` raises `ValueError`, Java
    `Thread.sleep(-1)` throws. Invalid, so stale: HTTP caches and invalid
    `max-age`. Earlier: negative deltas in arithmetic. Unsigned wrap: -1
    in an unsigned 32-bit ms field is 4,294,967,295 ms, about 49.7 days.
    Representations differ (verified): Python `timedelta(seconds=-1)` is
    stored as `days=-1, seconds=86399` and prints `-1 day, 23:59:59`, while
    `total_seconds()` is -1.0; Java `Duration.ofMillis(-1500)` prints
    `PT-1.5S` but stores `getSeconds() = -2`, `getNano() = 500000000`.
  - In code: -1 or 0 passed as "no timeout" where it means "expire now", or
    the reverse. Sentinels such as -1 for "unset" in duration fields later
    used in arithmetic. Negative durations from clock differences passed to
    sleeps, timers, or expiries unchecked (C19.3). Fields of `timedelta`
    or `Duration` read individually.
  - Fix: represent "no limit" and "unset" explicitly (nullable fields,
    optional types, named constants). Validate durations at boundaries and
    reject or clamp negatives by a stated rule. Read totals
    (`total_seconds()`, `toMillis()`). Document what negative and zero mean
    in each owned interface.
  - Not a finding: documented sentinels used only with the API that
    defines them.
  - Escalate: configuration or interfaces accepting negative or zero
    durations without documented meaning.
- Proposed severity (for the user to decide), per check: HIGH when unit
  errors set timeouts, expiries, rate limits, or retention off by factors
  of 1,000 or more; decimal-hour confusion changes pay or charges; or a
  negative or zero duration disables expiry, retention limits, or
  timeouts, or expires data immediately, on a core path. MEDIUM for
  metrics, logs, and configuration validation. LOW for test-only code.

Point ledger for C21:
- Inbound from PA-64: decimal hours versus `h:mm`, one-unit fix, payroll
  format escalation -> C21.2. Severity -> C21 severity.
- Inbound from C19.3: runtime reactions to negative durations -> C21.3.
- PA-114: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C21.1. Severity -> C21 severity.
- PA-115: all facts, representations, code patterns, checks, fixes,
  not-a-finding, escalation -> C21.3. Severity -> C21 severity.
