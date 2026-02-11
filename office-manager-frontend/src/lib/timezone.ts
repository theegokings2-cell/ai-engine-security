import { parseISO } from "date-fns";
import { formatInTimeZone, toZonedTime } from "date-fns-tz";

/**
 * Convert a UTC time string to user's timezone for display
 */
export function formatTimeInTimezone(
  utcTime: string,
  userTimezone: string,
  formatStr: string = "MMM d, yyyy h:mm a"
): string {
  try {
    const date = parseISO(utcTime);
    return formatInTimeZone(date, userTimezone, formatStr);
  } catch {
    return utcTime; // Return original if conversion fails
  }
}

/**
 * Convert user's local time input to UTC for storage
 */
export function convertToUTC(
  localTime: string,
  userTimezone: string
): string {
  try {
    // Parse the local time (assuming it's in the user's timezone)
    const date = new Date(localTime);
    // Convert to UTC by formatting in the user's timezone and re-parsing
    const utcDate = toZonedTime(date, userTimezone);
    return utcDate.toISOString();
  } catch {
    return localTime; // Return original if conversion fails
  }
}

/**
 * Get short timezone offset display (e.g., "EST", "PST", "GMT-5")
 */
export function getTimezoneOffset(timezone: string): string {
  try {
    const now = new Date();
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone,
      timeZoneName: "shortOffset",
    } as Intl.DateTimeFormatOptions).formatToParts(now);
    const tzPart = parts.find((p) => p.type === "timeZoneName");
    return tzPart?.value ?? "UTC";
  } catch {
    return "UTC";
  }
}

/**
 * Format date range in user's timezone
 */
export function formatDateRange(
  startUtc: string,
  endUtc: string,
  userTimezone: string
): string {
  const start = formatTimeInTimezone(startUtc, userTimezone, "MMM d, yyyy h:mm a");
  const end = formatTimeInTimezone(endUtc, userTimezone, "h:mm a zzz");
  return `${start} - ${end}`;
}
