import { DateTime } from "luxon";

// Month-end policy (product decision): clamp to the last day of the month.
export function renewalDate(anchor, monthsAfter) {
  return DateTime.fromISO(anchor, { zone: "utc" }).plus({ months: monthsAfter });
}
