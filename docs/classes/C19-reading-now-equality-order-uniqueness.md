# C19 Reading "now": equality, order, uniqueness

(sources: PA-30, 53, 60, 65, 68, 105, 106, 107; inbound from PA-11,
PA-12, PA-14, PA-22, C15.6, C16.3, C16.5, C17.3) Approved by the user.

Scope: what consecutive clock reads return, whether time read by code
only moves forward, ordering stored or cross-system timestamps, and
timestamps used as identifiers or tokens. Elapsed-time measurement is
C18. Precision of storage and transport is C20. What event a timestamp
records is C8.1.

- C19.1 Consecutive reads: equal or different.
  - Facts (verified, host-dependent): in a tight loop about 49 of
    1,000,000 back-to-back JS `Date.now()` pairs differed, and 100,000
    calls returned only 23 distinct values; about 21% of Python
    `datetime.now()` pairs differed. Preemption, GC, or I/O make the gap
    arbitrary (C18.3). The clock can step between reads (C15.1). App and
    database clocks differ, and Postgres `now()` is fixed for the
    transaction. JS `new Date(0) == new Date(0)` is `false` (reference
    comparison). Change markers are coarse: HTTP `Last-Modified` carries
    whole seconds; file mtimes step 2 s on FAT, 1 s on ext3 and HFS+,
    finer on ext4 and NTFS.
  - In code: date and time components from separate reads (`date =
    today()` then `time = now().time()`), a day or year off at midnight
    or New Year (also composition, C7.4). Start and end of one operation
    read separately. Tests asserting two `now()` calls equal. Cache keys,
    IDs, or partitions from separate reads in one request. JS `==` or
    `===` on Date objects. Loops waiting for "now" to change. Assertions
    that elapsed time is above zero. `updated_at = now()` as a change
    signal. Caching, builds, or sync by `Last-Modified` or mtime alone.
  - Fix: read the clock once per operation and derive every component
    from that value (C25). Compare values (`getTime()`, library
    equality). Where two reads are intended, compare with a tolerance and
    handle the second being earlier. Use sequence, counter, or version
    numbers to guarantee change or distinctness. Use ETags from content
    hashes or versions, and content hashes for build and sync detection.
  - Not a finding: separate monotonic reads used only to measure elapsed
    time. Timestamps kept for information, with versions or hashes for
    change detection.
- C19.2 Reads are not strictly increasing, and monotonic has a scope.
  - Facts: "monotonic" means non-decreasing. Python documents
    `time.monotonic()` as unable to go backward, and Java documents
    `System.nanoTime()` only for differences. 200,000 consecutive pairs of
    Python `monotonic_ns()` and Node `performance.now()` were all strictly
    increasing here (verified), which no platform guarantees. Monotonic
    clocks restart at boot (`CLOCK_MONOTONIC`), have an arbitrary origin
    per JVM (`nanoTime`), an undefined reference (Python), or count from
    each page's `timeOrigin` (`performance.now()`). Per-core counters
    disagreed on some older systems (C18.2), and hosts have separate
    clocks. Unix time can repeat at a leap second (C17.3).
  - In code: `assert t2 > t1`. Versions, sequence numbers, or
    event-sourcing positions taken directly from the clock. `>` on
    timestamps for deduplication or progress. Monotonic readings stored,
    sent between hosts, or compared across restarts.
  - Fix: compare monotonic reads with `>=` and handle equality. Where
    strictly increasing values are needed, generate `next = max(now, last
    + 1 unit)`, persist `last` across restarts, and lock in concurrent
    code. Use monotonic clocks only for in-process durations. Use
    sequences or log offsets for order.
  - Not a finding: non-strict monotonic comparisons with equal values
    handled.
- C19.3 Time read by code moves backward.
  - Facts: wall clocks step back, VMs restore, leap seconds repeat
    (C15, C17). Local wall time repeats an hour at fall-back and a day
    crossing the date line eastward. Operators, tests, and replays set
    "now" to the past (C25). Fixed-width counters wrap (32-bit ms after
    49.7 days; MPEG-TS stamps about every 26.5 hours, C16.5). Lagging
    replicas and caches show older state after newer. Runtimes react to
    negative durations differently (Python and Java raise, JS and Go
    return at once; C21), and unsigned subtraction wraps (Go
    `uint32(5) - uint32(10)` is 4294967291, verified).
  - In code: `now - last` without handling negatives (crashes, instant
    firing, huge unsigned values). Token buckets refilling by negative or
    underflowed amounts. Expiry extended when the clock moves back.
    Counter comparisons `now > deadline` that fail after a wrap (Java
    signed 32-bit example verified false while the wrap-safe
    `(now - deadline) > 0` is true). Guards that throw or drop data on `now <
    last_seen`. Negative `dt` in averages or physics. Reads routed to
    replicas right after a write.
  - Fix: measure durations with a monotonic clock (C18.1). Clamp negative
    elapsed values to zero and log them. Compare wrapping counters with
    wrap-safe arithmetic (subtract, test the signed result, as Linux
    `time_after` does). Define a policy for `now < last_seen` (accept and
    log, hold, or reject). Provide read-your-writes where users expect it.
  - Not a finding: monotonic durations with explicit handling of negative
    results.
  - Escalate: user-facing flows where stale replica reads after a write
    are possible and the required consistency is not stated.
- C19.4 Stored timestamps arrive out of order.
  - Facts: transactions commit out of timestamp order (Postgres `now()`
    is transaction start, so a long transaction commits later with an
    earlier stamp). Multiple writers, clients, and replicas stamp with
    their own clocks, and replication lag reorders arrival. Offline
    devices and queues deliver old events late. A far-future clock sets
    watermarks that later records never pass (C15.2).
  - In code: `ORDER BY created_at` taken as insertion order. Incremental
    sync or ETL with `WHERE updated_at > :watermark`, skipping late
    commits forever. Validations requiring each new timestamp to exceed
    the last. Time-series stores rejecting out-of-order samples
    (Prometheus by default, with an out-of-order window since 2.39). Local
    naive log stamps going backward each autumn.
  - Fix: use sequences, log offsets, or commit positions (LSN, change data
    capture) for order and cursors. If timestamp watermarks remain,
    re-read with an overlap margin longer than the longest transaction and
    deduplicate. Store UTC instants. Design pipelines for late data
    (buffering, event-time windows with allowed lateness, out-of-order
    ingestion).
  - Not a finding: timestamp ordering for display with sequence-based
    cursors behind it.
  - Escalate: sync or audit completeness that depends on timestamp order
    where maximum transaction length or lateness is not stated.
- C19.5 Timestamps as identifiers and tokens.
  - Facts: precision is not resolution (C19.7). Threads, cores,
    processes, and hosts read the same tick. Clocks repeat values
    (backward steps, VM restores, DST overlap in local time, leap
    seconds). Precision is lost downstream. Postgres `now()` gives every
    row in a transaction the same value (`clock_timestamp()` does not).
    At volume, collisions follow from probability. Clocks set far ahead
    produce IDs that sort after all later ones (C15.2).
  - In code: timestamps as primary keys, file or object names, temp
    directories, lock names, message IDs, or idempotency keys. Upserts or
    `ON CONFLICT ... DO UPDATE` keyed on a timestamp, silently
    overwriting. Password-reset tokens, session IDs, or nonces from
    timestamps, or random generators seeded with the time. Snowflake-style
    or UUIDv7 generators with no handling for a clock that moves back.
  - Fix: use real unique identifiers (sequences, UUIDv4, or UUIDv7 with
    random or counter bits per RFC 9562). For time-ordered IDs, combine
    timestamp, node ID, and counter, and make generators detect backward
    jumps and wait or fail. Generate security tokens with a
    cryptographically secure random generator. Make unique-key conflicts
    fail or retry, never silently overwrite.
  - Not a finding: timestamps as non-unique attributes. Composite keys
    pairing a timestamp with a unique discriminator.
  - Escalate: deduplication keyed on timestamps where the rule for two
    genuinely distinct simultaneous events is not stated.
- C19.6 Ordering events across systems.
  - Facts: clocks on different systems disagree (C15), so ordering their
    stamps orders clock readings, not events. Lamport (1978) shows only a
    partial order (happened-before) is grounded in causality, and any
    total order adds arbitrary tie-breaking. Google Spanner's TrueTime
    returns an interval and commit-waits to keep an external order, valid
    only inside Spanner. Ties, mixed precision, scales, leap-second
    repeats, and smearing break ordering. Stamps may record different
    moments (C8.1). Distant simultaneity is relative (space domains only,
    C16.2).
  - In code: logs, events, or audit trails from several services merged
    by timestamp to reconstruct cause and effect. Last-write-wins across
    replicas or devices on client or replica clocks, so a fast clock
    overwrites newer data. Traces with children starting before parents.
    Streams exported with a timestamp-based global order. Cross-shard
    timestamp-plus-ID order presented as true order. Long-absent peers
    merged by timestamp (C15.6).
  - Fix: get total order within a system from one authority (sequence,
    single-partition log offset, consensus log). Track causality with
    logical, vector, or hybrid logical clocks (as CockroachDB does), trace
    parent IDs, or version vectors. Treat cross-system timestamps as
    approximate with stated uncertainty. Publish order guarantees
    precisely (per key or partition) and give consumers sequence IDs.
    Resolve conflicts with version vectors or domain rules.
  - Not a finding: timestamp order for approximate display only.
  - Escalate: audit, financial, or legal processes requiring provable
    cross-system order where mechanism and tolerance are not stated.
- C19.7 Type precision versus clock resolution.
  - Facts (verified, host-dependent): Python reports `time.time()`
    resolution as 1e-09 s but returns a float64 spaced about 2.4e-07 s
    near today, while `time_ns()` keeps nanoseconds. Java `Instant.now()`
    had sub-microsecond digits in 997 of 1,000 reads here, but other
    platforms and JDKs give micro- or milliseconds. Types finer than the
    clock repeat or zero-fill trailing digits (Windows 15.6 ms ticks,
    coarsened browser timers). `clock_getres` and `get_clock_info` are
    claims, not guarantees. Accuracy is separate again (C15). MySQL
    `NOW()` returns whole seconds unless `NOW(6)`.
  - In code: nanosecond fields treated as nanosecond-accurate. Current
    time stored as float seconds expecting sub-microsecond detail.
    Uniqueness or order relying on trailing digits. Events shorter than
    the clock's resolution measured as zero (C20).
  - Fix: use integer nanosecond APIs where precision matters
    (`time_ns()`, `perf_counter_ns()`, `nanoTime()` for durations).
    Measure effective resolution on the target platform and record it.
    Document precision, resolution, and accuracy separately for regulated
    timestamps.
  - Not a finding: values whose documented precision matches the measured
    clock and storage type.
  - Escalate: audit or trading timestamps without stated precision and
    accuracy.
- Proposed severity (for the user to decide), per check: CRITICAL when
  time-derived values serve as security tokens, session IDs, or nonces.
  HIGH when separate reads produce off-by-one-period stored values;
  missed changes serve stale data or skip builds or sync; backward time
  crashes, disables rate limits, or extends expiry; watermarks skip or
  drop records; collisions overwrite records; versioning, ordering,
  conflict resolution, audit trails, or financial event order on a core
  path rely on clock reads; or precision assumptions break uniqueness or
  regulated timestamps. MEDIUM for flaky tests, logs, traces, metrics,
  temp files, caches, stale reads, and analytics. LOW for test-only code.

Point ledger for C19:
- Inbound from PA-11: ID generators reading the clock, backward-jump
  detection fix -> C19.5.
- Inbound from PA-12: sync cursors and watermarks from a far-future
  clock -> C19.4. Far-future time-based IDs -> C19.5.
- Inbound from PA-14: last-write-wins on client timestamps -> C19.6.
- Inbound from PA-22: tick-counter wrap comparison -> C19.3.
- Inbound from C15.6: version vectors for long-absent peers -> C19.6.
- Inbound from C16.3: monotonic restart at reboot -> C19.2.
- Inbound from C16.5: timestamp wraparound -> C19.3.
- Inbound from C17.3: Unix time assumed strictly increasing -> C19.2.
- PA-30: all facts, code patterns, checks, fixes, not-a-findings,
  escalation -> C19.5. Severity -> C19 severity.
- PA-53: all facts, code patterns, checks, fixes, not-a-finding -> C19.1.
  Components from separate reads -> C19.1 with C7.4. Read-once fix ->
  C19.1 with C25. Severity -> C19 severity.
- PA-60: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C19.6. Severity -> C19 severity.
- PA-65: causes of out-of-order stored stamps, `ORDER BY`, watermarks,
  validations, time-series rejection, local logs, sequence fix, overlap
  fix, UTC fix, late-data fix, not-a-finding, escalation -> C19.4.
  Monotonic scope and persistence of monotonic readings -> C19.2.
  Severity -> C19 severity.
- PA-68: all facts, runtime reactions, code patterns, checks, fixes,
  not-a-finding, escalation -> C19.3. Negative sleeps -> C21 by
  reference. Severity -> C19 severity.
- PA-105: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C19.7. Sub-resolution durations -> C20 by reference.
  Severity -> C19 severity.
- PA-106: all facts, code patterns, checks, fixes, not-a-finding ->
  C19.1. ID collisions -> C19.5. Zero elapsed -> C19.3 and C18.3.
  Severity -> C19 severity.
- PA-107: all facts, code patterns, checks, fixes, not-a-finding ->
  C19.2. Last-write-wins -> C19.6. Severity -> C19 severity.
