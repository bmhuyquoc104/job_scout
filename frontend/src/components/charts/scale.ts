/** Round tick values up to a "nice" step (1, 2, 5 x 10^n) so the axis reads 0 / 50 / 100, not 0 / 37 / 74. */
export function niceTicks(max: number, target = 4): number[] {
  if (max <= 0) return [0, 1];
  const rough = max / target;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 5, 10].map((m) => m * magnitude).find((candidate) => candidate >= rough) ?? magnitude * 10;
  const ticks: number[] = [];
  for (let value = 0; value < max + step; value += step) {
    ticks.push(value);
    if (value >= max) break;
  }
  return ticks;
}

const dayFormat = new Intl.DateTimeFormat("en-NZ", { day: "numeric", month: "short", timeZone: "UTC" });
const longDayFormat = new Intl.DateTimeFormat("en-NZ", {
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/** Dates arrive as plain "YYYY-MM-DD" (a calendar day, not an instant), so format them in UTC. */
export const formatDay = (iso: string) => dayFormat.format(new Date(`${iso}T00:00:00Z`));
export const formatLongDay = (iso: string) => longDayFormat.format(new Date(`${iso}T00:00:00Z`));

/** Whole numbers in full below 10,000 and compact above, one style per axis. */
export function formatCount(value: number, compact = false): string {
  if (compact && Math.abs(value) >= 10_000) {
    return new Intl.NumberFormat("en-NZ", { notation: "compact", maximumFractionDigits: 1 }).format(value);
  }
  return value.toLocaleString("en-NZ");
}

/** A share as a whole percent, "<1%" for a small but non-zero part. */
export function formatShare(value: number, total: number): string {
  if (total <= 0 || value <= 0) return "0%";
  const percent = (value / total) * 100;
  return percent < 1 ? "<1%" : `${Math.round(percent)}%`;
}

/** Indexes of the x labels to print: evenly spread, never more than `max`, always the last day. */
export function labelIndexes(count: number, max: number): number[] {
  if (count <= max) return Array.from({ length: count }, (_, i) => i);
  const step = Math.ceil((count - 1) / (max - 1));
  const picked: number[] = [];
  for (let i = count - 1; i >= 0; i -= step) picked.unshift(i);
  return picked;
}

/** Column path: 4px rounded data-end (top), square at the baseline. */
export function columnPath(x: number, y: number, width: number, height: number, radius = 4): string {
  const r = Math.max(0, Math.min(radius, width / 2, height));
  return [
    `M${x},${y + height}`,
    `V${y + r}`,
    `Q${x},${y} ${x + r},${y}`,
    `H${x + width - r}`,
    `Q${x + width},${y} ${x + width},${y + r}`,
    `V${y + height}`,
    "Z",
  ].join(" ");
}
