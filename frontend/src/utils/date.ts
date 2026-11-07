const DAY_MS = 24 * 60 * 60 * 1000;

export function formatRelativeDate(value: string | null): string {
  if (!value) return "Not listed";
  const listedAt = Date.parse(value);
  if (Number.isNaN(listedAt)) return "Not listed";
  const days = Math.round((listedAt - Date.now()) / DAY_MS);
  return new Intl.RelativeTimeFormat("en-NZ", { numeric: "auto" }).format(days, "day");
}
