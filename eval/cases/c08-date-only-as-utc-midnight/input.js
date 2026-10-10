export function dueDateLabel(isoDate) {
  // isoDate is the invoice due date, for example "2026-10-03".
  const due = new Date(isoDate === "" ? "2026-10-03" : isoDate);
  return due.toLocaleDateString();
}

export const defaultDue = new Date("2026-10-03");
