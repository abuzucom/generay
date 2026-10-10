export function userOffsetHours() {
  // Sent to the server and used to bucket the user's hourly usage for billing.
  return Math.trunc(-new Date().getTimezoneOffset() / 60);
}
