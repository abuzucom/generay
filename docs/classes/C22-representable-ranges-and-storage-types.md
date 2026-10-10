# C22 Representable ranges and storage types

(sources: PA-18, 72, 76, 80, 132; inbound from PA-19, C8, C9.3, C17.4) Approved by the user.

Scope: the range each type, library, format, and store can represent,
valid year numbers, sentinels and special values, epochs of different
platforms, year width in strings, and what "timestamp" means in each
database and file format. Year numbering schemes and eras are C6.5.
Parsing is C23. Display is C24.

- C22.1 Range limits of types, libraries, and formats.
  - Facts (verified where marked): signed 32-bit Unix seconds run from
    1901-12-13 20:45:52 to 2038-01-19 03:14:07 UTC (verified), unsigned to
    2106. NTP 32-bit seconds since 1900 roll over on 2036-02-07 06:28:16
    UTC (verified). MySQL `TIMESTAMP`: 1970-01-01 00:00:01 to 2038-01-19;
    MySQL `DATE`/`DATETIME`: 1000 to 9999. SQL Server `datetime` from
    1753, `date` 0001 to 9999. .NET `DateTime` and Python `datetime`: 1 to
    9999 (`datetime(9999,12,31) + timedelta(days=1)` raises
    OverflowError, verified). JS `Date`: +/-8.64e15 ms, up to
    +275760-09-13, then `NaN` (verified). Postgres: 4713 BC to 294276 AD.
    Java `java.time`: about +/-1 billion years. Go formats -0044 and 12026
    but `MarshalJSON` fails outside 0 to 9999 (verified). C `struct tm`
    stores years from 1900, and `strftime` for negative years is
    implementation-defined. pandas nanosecond timestamps cover 1677-09-21
    to 2262-04-11 (documented; not verified here). FAT 1980 to 2107, HFS+
    1904 to 2040, FILETIME from 1601, Excel nothing before its epoch.
    RFC 3339 and JSON Schema `date-time` allow 0000 to 9999, Protobuf
    `Timestamp` 0001 to 9999, BigQuery `DATE` 0001 to 9999. Some platforms
    reject negative epochs (Microsoft C runtime `localtime`). Real dates
    already reach past 2038 (mortgages, pensions, certificates,
    retention), and clocks reach extremes by accident and on purpose
    (C15.2). One layer accepting a value says nothing about the next.
  - In code: 32-bit epoch fields or columns, including binary protocols,
    file formats, and firmware. MySQL `TIMESTAMP` for values past 2038.
    `now + duration` near a range end raising or wrapping. Historical,
    astronomical, geological, or far-future data passed through types that
    cannot hold it. Serialization failing only for out-of-range values in
    production (Go JSON, Protobuf, BigQuery). Data frames converting or
    failing outside pandas' range. Pre-1970 values rejected or mishandled.
  - Fix: use 64-bit epochs and wide database types. Establish the domain
    range and verify every layer supports it, or validate at input. Use
    wide-range types where needed (`java.time`, Astropy `Time`), or store
    deep-time values as numeric years with a named reference. Choose
    coarser units in data libraries when range matters more. Test "now"
    and arithmetic at 1970, 2036-02-07, 2038-01-19, year 9999, and the
    domain's extremes, including serialization.
  - Not a finding: a documented, validated domain range narrower than
    every layer's range (birth dates after 1900, enforced at input).
  - Escalate: long-lived values (loans, pensions, certificates, archival
    retention) or scientific and long-horizon data whose full storage and
    transport path or required range cannot be established.
- C22.2 Valid year numbers.
  - Facts (verified where marked): historical numbering has no year 0
    (Python `date(0, 1, 1)` raises), astronomical numbering does (C6.5).
    Era calendars start at 1 and have bounds: Java `JapaneseDate` rejects
    dates before Meiji 6 (1873), and `HijrahChronology` (Umm al-Qura)
    supports only 1300 to 1600 AH (verified). Gregorian years before 1582
    are proleptic. Java `Year` spans -999,999,999 to 999,999,999. ISO 8601
    allows expanded years only by agreement: Java `LocalDate.parse`
    accepts `-0044-03-15` and `+12026-01-01`, Python `fromisoformat`
    rejects `+12026-01-01` (verified). Two-digit years are not years until
    expanded (C23).
  - In code: year fields as unconstrained integers, rejected deep in the
    stack. Years accepted by one layer (Java, Postgres, JS) and rejected by
    another (Python, MySQL, .NET). Expanded or negative ISO years emitted
    by one service and rejected by consumers. Era or Hijri conversions
    crashing outside library ranges.
  - Fix: define each field's valid range from the domain and the narrowest
    layer, and validate at input. Check calendar-library ranges before
    converting. Agree on expanded-year formats with every consumer, or
    avoid them.
  - Not a finding: modern-date fields validated to a range every layer
    supports.
  - Escalate: historical, astronomical, or long-horizon data without a
    stated year range and numbering scheme.
- C22.3 Sentinels and special values.
  - Facts: sentinels such as `9999-12-31`, `MAX_DATE`, `0`, `0001-01-01`,
    or `1970-01-01` for "never" or "unset" overflow in arithmetic or
    collide with real values (an epoch-booted device's "now"). Postgres
    `infinity` and `-infinity` reach application code, where drivers map
    them to extreme values or raise. Loops over "unbounded" ranges run to
    the type's maximum.
  - In code: sentinel dates with arithmetic on them. Sentinels shown to
    users as dates (C24). `infinity` unhandled. Iteration without
    termination at a type limit.
  - Fix: use explicit nullable fields or flags for "never" and "unset".
    Where sentinels remain, saturate arithmetic instead of overflowing.
    Handle `infinity` explicitly or forbid it in the schema. Bound
    iteration.
- C22.4 Epochs differ between platforms.
  - Facts (verified offsets from Unix where marked): Unix and Java
    1970-01-01; NTP 1900-01-01; GPS 1980-01-06 (315,964,800 s, verified);
    Apple Cocoa reference date 2001-01-01 (978,307,200 s, verified);
    Windows FILETIME 1601-01-01; .NET ticks 0001-01-01; Excel 1899-12-30
    (1900 system, with the phantom day in C2.5) or 1904-01-01.
  - In code: values converted with the wrong epoch or a hand-typed
    constant: an Apple reference date read as Unix time is 31 years
    early; FILETIME misread as Unix is centuries off.
  - Fix: use library conversions with named epochs, not literal
    constants (BP-1). Name the epoch and unit of every numeric field
    (C20.1).
- C22.5 Year width in date strings.
  - Facts (verified): Java prints `+10000-01-01` and `-0044-03-15`; JS
    `toISOString()` uses a sign and six digits outside 0000 to 9999
    (`+010000-01-01T...Z`, `-000044-03-15T...Z`). Python
    `date(5,1,1).strftime('%Y-%m-%d')` gives `5-01-01` on glibc while
    `isoformat()` gives `0005-01-01`. Postgres shows `0044-03-15 BC` and
    five-digit years past 9999. Python `\d` matches Arabic-Indic digits
    for `str` patterns unless `re.ASCII`, while JS `\d` is ASCII only.
    `YYYY` is a week-based year in Java and other libraries (C24).
  - In code: regexes such as `^\d{4}-\d{2}-\d{2}$` rejecting valid
    expanded years or accepting non-ASCII digits in Python. Slicing by
    position (`s[0:4]`, `s[5:7]`). Fixed-width columns (`CHAR(10)`) and
    file layouts. `strftime('%Y')` for machine dates. Text sorting of
    signed or variable-width years (C23).
  - Fix: parse into typed values with a library and read fields from the
    value. Produce machine dates with ISO formatters (`isoformat()`,
    `toISOString()`, `java.time` `toString()`). Use ASCII digit classes
    (`[0-9]`, `re.ASCII`) and normalize native digits deliberately (C23).
    Decide whether expanded years are allowed and validate the range.
  - Not a finding: fixed four-digit patterns on fields documented as 1000
    to 9999 and produced by an ISO formatter.
  - Escalate: file formats or partner interfaces with fixed-width date
    fields where out-of-range years may occur.
- C22.6 "Timestamp" means different things by product.
  - Facts: SQL standard `TIMESTAMP` is without time zone. Postgres
    `timestamp` is zone-less and `timestamptz` stores an instant with no
    zone. MySQL `TIMESTAMP` converts through the session zone, covers 1970
    to 2038, and on older defaults the first such column auto-updates on
    every row change (`explicit_defaults_for_timestamp`, on by default
    since 8.0.2); `DATETIME` is zone-less. SQL Server `timestamp` is
    `rowversion`, a binary counter with no date or time. Oracle
    `TIMESTAMP` is zone-less, `WITH TIME ZONE` stores a region or offset,
    `WITH LOCAL TIME ZONE` normalizes to the database zone, and `DATE`
    holds a time to the second. SQLite has no date type: one `timestamp`
    column held text, an integer, and `not a date` side by side
    (verified), and `CURRENT_TIMESTAMP` returns UTC text. BigQuery
    `TIMESTAMP` is an instant and `DATETIME` zone-less. Snowflake maps
    `TIMESTAMP` to `TIMESTAMP_NTZ` by default through a setting. Spark
    `TIMESTAMP` acts as an instant in the session zone, with
    `TIMESTAMP_NTZ` added later. Parquet and Avro distinguish UTC-adjusted
    from local timestamps, and legacy Parquet `INT96` is read differently
    by engines. Drivers map types differently (JDBC uses the JVM zone,
    `psycopg` returns aware values for `timestamptz` and naive for
    `timestamp`) (C9.3).
  - In code: schemas or migrations ported by type name. SQL Server
    `timestamp` columns treated as dates. MySQL `TIMESTAMP` columns
    changing on unrelated updates (C8.1). Pipelines moving timestamps
    between warehouses, Parquet, and Avro without checking semantics.
    SQLite timestamp columns with mixed types.
  - Fix: choose types by semantics (instant types for instants,
    zone-less for local values, date types for dates; C8.2). Document each
    column's meaning and zone policy. Map types explicitly in migrations
    and pipelines and test round trips. In SQLite, store one documented
    representation (ISO 8601 UTC text, or integer epoch with unit) and
    enforce it with checks.
  - Not a finding: columns whose product-specific semantics are
    documented and match their use.
  - Escalate: migrations between products without mapped timestamp
    semantics.
- Proposed severity (for the user to decide), per check: HIGH when
  storage cannot represent values the system already writes (a 2050
  maturity in a MySQL `TIMESTAMP`; user decision: not a CRITICAL
  exception). HIGH also for 32-bit time on core paths,
  sentinel overflow, out-of-range or misnumbered years that crash or
  corrupt data, wrong epochs that corrupt stored records, string handling
  of years that corrupts or rejects stored dates, extreme years failing
  at a serialization boundary, and type-name assumptions that shift,
  corrupt, or misinterpret stored times or use a row version as a time.
  MEDIUM for parsers, display, historical conversions, analytics
  pipelines, validation gaps, and exports. LOW for test-only code.

Point ledger for C22:
- Inbound from PA-19: epoch list and Apple-as-Unix error, named-epoch
  fix -> C22.4. Postgres `infinity`, unbounded iteration -> C22.3.
  Historical data in narrow types, type-range fix -> C22.1. Stored-record
  severity -> C22 severity.
- Inbound from C8: database type semantics -> C22.6.
- Inbound from C9.3: driver type mappings -> C22.6.
- Inbound from C17.4: other platform epochs -> C22.4.
- PA-18: extremes by accident and on purpose, long-lived dates, range
  table, 32-bit fields, MySQL `TIMESTAMP`, range-end arithmetic,
  four-digit-year assumptions, pre-1970 handling, what to check, 64-bit
  fix, plausibility, boundary tests, not-a-finding, escalation -> C22.1.
  Sentinels and saturation fix -> C22.3. Severity -> C22 severity.
- PA-72: year 0, era bounds, proleptic years, Java `Year`, expanded
  forms, two-digit years, unconstrained fields, cross-layer acceptance,
  emitted expanded years, era crashes, range fix, library-range fix,
  agreement fix, not-a-finding, escalation -> C22.2. Type bounds ->
  C22.1. Year 0 numbering mix and scheme fix -> C6.5 by reference.
  Severity -> C22 severity.
- PA-76: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C22.5. `YYYY` meaning -> C24 by reference. Text sorting
  -> C23 by reference. Severity -> C22 severity.
- PA-80: language and library ranges, serialization limits, pipeline
  narrowest layer, all code patterns, checks, fixes, not-a-finding,
  escalation -> C22.1. Severity -> C22 severity.
- PA-132: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C22.6. Severity -> C22 severity.
