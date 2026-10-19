const DEFAULT_TIMEZONE = "Asia/Kolkata";

// The device's IANA timezone (e.g. "Asia/Kolkata"), so the backend can decide what "today" means
// for this user. Falls back to India when the JS engine cannot report it.
export function deviceTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || DEFAULT_TIMEZONE;
  } catch {
    return DEFAULT_TIMEZONE;
  }
}
