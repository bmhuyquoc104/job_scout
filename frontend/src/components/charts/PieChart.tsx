import { useState, type KeyboardEvent } from "react";
import { Box, Typography, useTheme } from "@mui/material";
import { formatCount, formatShare } from "./scale";

export interface PieSlice {
  key: string;
  label: string;
  value: number;
  color: string;
}

interface PieChartProps {
  title: string;
  slices: PieSlice[];
}

const SIZE = 200;
const RADIUS = 92;
const CENTER = SIZE / 2;

function pointAt(angle: number, radius = RADIUS) {
  return { x: CENTER + radius * Math.cos(angle), y: CENTER + radius * Math.sin(angle) };
}

/**
 * Pie of one whole split into parts, clockwise from 12 o'clock in the order given. Slices are
 * separated by a 2px surface-colour gap and carry no text; the legend beside it lists every part with
 * its count and share, so nothing depends on colour or hover alone.
 */
export default function PieChart({ title, slices }: PieChartProps) {
  const theme = useTheme();
  const [active, setActive] = useState<number | null>(null);
  const parts = slices.filter((slice) => slice.value > 0);
  const total = parts.reduce((sum, slice) => sum + slice.value, 0);

  function onKeyDown(event: KeyboardEvent) {
    const last = parts.length - 1;
    const next: Record<string, number> = {
      ArrowRight: active === null ? 0 : Math.min(last, active + 1),
      ArrowDown: active === null ? 0 : Math.min(last, active + 1),
      ArrowLeft: active === null ? last : Math.max(0, active - 1),
      ArrowUp: active === null ? last : Math.max(0, active - 1),
      Home: 0,
      End: last,
    };
    if (event.key === "Escape") setActive(null);
    else if (event.key in next) {
      event.preventDefault();
      setActive(next[event.key]);
    }
  }

  if (total === 0) return <Typography color="text.secondary">No open jobs to show.</Typography>;

  let start = -Math.PI / 2;
  const arcs = parts.map((slice) => {
    const angle = (slice.value / total) * Math.PI * 2;
    const from = pointAt(start);
    const to = pointAt(start + angle);
    const middle = start + angle / 2;
    const path = `M${CENTER},${CENTER} L${from.x},${from.y} A${RADIUS},${RADIUS} 0 ${angle > Math.PI ? 1 : 0} 1 ${to.x},${to.y} Z`;
    start += angle;
    return { slice, path, push: { x: Math.cos(middle) * 5, y: Math.sin(middle) * 5 } };
  });

  const focused = active === null ? null : parts[active];

  return (
    <Box
      tabIndex={0}
      role="group"
      aria-label={`${title}. Use the arrow keys to read each part.`}
      onKeyDown={onKeyDown}
      onFocus={() => setActive((current) => current ?? 0)}
      onBlur={() => setActive(null)}
      sx={{ outline: "none", "&:focus-visible": { outline: `2px solid ${theme.palette.primary.main}`, outlineOffset: 2, borderRadius: 1 } }}
    >
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 3 }}>
        <svg width={176} height={176} viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={title} style={{ flex: "none", overflow: "visible" }}>
          {parts.length === 1 ? (
            <circle cx={CENTER} cy={CENTER} r={RADIUS} fill={parts[0].color} />
          ) : (
            arcs.map(({ slice, path, push }, index) => (
              <path
                key={slice.key}
                d={path}
                fill={slice.color}
                stroke={theme.palette.background.paper}
                strokeWidth={2}
                strokeLinejoin="round"
                opacity={active === null || active === index ? 1 : 0.45}
                transform={active === index ? `translate(${push.x} ${push.y})` : undefined}
                onPointerEnter={() => setActive(index)}
                onPointerLeave={() => setActive(null)}
              />
            ))
          )}
        </svg>
        <Box component="ul" aria-label="Legend" sx={{ flex: 1, minWidth: 190, m: 0, p: 0, listStyle: "none" }}>
          {parts.map((slice, index) => (
            <Box
              component="li"
              key={slice.key}
              onPointerEnter={() => setActive(index)}
              onPointerLeave={() => setActive(null)}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                py: 0.4,
                px: 0.75,
                borderRadius: 1,
                bgcolor: active === index ? "action.hover" : "transparent",
              }}
            >
              <Box sx={{ width: 10, height: 10, bgcolor: slice.color, borderRadius: "2px", flex: "none" }} />
              <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }} noWrap>
                {slice.label}
              </Typography>
              <Typography variant="body2" fontWeight={700} sx={{ fontVariantNumeric: "tabular-nums" }}>
                {formatCount(slice.value)}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ width: 34, textAlign: "right" }}>
                {formatShare(slice.value, total)}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
      {/* One readout for the part under the pointer or keyboard focus (or the total). */}
      <Typography role="status" variant="body2" color="text.secondary" sx={{ mt: 1.5, minHeight: 22 }}>
        {focused
          ? `${focused.label}: ${formatCount(focused.value)} jobs (${formatShare(focused.value, total)})`
          : `${formatCount(total)} open jobs in total`}
      </Typography>
    </Box>
  );
}
