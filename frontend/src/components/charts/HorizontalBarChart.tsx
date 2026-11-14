import { Box, Tooltip, Typography } from "@mui/material";
import { formatCount, formatShare } from "./scale";

export interface BarItem {
  key: string;
  label: string;
  value: number;
  color: string;
}

interface HorizontalBarChartProps {
  title: string;
  bars: BarItem[];
  /** What the shares are a share of. */
  total: number;
  /** Replaces the default "count and share" text, e.g. for salaries. */
  valueText?: (bar: BarItem) => string;
}

const BAR_HEIGHT = 16; // columns and bars stay thin (24px at most)
const TRACK_SHARE = 82; // longest bar fills this much of the track, leaving room for its value

/** Ranked horizontal bars: names on the left, value at the tip of each bar, biggest first. */
export default function HorizontalBarChart({ title, bars, total, valueText }: HorizontalBarChartProps) {
  const peak = Math.max(1, ...bars.map((bar) => bar.value));

  return (
    <Box component="ul" role="list" aria-label={title} sx={{ m: 0, p: 0, listStyle: "none", display: "grid", gap: 1.25 }}>
      {bars.map((bar) => (
        <Tooltip
          key={bar.key}
          arrow
          placement="top"
          followCursor
          title={valueText ? `${bar.label}: ${valueText(bar)}` : `${bar.label}: ${formatCount(bar.value)} jobs (${formatShare(bar.value, total)})`}
        >
          <Box
            component="li"
            sx={{
              display: "grid",
              gridTemplateColumns: "minmax(84px, 118px) 1fr",
              alignItems: "center",
              gap: 1.5,
              "&:hover .bar-fill": { filter: "brightness(1.18)" },
            }}
          >
            <Typography variant="body2" color="text.secondary" noWrap>
              {bar.label}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
              <Box
                className="bar-fill"
                // 4px rounded data end, square where it starts.
                sx={{
                  flex: "none",
                  height: BAR_HEIGHT,
                  width: `${(bar.value / peak) * TRACK_SHARE}%`,
                  minWidth: 3,
                  bgcolor: bar.color,
                  borderRadius: "0 4px 4px 0",
                }}
              />
              <Typography variant="body2" noWrap sx={{ fontVariantNumeric: "tabular-nums" }}>
                {valueText ? (
                  <b>{valueText(bar)}</b>
                ) : (
                  <>
                    <b>{formatCount(bar.value)}</b>{" "}
                    <Typography component="span" variant="caption" color="text.secondary">
                      {formatShare(bar.value, total)}
                    </Typography>
                  </>
                )}
              </Typography>
            </Box>
          </Box>
        </Tooltip>
      ))}
    </Box>
  );
}
