const MS_PER_SECOND = 1000;

export function sessionExpired(jwtPayload, nowMs) {
  // exp is a JWT NumericDate in seconds (RFC 7519).
  return jwtPayload.exp * MS_PER_SECOND <= nowMs;
}
