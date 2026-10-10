export function nextRenewal(current) {
  // Monthly subscription renewal, anchored on the signup day.
  const next = new Date(current.getTime());
  next.setMonth(next.getMonth() + 1);
  return next;
}
