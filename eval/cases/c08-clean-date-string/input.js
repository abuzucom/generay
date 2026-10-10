export function dueDateLabel(isoDate) {
  // Keep the due date as a calendar date; never convert it to an instant.
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Intl.DateTimeFormat("en-US", { timeZone: "UTC", dateStyle: "medium" })
    .format(Date.UTC(year, month - 1, day));
}
