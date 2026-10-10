export function userZone() {
  // Default only; the profile page asks the user to confirm.
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}
