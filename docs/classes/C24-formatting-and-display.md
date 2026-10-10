# C24 Formatting and display

(sources: PA-32, 73, 74, 75, 85, 112; inbound from PA-3, PA-7, PA-19,
C2.5, C5.3, C6.1, C12.3, C22.3, C22.5) Approved by the user.

Scope: producing date and time text: display strings flowing back into
data, locale order, calendars and digits, displayed precision and year,
week-year tokens, formatting mechanics, and 12-hour clocks. Generay checks
all of this independently of adorno (separate repositories; overlap is
accepted, user decision). Parsing is C23.

- C24.1 Display strings are not data.
  - Facts: locale output varies by calendar, digits, marks, and
    precision, so display strings do not round-trip. Machine-facing
    exports in locale formats are misread downstream.
  - In code: locale-formatted dates written to storage, used as keys or
    file names, or parsed back. Edit forms that show a timestamp without
    seconds or fractions and save the shown value, rewriting the stored
    value on a no-change save and breaking optimistic-concurrency checks.
    Tests, reconciliations, or exports comparing displayed strings with
    stored values. Screen scraping, copy-paste, and CSV round trips.
    Exports, CSV, or APIs produced with `toLocaleDateString()` or the
    server locale.
  - Fix: ISO 8601 / RFC 3339 for storage and transport, locale formatting
    only at the display edge, and never parse display strings back. Submit
    unchanged fields with their original values or omit them. Compare
    typed values. Use full-precision machine formats for re-importable
    exports.
  - Not a finding: display-only formatting that never flows back.
- C24.2 Locale order, calendars, and digits in output.
  - Facts (Node `Intl`, verified): 2025-10-03 formats as `10/3/2025`
    (`en-US`), `03/10/2025` (`en-GB`), `3.10.2025` (`de-DE`), `2025. 10.
    03.` (`hu-HU`). ISO 8601 is clear to technical readers but unfamiliar
    to much of the public. Locale defaults select other calendars:
    `th-TH` shows Buddhist year 2568, `fa-IR` Solar Hijri 1404/7/11 in
    Persian digits; requested calendars show Japanese `R7/10/3` and Minguo
    year 114. `ar-EG` uses Arabic-Indic digits and inserts right-to-left
    marks (U+200F). Month and day names differ by language, and users type
    native digits.
  - In code: a Gregorian year assumed from locale output (2568 stored as
    Gregorian). Free-text input parsed with one assumed order (C23.3).
    ASCII-only parsers rejecting native digits, or lenient ones stripping
    marks and misreading fields. Locale formatters without a pinned
    calendar in machine-facing or cross-locale output.
  - Fix: request Gregorian and ASCII digits explicitly where required
    (`Intl` `calendar: "gregory"`, `numberingSystem: "latn"`; C6.1). Use
    structured inputs (pickers, separate fields). Normalize native digits
    in input deliberately. For cross-locale displays, include the month
    name (`3 Oct 2025`) or label ISO.
  - Not a finding: ISO 8601 shown to technical audiences. Labeled
    non-Gregorian displays that never flow back.
  - Escalate: multi-locale products without stated display and input
    formats, including calendar system.
- C24.3 Displayed precision and offsets.
  - Facts (verified): Python `strftime('%H:%M:%S')` and
    `isoformat(timespec='seconds')` show 09:00:59.6 as `09:00:59`, and
    rounding formatters show `09:01:00`. Storage may already have rounded
    (C20.2). Offset labels drop seconds: New York 1880 UTC 12:00:00
    displays as `07:03:58 GMT-0456` in JS and parses back to `11:59:58Z`
    (C12.3). Leap seconds display as 23:59:59 or 00:00:00 by library.
    GPS-time devices differ from UTC by 18 s. Client offset correction or
    smearing shifts displayed seconds. Many displays omit seconds or show
    relative times.
  - In code: users acting on a displayed time that differs from the
    enforced one (deadline shown 17:00, enforced at 16:59:59.5).
    Truncation and rounding mixed across formatters.
  - Fix: choose truncation or rounding deliberately and consistently.
    Enforce deadlines at the displayed boundary, or display the enforced
    one.
  - Escalate: deadline displays whose precision differs from enforcement
    without a stated intended boundary.
- C24.4 Displayed year differs from the stored year.
  - Facts (verified where marked): zone conversion near New Year
    (`2026-12-31T22:00Z` is `01/01/2027` in Moscow). Week-based year
    tokens: Java `YYYY` is week-year and follows the host locale (US
    locale prints 2026-12-31 as 2027-12-31), and `%Y-W%V` mixes calendar
    year with ISO week (2024-12-30 becomes `2024-W01` instead of
    `2025-W01`). Locale calendars differ greatly from Gregorian (for
    2025-10-03: Buddhist 2568, Persian 1404, Islamic Umm al-Qura 1447,
    Hebrew 5786, Japanese Reiwa 7, Minguo 114, Ethiopic 2018, Coptic 1742,
    Indian Saka 1947). Legacy accessors: JS `getYear()` and Java
    `Date.getYear()` return year minus 1900 (126), and "19" + it gives
    19126. Two-digit years. Date-only values sent as instants shift
    across January 1 (C8.3). BC years: Java `uuuu` prints 44 BC as
    `-0043`, `yyyy` with `G` prints `0044 BC`. Spreadsheet 1900 and 1904
    systems differ by 1,462 days, about four years (verified day count).
    Fiscal, academic, and tax labels ("FY2027" for October 2026 in the US
    federal convention, "2026/27") are not calendar years (C5.3). Large
    differences also come from wrong epochs (31 years for Apple as Unix),
    wrong units (year 58467), 32-bit overflow (2038 to 1901), and
    sentinels shown as dates (0001-01-01, 1970-01-01, 9999-12-31; C22).
  - In code: years shown from UTC for local events or the reverse.
    `YYYY`, `%G` with `%Y`, `getYear()`, or `yy` in display code. Locale
    formatters without a pinned calendar. Reports grouped by displayed
    year disagreeing with stored-year queries. Spreadsheet imports and
    exports without a declared date system. Year checks accepting plus or
    minus 1 as close enough. Tests covering only New Year boundaries.
  - Fix: display the year from the local date in the defining zone (C3.3,
    C14). Use `yyyy` or `uuuu` (Java), `getFullYear()` (JS), and
    four-digit years. Pair week numbers only with week-based years
    (`%G-W%V`, Java `IsoFields.WEEK_BASED_YEAR` with
    `WEEK_OF_WEEK_BASED_YEAR`). Pin calendar and numbering system where
    Gregorian is required. Read the workbook's date system and convert
    with the spreadsheet library. Label fiscal, academic, and tax years.
    Assert exact expected years per calendar and conversion in tests, and
    apply plausibility bounds to years at input, storage, and display
    (C15.2, C22.1).
  - Not a finding: week-year tokens in deliberate, labeled ISO week
    reporting. Deliberate non-Gregorian or fiscal displays that are
    labeled and never parsed back.
  - Escalate: reports or documents whose displayed year has legal or
    financial meaning without a stated defining zone or calendar.
- C24.5 Formatting mechanics.
  - Facts (verified where marked): rounding a fraction carries into every
    earlier field: naive `'%02d.%03d' % (59, round(0.9996 * 1000))` prints
    `59.1000`, while 2026-12-31T23:59:59.9996 rounded first prints
    `2027-01-01T00:00:00.000`. Local fields depend on the resolved offset.
    Russian uses genitive month names in full dates and nominative alone
    (Java `MMMM` versus `LLLL`, verified, transliterated). The first year
    of a Japanese era is written "gannen" (Node `Intl`, verified).
    Ordinals and plurals depend on number and language (1st, 11th; "in 1
    minute", "2 minutes ago"). Order, digits, marks, sign, and width vary
    (C24.2, C22.5).
  - In code: hand-built formatters concatenating fields with separate
    fraction rounding. Month names from one fixed array. Ordinal suffixes
    by last digit only. Fixed field order for every locale.
  - Fix: round or truncate the value first with full carry, then format
    (C20.5). Use library formatters: ISO for machines, ICU or `Intl` for
    people, including stand-alone versus format forms. Use
    `Intl.PluralRules`, `Intl.RelativeTimeFormat`, or ICU messages.
  - Not a finding: library formatting of values already reduced to the
    displayed precision.
  - Escalate: user-facing date text in supported languages without stated
    grammatical requirements.
- C24.6 Midnight, noon, and 12-hour clocks.
  - Facts (Node `Intl` for 00:00, verified, non-ASCII described): `en-US`
    `12:00 AM`; `en-GB` and `en-AU` 12-hour `12:00 am`; Japanese puts the
    marker first and counts 0 to 11 ("gozen 0:00", noon "gogo 0:00");
    Chinese and Korean put the marker first. `hourCycle: "h11"` gives
    `0:00 AM`, `"h24"` gives `24:00`. `dayPeriod: "long"` gives "12 in the
    morning". Markers vary (`AM`, `am`, `a.m.`, words) and position. Some
    ICU versions put a narrow no-break space (U+202F) before `AM`, breaking
    parsers; this Node build (ICU 77.1) emits a plain space. Style guides
    avoid "12 AM" and "12 PM". "Midnight on Friday" can mean either end of
    Friday, so contracts write 23:59 or 12:01 AM.
  - In code: `hour % 12 || 12` plus " AM" for every locale. Parsers
    expecting an ASCII suffix after a plain space. Midnight and noon
    swapped by 12 AM/PM bugs (parsing C23.5). Deadlines shown or stored as
    "midnight" without a date boundary.
  - Fix: format and parse with locale-aware libraries. Use 24-hour or ISO
    formats for machine data. State midnight deadlines as an unambiguous
    instant or half-open range (C3.6), and display them as "end of Friday"
    or 23:59.
  - Not a finding: library-formatted 12-hour times for display only.
  - Escalate: deadlines or schedules written as "midnight" or "12 AM"
    without a stated start or end of day.
- Proposed severity (for the user to decide), per check: HIGH when
  displayed or formatted values are parsed or saved into wrong stored
  values, break concurrency checks, feed legal documents, invoices, or
  data entry with wrong years, store broken carries, or shift deadlines or
  appointments by 12 or 24 hours on a core path. MEDIUM for machine
  exports in locale formats, reconciliation, reports, labels, and
  user-facing text. LOW for test-only code.

Point ledger for C24:
- Inbound from PA-3: Java `YYYY` week-year example and host-locale
  dependence, `yyyy`/`uuuu` fix, week-year-token not-a-finding -> C24.4.
- Inbound from PA-7: `%Y-W%V` labels, week-label check, ISO pairing fix,
  ISO reporting not-a-finding -> C24.4.
- Inbound from PA-19: Java `uuuu` versus `yyyy G` output -> C24.4.
- Inbound from C2.5: 1,462-day difference between spreadsheet systems ->
  C24.4.
- Inbound from C5.3: fiscal label display -> C24.4.
- Inbound from C6.1: era and calendar display, pinned Gregorian -> C24.2.
- Inbound from C12.3: offset display round trip -> C24.3.
- Inbound from C22.3: sentinels shown as dates -> C24.4.
- Inbound from C22.5: `YYYY` meaning -> C24.4.
- PA-32: locale formats, calendars, digits and marks, names, display
  strings as data, machine exports -> C24.1 and C24.2. Free-text order ->
  C23.3 by reference. Gregorian-from-locale, native digits, pinned
  calendar and digits fix, structured inputs, month-name display,
  not-a-findings, multi-locale escalation -> C24.2. ISO/display split fix
  -> C24.1. Adorno relationship -> scope line (independent). Severity -> C24 severity.
- PA-73: formatter truncation and rounding, stored rounding, offset
  labels, leap-second display, GPS, client correction, omitted seconds,
  deadline mismatch, rounding fix, enforcement fix, escalation -> C24.3.
  Edit-form round trips, string comparisons, parse-back, separate-value
  fix, typed compare, full-precision exports, not-a-finding -> C24.1.
  Severity -> C24 severity.
- PA-74: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C24.4. Severity -> C24 severity.
- PA-75: calendar year table, legacy APIs, pivots, spreadsheet systems,
  epoch, unit, overflow, sentinels, tolerance checks, New-Year-only tests,
  plausibility, exact-year test fix, bound fix, pin fix, not-a-finding ->
  C24.4. Severity -> C24 severity.
- PA-85: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C24.5. 12-hour `hour % 12` -> C24.6. Severity -> C24
  severity.
- PA-112: all facts, code patterns, checks, fixes, not-a-finding,
  escalation -> C24.6. Severity -> C24 severity.
