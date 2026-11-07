import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { Box, Typography, useTheme } from "@mui/material";
import { columnPath, formatCount, formatDay, formatLongDay, labelIndexes, niceTicks } from "./scale";

export interface ChartSeries {
  key: string;
  label: string;
  color: string;
  values: number[];
}
export type ChartKind = "line" | "grouped";

interface TimeSeriesChartProps {
  /** Accessible name; also what a screen reader hears first. */
  title: string;
  /** One "YYYY-MM-DD" per x position. */
  dates: string[];
  series: ChartSeries[];
  kind: ChartKind;
  /** Total height including the x-axis band. */
  height?: number;
}

const MARGIN = { top: 14, right: 16, bottom: 26, left: 44 };
const SURFACE_GAP = 2;
const MAX_BAR = 24;
const TOOLTIP_WIDTH = 210;

/**
 * Hand-drawn SVG chart following the data-viz spec: 2px lines, columns capped at 24px with a 4px
 * rounded data end and a 2px surface gap, hairline grid, hover crosshair with one tooltip for every
 * series, and the same details on keyboard focus. Text always uses text tokens, never series colours.
 */
export default function TimeSeriesChart({ title, dates, series, kind, height = 220 }: TimeSeriesChartProps) {
  const theme = useTheme();
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [active, setActive] = useState<number | null>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const count = dates.length;
  const plotWidth = Math.max(0, width - MARGIN.left - MARGIN.right);
  const plotHeight = height - MARGIN.top - MARGIN.bottom;
  const band = count ? plotWidth / count : 0;
  const baseline = MARGIN.top + plotHeight;

  const peak = Math.max(0, ...series.flatMap((item) => item.values));
  const ticks = niceTicks(peak);
  const top = ticks[ticks.length - 1];
  const yOf = (value: number) => MARGIN.top + plotHeight - (value / top) * plotHeight;
  const xCenter = (index: number) => MARGIN.left + band * (index + 0.5);

  const grid = theme.palette.divider;
  const surface = theme.palette.background.paper;
  const labelFill = theme.palette.text.secondary;

  function moveTo(event: PointerEvent<SVGRectElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    const index = Math.floor(((event.clientX - box.left) / box.width) * count);
    setActive(Math.min(count - 1, Math.max(0, index)));
  }

  function onKeyDown(event: KeyboardEvent) {
    const last = count - 1;
    const keys: Record<string, number> = {
      ArrowLeft: Math.max(0, (active ?? last) - 1),
      ArrowRight: Math.min(last, (active ?? last) + 1),
      Home: 0,
      End: last,
    };
    if (event.key === "Escape") setActive(null);
    else if (event.key in keys) {
      event.preventDefault();
      setActive(keys[event.key]);
    }
  }

  const labelEvery = labelIndexes(count, Math.max(2, Math.floor(plotWidth / 72)));
  const showLegend = series.length > 1;
  const activeX = active === null ? 0 : xCenter(active);
  // Open on whichever side of the pointer has room for the tooltip.
  const flip = active !== null && activeX + 14 + TOOLTIP_WIDTH > width;

  return (
    <Box
      ref={ref}
      tabIndex={0}
      role="group"
      aria-label={`${title}. Use the left and right arrow keys to read each day.`}
      onKeyDown={onKeyDown}
      onFocus={() => setActive((current) => current ?? count - 1)}
      onBlur={() => setActive(null)}
      sx={{ position: "relative", width: "100%", outline: "none", "&:focus-visible": { outline: `2px solid ${theme.palette.primary.main}`, outlineOffset: 2, borderRadius: 1 } }}
    >
      {showLegend && (
        <Box component="ul" aria-label="Legend" sx={{ display: "flex", flexWrap: "wrap", gap: 2, m: 0, mb: 1, p: 0, listStyle: "none" }}>
          {series.map((item) => (
            <Box component="li" key={item.key} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
              {kind === "line" ? (
                <Box sx={{ width: 16, height: 2, bgcolor: item.color, borderRadius: 1 }} />
              ) : (
                <Box sx={{ width: 10, height: 10, bgcolor: item.color, borderRadius: "2px" }} />
              )}
              <Typography variant="caption" color="text.secondary">
                {item.label}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
      <Box sx={{ position: "relative" }}>
      {width > 0 && count > 0 && (
        <svg width={width} height={height} role="img" aria-label={title} style={{ display: "block", overflow: "visible" }}>
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={MARGIN.left} x2={MARGIN.left + plotWidth} y1={yOf(tick)} y2={yOf(tick)} stroke={grid} strokeWidth={1} />
              <text x={MARGIN.left - 8} y={yOf(tick)} dy="0.32em" textAnchor="end" fontSize={11} fill={labelFill}>
                {formatCount(tick, true)}
              </text>
            </g>
          ))}
          {labelEvery.map((index) => (
            <text key={dates[index]} x={xCenter(index)} y={baseline + 17} textAnchor="middle" fontSize={11} fill={labelFill}>
              {formatDay(dates[index])}
            </text>
          ))}

          {active !== null && kind !== "line" && (
            <rect x={MARGIN.left + band * active} y={MARGIN.top} width={band} height={plotHeight} fill={theme.palette.text.primary} opacity={0.06} />
          )}

          {kind === "line" &&
            series.map((item) => {
              const points = item.values.map((value, index) => `${xCenter(index)},${yOf(value)}`);
              const last = item.values.length - 1;
              return (
                <g key={item.key}>
                  {count > 1 && (
                    <>
                      <path d={`M${points.join(" L")} L${xCenter(last)},${baseline} L${xCenter(0)},${baseline} Z`} fill={item.color} opacity={0.1} />
                      <path d={`M${points.join(" L")}`} fill="none" stroke={item.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                    </>
                  )}
                  <circle cx={xCenter(last)} cy={yOf(item.values[last])} r={4} fill={item.color} stroke={surface} strokeWidth={2} />
                  {series.length === 1 && (
                    <text x={xCenter(last)} y={yOf(item.values[last]) - 10} textAnchor={last === 0 ? "middle" : "end"} fontSize={12} fontWeight={600} fill={theme.palette.text.primary}>
                      {formatCount(item.values[last])}
                    </text>
                  )}
                  {active !== null && active !== last && (
                    <circle cx={xCenter(active)} cy={yOf(item.values[active])} r={4} fill={item.color} stroke={surface} strokeWidth={2} />
                  )}
                </g>
              );
            })}

          {kind === "grouped" &&
            dates.map((date, index) => {
              const barWidth = Math.max(1, Math.min(MAX_BAR, (band * 0.8 - SURFACE_GAP * (series.length - 1)) / series.length));
              const groupWidth = series.length * barWidth + SURFACE_GAP * (series.length - 1);
              return series.map((item, seriesIndex) => {
                const value = item.values[index];
                if (value <= 0) return null;
                const x = xCenter(index) - groupWidth / 2 + seriesIndex * (barWidth + SURFACE_GAP);
                return <path key={`${date}-${item.key}`} d={columnPath(x, yOf(value), barWidth, baseline - yOf(value))} fill={item.color} />;
              });
            })}

          <line x1={MARGIN.left} x2={MARGIN.left + plotWidth} y1={baseline} y2={baseline} stroke={theme.palette.text.disabled} strokeWidth={1} opacity={0.5} />
          {active !== null && kind === "line" && (
            <line x1={xCenter(active)} x2={xCenter(active)} y1={MARGIN.top} y2={baseline} stroke={theme.palette.text.disabled} strokeWidth={1} />
          )}
          {/* Hit area: the whole plot, so the pointer only has to be near a day, not on a 2px line. */}
          <rect x={MARGIN.left} y={MARGIN.top} width={plotWidth} height={plotHeight} fill="transparent" onPointerMove={moveTo} onPointerDown={moveTo} onPointerLeave={() => setActive(null)} />
        </svg>
      )}
      {active !== null && width > 0 && (
        <Box
          role="status"
          sx={{
            position: "absolute",
            top: MARGIN.top,
            left: flip ? undefined : activeX + 14,
            right: flip ? width - activeX + 14 : undefined,
            width: "max-content",
            maxWidth: TOOLTIP_WIDTH,
            p: 1.25,
            pointerEvents: "none",
            bgcolor: "background.paper",
            border: 1,
            borderColor: "divider",
            borderRadius: 1.5,
            boxShadow: 3,
            zIndex: 1,
          }}
        >
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
            {formatLongDay(dates[active])}
          </Typography>
          {series.map((item) => (
            <Box key={item.key} sx={{ display: "flex", alignItems: "center", gap: 1, py: 0.1 }}>
              <Box sx={{ width: 12, height: 2, bgcolor: item.color, flex: "none" }} />
              <Typography variant="body2" fontWeight={700} sx={{ minWidth: 28 }}>
                {formatCount(item.values[active])}
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>
                {item.label}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
      </Box>
    </Box>
  );
}
