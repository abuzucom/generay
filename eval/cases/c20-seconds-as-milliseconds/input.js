export function sessionExpired(jwtPayload) {
  // exp is a JWT NumericDate.
  return new Date(jwtPayload.exp) < new Date();
}
