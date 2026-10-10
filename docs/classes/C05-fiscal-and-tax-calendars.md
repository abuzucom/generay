# C5 Fiscal and tax calendars

(sources: PA-123, 124; inbound from PA-2, PA-3, PA-5, PA-7, PA-39, PA-45) Approved by the user.

Scope: fiscal, tax, statutory, payroll, and management calendars: when
their years start, how their periods are built, how they are labeled,
and how entities with different calendars are combined. Attributing
spans across period boundaries is C3.1. Week definitions are C4.3.
Displaying fiscal labels is C24. Non-Gregorian calendars as such are C6.

- C5.1 Fiscal and tax year starts.
  - Facts: governments differ: US federal October 1 to September 30,
    most US states July 1, New York April 1, Texas September 1; UK
    government April 1 and UK personal tax year April 6 to April 5 (a
    date inherited from the 1752 calendar change); Canada federal, Japan,
    and India April 1; Australia July 1; New Zealand government July 1
    and tax year April 1; Iran at Nowruz, around March 21, on the Solar
    Hijri calendar. Companies choose freely (Microsoft July 1, Walmart
    February 1). Academic years also differ. Entities change fiscal
    years, producing short transition years.
  - In code: fiscal or tax year computed as the calendar year. Fiscal
    quarter as `(month - 1) // 3 + 1`. Tax totals grouped by calendar
    year. One hardcoded start month.
  - Fix: configure each entity's and jurisdiction's calendar (start date
    or week rule, label convention, effective dates for changes). Compute
    fiscal periods from that configuration in one service. Use the
    jurisdiction's tax year for tax. Test transition years.
  - Not a finding: configurable fiscal calendars with documented label
    conventions.
- C5.2 Fiscal period structure.
  - Facts: 4-4-5, 4-5-4, and 5-4-4 calendars use 28- and 35-day
    "months". 13-period years use 28-day periods. 52/53-week fiscal years
    have 364 or 371 days and end on a fixed weekday (Apple: the last
    Saturday of September), so their boundaries move against calendar
    dates. Fiscal months differ by organization, so "the month" is not
    the same span for two entities.
  - In code: 52/53-week years approximated by month boundaries. Fiscal
    periods derived from calendar months. Week 53 dropped or never
    tested. 28-to-31-day assumptions applied to fiscal periods.
  - Fix: generate periods from the configured rule (week pattern, year-end
    weekday, 53rd-week rule) with a library or one owned service. Test a
    53-week year and the following year.
  - Not a finding: fiscal periods produced by the configured rule,
    including the week-based not-a-finding in C3.1.
- C5.3 Fiscal labels and quarters.
  - Facts: "FY2027" in the US federal convention is the year ending in
    2027 (starting October 2026). Many Japanese organizations name the
    fiscal year by its starting year. Fiscal quarters follow the fiscal
    year, so "Q1" names different months for different entities.
  - In code: one "FY" label convention for every entity. Quarter labels
    computed from calendar months. Joins or comparisons by label across
    entities.
  - Fix: store the label convention with the calendar and generate labels
    from it. Compare periods by their date ranges, not by label. (Label
    display is C24.)
- C5.4 Multi-entity calendars and consolidation.
  - Facts: local law can dictate the year (India's Companies Act 2013:
    April 1 to March 31, with exceptions by approval; Chinese statutory
    accounts on the calendar year; many Japanese companies closing March
    31). Local calendars set some years (Iran at Nowruz; Ethiopia and
    Nepal in July). Tax, VAT, and payroll periods differ from accounting
    years. IFRS 10 permits a subsidiary's reporting date to differ from
    the parent's by no more than three months, with adjustments for
    significant events. Acquisitions bring their own years. Groups mix
    52/53-week and month-end entities.
  - In code: one global fiscal setting for all entities. Consolidation
    by period label without mapping each entity's period to the group's.
    Statutory or tax reports generated from the group calendar. Payroll
    and tax periods derived from the fiscal year.
  - Fix: define statutory, tax, management, and payroll calendars per
    legal entity, all effective-dated. Map entity periods to group
    periods explicitly, with documented offsets and adjustments. Generate
    statutory and tax reports from each entity's own calendars.
  - Not a finding: per-entity calendars with documented consolidation
    mapping.
- Escalate (C5): financial, tax, or payroll features whose calendar per
  entity and jurisdiction, period rule, or label convention is not
  stated. Tax-year or fiscal-year reports whose straddling-period rule is
  not stated (attribution rule itself is C3.1).
- Proposed severity (for the user to decide), per check: HIGH when
  financial statements, tax filings or returns, budgets, payroll,
  consolidated statements, or regulated reports on a core path use the
  wrong year, period, or entity calendar. MEDIUM for management
  dashboards and labels. LOW for test-only code.

Point ledger for C5:
- Inbound from PA-2: 4-4-5, 4-5-4, 5-4-4 periods of 28 or 35 days ->
  C5.2. Fiscal-calendar not-a-finding -> C5.2.
- Inbound from PA-3: 52/53-week fiscal years (364 or 371 days) -> C5.2.
- Inbound from PA-5: fiscal period boundaries -> C5.2.
- Inbound from PA-7: fiscal or tax year computed as the calendar year ->
  C5.1. Fiscal, tax, and academic years not starting January 1 (facts
  already in C3.1) -> C5.1 detail. Tax-year escalation -> C5 escalation
  (zone and attribution parts stay in C3).
- Inbound from PA-39: fiscal 35-day and 28-day periods -> C5.2.
- Inbound from PA-45: fiscal months differ by organization -> C5.2.
- PA-123: government, company, and tax year starts, transition years,
  calendar-year code, quarter formula, tax grouping, per-entity
  configuration fix, single service, jurisdiction tax year,
  not-a-finding -> C5.1. 52/53-week years approximated by months ->
  C5.2. Label conventions and quarters -> C5.3. Escalation -> C5
  escalation. Severity -> C5 severity.
- PA-124: local law, local calendars, tax/VAT/payroll differences,
  IFRS 10, acquisitions, mixed 52/53-week entities, global setting,
  label consolidation, statutory reports from group calendar, payroll
  derived from fiscal year, what to check, per-entity calendars, period
  mapping, own-calendar reports, not-a-finding -> C5.4. Escalation ->
  C5 escalation. Severity -> C5 severity.
