const thousands = (value: number) => `$${Math.round(value / 1000)}k`;

/** Short form of the parsed yearly estimate, e.g. "$110k–$135k / yr"; empty when there is none. */
export function formatAnnualRange(min: number | null, max: number | null): string {
  if (min == null && max == null) return "";
  if (min != null && max != null) {
    return min === max ? `${thousands(min)} / yr` : `${thousands(min)}–${thousands(max)} / yr`;
  }
  return max != null ? `up to ${thousands(max)} / yr` : `from ${thousands(min as number)} / yr`;
}
