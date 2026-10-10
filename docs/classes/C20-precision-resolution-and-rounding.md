# C20 Precision, resolution, and rounding

(sources: PA-23, 24, 29, 81, 82; inbound from C3.6, C7.5, C17.4, C19.7) Approved by the user.

Scope: the unit and precision of time values at every boundary,
precision lost or mixed between layers, floating-point epochs, and how
precision is reduced. Clock resolution versus type precision is C19.7.
Duration units are C21. Parsing fractional seconds is C23. Display
precision is C24.

- C20.1 Units of numeric timestamps.
  - Facts: platforms use seconds (Unix, JWT), milliseconds (JS `Date`,
    Java `currentTimeMillis`), microseconds (Python, Postgres, MySQL
    `DATETIME(6)`), 100 ns ticks (.NET), or nanoseconds (Go, Java
    `Instant`, Linux `timespec`). Bare numbers do not say which (verified):
    JS `new Date(1782900000)` is 1970-01-21; Python
    `datetime.fromtimestamp(ms)` raises "year 58467 is out of range".
  - In code: seconds passed where milliseconds are expected or the
    reverse, in API fields, columns, JWT claims, and config.
  - Fix: put the unit in names (`created_at_ms`) or use typed instants
    (`Instant`, `time.Time`). Document the unit and epoch of every numeric
    field (C17.4). Detection by magnitude is C23.
  - Not a finding: numeric fields whose unit is in the name, schema, or
    type and matches the consumer.
- C20.2 Precision lost between layers.
  - Facts: sources finer than milliseconds (Postgres, Python, BigQuery,
    Spark at us; Go, Java, Linux, Protobuf, pandas at ns; Parquet in ms,
    us, or ns) pass through millisecond-only sinks (JS `Date`,
    `java.util.Date`, BSON dates, Kafka record timestamps, Elasticsearch
    `date` versus `date_nanos`). MySQL `DATETIME` and `TIMESTAMP` default
    to whole seconds and round by default, so 23:59:59.6 is stored as the
    next day. Many events fall in one second or millisecond, and many
    operations take under a millisecond.
  - In code: values truncated through a millisecond layer and compared
    with the original, so optimistic-concurrency checks from a JS client
    always fail against a microsecond column. Second-level or
    millisecond-level ties making "latest" ambiguous, and keyset
    pagination without a tie-breaker skipping or repeating rows. Durations
    under a millisecond recorded as 0, skewing latency metrics and rates.
    Millisecond ID generators without a counter or with one that
    overflows (C19.5).
  - Fix: choose and document each field's precision end to end, with
    types that hold it (`DATETIME(6)`, `timestamptz`, 64-bit integers).
    Where a millisecond layer is unavoidable, truncate at the source and
    compare at that precision everywhere. Use version numbers, not
    timestamps, for optimistic concurrency. Add tie-breakers to ordering
    and pagination. Set MySQL `TIME_TRUNCATE_FRACTIONAL` or truncate
    before writing. Measure short durations with high-resolution
    monotonic clocks and record them in us or ns.
  - Not a finding: a documented precision that every layer agrees on.
  - Escalate: audit, legal, trading, telemetry, or event-sourcing records
    without a stated precision.
- C20.3 Mixed precision in one field.
  - Facts: different write paths truncate differently. A column widened
    to `DATETIME(6)` leaves old rows at whole seconds. Platform upgrades
    change precision (Java 9 raised `Instant.now()` beyond ms on common
    platforms). Devices, partners, and logs report different units.
    Dates, months, years, and approximate values ("sometime in 2019") sit
    beside full timestamps. A midnight timestamp that means a date, or a
    millisecond value from a 15.6 ms clock, claims precision it lacks.
  - In code: equality and deduplication failing between truncated and
    full copies. Closed bounds at whole seconds (`ts <= '... 23:59:59'`)
    missing 23:59:59.5 (C3.6). Truncated values sorting before the same
    moment at full precision. Negative durations from mixed endpoints
    (09:00:00.900 to a truncated 09:00:00 gives -0.9 s). Sync cursors
    with a truncated `last_seen`. Dates coerced to midnight compared with
    full timestamps. Cache or idempotency keys from strings of different
    precision. Coarse sources piling up at `.000`.
  - Fix: declare each field's precision and normalize on write. Keep
    coarse values in their own types or store their granularity. Compare
    at an explicit common precision, normally the coarser. Use half-open
    ranges (C3.6). Add tie-breakers, and use sequences or `>=` with
    deduplication for cursors (C19.4). Clamp cross-source durations at
    zero and log negatives as data errors.
  - Not a finding: one precision enforced on every write path.
  - Escalate: datasets mixing granularities (historical, medical) without
    stated comparison rules.
- C20.4 Floating-point epochs.
  - Facts (verified): float32 epoch seconds near 1.78e9 are spaced 128 s
    apart. float64 seconds lose sub-microsecond detail. Nanosecond epochs
    in JSON exceed 2^53 and lose precision as JS numbers.
  - In code: epochs in float columns or variables. High-precision epochs
    sent as JSON numbers.
  - Fix: store integer epochs with a named unit. Send high-precision
    values as RFC 3339 strings or integer strings.
- C20.5 Reducing precision: truncation and rounding.
  - Facts (verified): truncation toward zero is wrong for negative
    epochs: -1500 ms is 23:59:58.500 on 1969-12-31, but JS `Math.trunc`,
    Java `-1500 / 1000`, and Python `int(-1.5)` give 23:59:59, while
    flooring (`Math.floor`, `Instant.getEpochSecond()` = -2,
    `math.floor`) is right. The fraction of a negative value is easy to
    get wrong: JS `-1600 % 1000` is -600, so "below 500" logic truncates
    toward zero. Rounding moves values up to half a unit, and .5 and above
    round into the next second, day, month, or year. Half-way rules differ:
    JS and Java `Math.round(-1.5)` is -1 and `Math.round(2.5)` is 3, Java
    `Math.rint(2.5)` is 2.0, Python `round(-1.5)` is -2 and `round(2.5)`
    is 2 (half to even). Floating-point conversions land just above or
    below .5. Boundaries flip: 17:00:00.900 truncated passes a `<=
    17:00:00` deadline it missed, 17:00:00.400 rounded also passes, and
    16:59:59.600 rounded fails one it met. Per-item truncation biases
    totals down and rounding up biases them up, by up to a unit per item.
  - In code: `ms / 1000` with integer division, `Math.trunc`, or `int()`
    on possibly negative epochs. Fractions via `%`. Language-default
    `round()` with an unknown half-way rule. Deadline or cutoff checks
    after reducing precision. Per-item rounding before summing for billing
    or usage. Epochs rounded through floating point. Reduced values used
    as keys or for ordering.
  - Fix: floor for epoch conversions (`Math.floorDiv`, `Math.floor`,
    `Instant.getEpochSecond()`, Java `truncatedTo`) and floor modulo for
    fractions (C7.7). Choose rounding mode from the requirement and apply
    it with exact integer or decimal arithmetic (Java `BigDecimal` with
    `RoundingMode`, Python `decimal`). Compare deadlines and cutoffs at
    full precision, then reduce for storage or display. Sum at full
    precision and round once. Keep a tie-breaker where reduced values key
    or order records.
  - Not a finding: truncating or rounding non-negative values for
    display or logs only, with comparisons at full precision.
  - Escalate: billing, metering, or deadline rules without a stated
    rounding rule (per item or total; up, down, nearest, or half-even).
- Proposed severity (for the user to decide), per check: HIGH for unit
  confusion on core paths; truncation that breaks concurrency checks,
  deduplication, or ID uniqueness; pagination or cursors that skip or
  repeat records; rounding that moves values into the next day or period;
  and reduced precision that changes deadline outcomes, billing totals,
  pre-1970 values, or durations on a core path. MEDIUM for ordering
  ambiguity in logs, latency metrics, analytics, and reports. LOW for
  test-only code.

Point ledger for C20:
- Inbound from C3.6: values rounding into the next day -> C20.2 and
  C20.5.
- Inbound from C7.5: adequate precision for differences -> C20.3.
- Inbound from C17.4: unit of epoch values -> C20.1.
- Inbound from C19.7: durations shorter than resolution -> C20.2.
- PA-23: platform units, unit-confusion examples, unit-in-name fix,
  typed values -> C20.1. Events per second, wire fractions, MySQL
  rounding, ordering and pagination ties, round-trip loss,
  precision-choice fix, tie-breaker fix, truncation fix, common-precision
  fix, not-a-finding, escalation -> C20.2. Float epochs and JSON fix ->
  C20.4. IDs and file names from second timestamps -> C19.5. Durations
  read as zero used as divisor -> C18.3. Severity -> C20 severity.
- PA-24: sub-ms sources, ms sinks, sub-ms operations, truncated round
  trips, concurrency checks, sub-ms durations as zero, ties, layer and
  equality checks, end-to-end precision fix, version-number fix,
  high-resolution measurement, not-a-finding, escalation -> C20.2.
  Coarse clocks and coarsened `performance.now()` -> C19.7. Parsers
  dropping or misreading fractions (JS, `SimpleDateFormat` `SSS`),
  ISO-parser fix -> C23 (inbound). Per-millisecond ID counters, RFC 9562
  fix -> C19.5. Severity -> C20 severity.
- PA-29: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C20.3. Severity -> C20 severity.
- PA-81: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C20.5. Collisions after reduction -> C20.5 with C19.5.
  Severity -> C20 severity.
- PA-82: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C20.5. Severity -> C20 severity.
