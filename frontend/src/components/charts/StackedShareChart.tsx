import { Box, Tooltip, Typography } from "@mui/material";
import { formatCount } from "./scale";

export interface Segment {
  key: string;
  label: string;
  value: number;
  color: string;
}

export interface StackedRow {
  key: string;
  label: string;
  segments: Segment[];
}

interface StackedShareChartProps {
  title: string;
  rows: StackedRow[];
  /** What a segment's number counts, for the tooltip: "jobs", "mentions". */
  unit: string;
}

const MIN_LABELLED = 9; // a segment narrower than this share gets no text inside it

/** Dark text on light segments and white on dark ones, as theme colours, so the percentage stays readable. */
function textOn(hex: string): string {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "background.default" : "common.white";
}

/**
 * One 100% bar per row, split by category, on a shared 0-100% scale: the way to compare the *mix*
 * of countries of very different sizes. Counts stay in the tooltip and the table twin.
 */
export default function StackedShareChart({ title, rows, unit }: StackedShareChartProps) {
  const legend = new Map<string, Segment>();
  rows.forEach((row) =>
    row.segments.forEach((segment) => segment.value > 0 && !legend.has(segment.key) && legend.set(segment.key, segment)),
  );

  return (
    <Box>
      <Box component="ul" aria-label={`${title} legend`} sx={{ m: 0, mb: 1.5, p: 0, listStyle: "none", display: "flex", flexWrap: "wrap", gap: 1.5 }}>
        {[...legend.values()].map((segment) => (
          <Box component="li" key={segment.key} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
            <Box aria-hidden sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: segment.color }} />
            <Typography variant="caption" color="text.secondary">
              {segment.label}
            </Typography>
          </Box>
        ))}
      </Box>
      <Box component="ul" role="list" aria-label={title} sx={{ m: 0, p: 0, listStyle: "none", display: "grid", gap: 1.5 }}>
        {rows.map((row) => {
          const total = row.segments.reduce((sum, segment) => sum + segment.value, 0);
          return (
            <Box component="li" key={row.key} sx={{ display: "grid", gridTemplateColumns: "minmax(80px, 130px) 1fr", alignItems: "center", gap: 1.5 }}>
              <Typography variant="body2" noWrap title={row.label}>
                {row.label}
              </Typography>
              {total === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  No jobs
                </Typography>
              ) : (
                <Box sx={{ display: "flex", height: 26, borderRadius: 0.75, overflow: "hidden", bgcolor: "action.hover" }}>
                  {row.segments
                    .filter((segment) => segment.value > 0)
                    .map((segment) => {
                      const share = (100 * segment.value) / total;
                      return (
                        <Tooltip key={segment.key} arrow placement="top" title={`${row.label} · ${segment.label}: ${formatCount(segment.value)} ${unit} (${share.toFixed(1)}%)`}>
                          <Box sx={{ width: `${share}%`, bgcolor: segment.color, display: "grid", placeItems: "center", minWidth: 2 }}>
                            {share >= MIN_LABELLED && (
                              <Typography variant="caption" sx={{ color: textOn(segment.color), fontWeight: 700, lineHeight: 1 }}>
                                {Math.round(share)}%
                              </Typography>
                            )}
                          </Box>
                        </Tooltip>
                      );
                    })}
                </Box>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
