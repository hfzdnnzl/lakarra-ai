/** Format helpers for Content Analytics optional metrics. */

/** Stored watch_time is total seconds; display as hh:mm:ss. */
export function secondsToHms(totalSeconds: number | null | undefined): string {
  if (totalSeconds == null || totalSeconds < 0 || Number.isNaN(totalSeconds)) {
    return "";
  }
  const whole = Math.round(totalSeconds);
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const seconds = whole % 60;
  return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

/** Parse hh:mm:ss (or mm:ss) into total seconds. */
export function hmsToSeconds(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parts = trimmed.split(":").map((part) => Number.parseInt(part, 10));
  if (parts.some((part) => Number.isNaN(part) || part < 0)) {
    return null;
  }
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  }
  if (parts.length === 1) {
    return parts[0];
  }
  return null;
}

/** Stored completion_rate is 0–1; display as percentage. */
export function ratioToPercent(ratio: number | null | undefined): string {
  if (ratio == null || Number.isNaN(ratio)) {
    return "";
  }
  const pct = ratio * 100;
  return Number.isInteger(pct) ? String(pct) : pct.toFixed(2).replace(/\.?0+$/, "");
}

/** Parse a percentage (e.g. 45 or 45%) into 0–1 ratio. */
export function percentToRatio(value: string): number | null {
  const trimmed = value.trim().replace(/%$/, "");
  if (!trimmed) {
    return null;
  }
  const pct = Number.parseFloat(trimmed);
  if (Number.isNaN(pct)) {
    return null;
  }
  return Math.min(1, Math.max(0, pct / 100));
}

export function hasSavedMetrics(metrics: {
  views?: number | null;
  likes?: number | null;
  comments?: number | null;
  shares?: number | null;
  saves?: number | null;
}): boolean {
  return (
    metrics.views != null ||
    metrics.likes != null ||
    metrics.comments != null ||
    metrics.shares != null ||
    metrics.saves != null
  );
}

export function formatMetricDisplay(
  field: string,
  value: number | null | undefined,
): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  if (field === "watch_time") {
    return secondsToHms(value) || "—";
  }
  if (field === "completion_rate") {
    const pct = ratioToPercent(value);
    return pct ? `${pct}%` : "—";
  }
  if (field === "average_watch_duration") {
    return `${value}s`;
  }
  return value.toLocaleString();
}
