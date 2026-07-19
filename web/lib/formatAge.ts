/** Format a unix timestamp (seconds) as a relative age string. */
export function formatAge(unixSeconds: number, nowMs: number = Date.now()): string {
  const ageSec = Math.max(0, Math.floor(nowMs / 1000 - unixSeconds));
  if (ageSec < 60) {
    return `${ageSec}s`;
  }
  const ageMin = Math.floor(ageSec / 60);
  if (ageMin < 60) {
    return `${ageMin}m`;
  }
  const ageHr = Math.floor(ageMin / 60);
  if (ageHr < 48) {
    return `${ageHr}h`;
  }
  const ageDay = Math.floor(ageHr / 24);
  return `${ageDay}d`;
}
