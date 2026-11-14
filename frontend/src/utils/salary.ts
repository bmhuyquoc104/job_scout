const thousands = (value: number, symbol: string) => `${symbol}${Math.round(value / 1000)}k`;

/** Short form of the parsed yearly estimate, e.g. "$110k–$135k / yr"; empty when there is none. */
export function formatAnnualRange(
  min: number | null,
  max: number | null,
  symbol = "$",
): string {
  if (min == null && max == null) return "";
  const low = min == null ? "" : thousands(min, symbol);
  const high = max == null ? "" : thousands(max, symbol);
  if (min != null && max != null) {
    return min === max ? `${low} / yr` : `${low}–${high} / yr`;
  }
  return max != null ? `up to ${high} / yr` : `from ${low} / yr`;
}
