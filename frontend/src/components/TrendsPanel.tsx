import { useState } from "react";
import { Alert, Box, MenuItem, Paper, TextField, Typography } from "@mui/material";
import { getLocations, getSources, getTrends, SOURCE_LABELS, sourceLabel } from "../api/client";
import { useApi } from "../api/useApi";
import ChartCard from "./charts/ChartCard";
import ChartShell from "./charts/ChartShell";
import ChartTable from "./charts/ChartTable";
import HorizontalBarChart, { type BarItem } from "./charts/HorizontalBarChart";
import PieChart from "./charts/PieChart";
import { formatCount, formatLongDay, formatShare } from "./charts/scale";
import { chartColors } from "../theme";

const TOP_REGIONS = 8; // the rest are folded into one "Other" bar; the table lists them all

const RANGES = [
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 90 days" },
];

const SENIORITY_LABELS: Record<string, string> = {
  graduate: "Graduate / intern",
  junior: "Junior",
  mid: "Mid-level",
  senior: "Senior",
  lead: "Lead / principal",
  management: "Management",
  unspecified: "Not stated",
};

function StatTile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.75, bgcolor: "background.paper" }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography sx={{ fontSize: 28, fontWeight: 650, lineHeight: 1.2 }}>{value}</Typography>
      {note && (
        <Typography variant="caption" color="text.secondary">
          {note}
        </Typography>
      )}
    </Paper>
  );
}

/** Trend charts for one category, rebuilt from the job event history. */
export default function TrendsPanel({ categoryId }: { categoryId: string }) {
  const [days, setDays] = useState(30);
  const { data, error, loading } = useApi(() => getTrends(categoryId, days), [categoryId, days], "Unable to load trends.");

  const points = data?.points ?? [];
  const dates = points.map((point) => point.date);
  const first = points[0];
  const last = points[points.length - 1];
  const newTotal = points.reduce((sum, point) => sum + point.new, 0);
  const closedTotal = points.reduce((sum, point) => sum + point.closed, 0);
  const change = first && last ? last.total_open - first.total_open : 0;
  // Open jobs by seniority as of the last day shown.
  const seniority = (data?.seniority_levels ?? []).map((level) => ({
    key: level,
    label: SENIORITY_LABELS[level] ?? level,
    value: last?.by_seniority[level] ?? 0,
    color: chartColors.seniority[level],
  }));
  const seniorityTotal = seniority.reduce((sum, slice) => sum + slice.value, 0);

  const { data: sourceData } = useApi(() => getSources(categoryId), [categoryId], "Unable to load sources.");
  const sourceIds = Object.keys(SOURCE_LABELS);
  const sourceSlices = (sourceData?.sources ?? []).map((item) => ({
    key: item.source,
    label: sourceLabel(item.source),
    value: item.count,
    color: chartColors.sourcePalette[sourceIds.indexOf(item.source) % chartColors.sourcePalette.length],
  }));
  const sourceTotal = sourceData?.total_open ?? 0;

  const { data: locations } = useApi(() => getLocations(categoryId), [categoryId], "Unable to load locations.");
  const regions = locations?.regions ?? [];
  const otherRegions = regions.slice(TOP_REGIONS);
  const bars: BarItem[] = [
    ...regions.slice(0, TOP_REGIONS).map((item) => ({ key: item.region, label: item.region, value: item.count, color: chartColors.primary })),
    ...(otherRegions.length
      ? [
          {
            key: "other",
            label: `Other (${otherRegions.length})`,
            value: otherRegions.reduce((sum, item) => sum + item.count, 0),
            color: chartColors.seniority.unspecified,
          },
        ]
      : []),
  ];

  return (
    <Box component="section" aria-label="Trends" sx={{ mb: 2.5 }}>
      {/* One filter row above everything it scopes. */}
      <Box sx={{ display: "flex", justifyContent: "flex-start", mb: 1.5 }}>
        <TextField select size="small" label="Period" value={days} onChange={(event) => setDays(Number(event.target.value))} sx={{ minWidth: 150 }}>
          {RANGES.map((range) => (
            <MenuItem key={range.days} value={range.days}>
              {range.label}
            </MenuItem>
          ))}
        </TextField>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      {!error && !loading && points.length === 0 && (
        <Typography color="text.secondary">No history yet. Trends appear after the first scrape records job changes.</Typography>
      )}
      {points.length > 0 && last && (
        // While a new period loads, the previous charts stay in place, dimmed.
        <Box sx={{ opacity: loading ? 0.55 : 1, transition: "opacity 120ms" }}>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 1.5, mb: 1.5 }}>
            <StatTile
              label="Open jobs now"
              value={formatCount(last.total_open)}
              note={points.length > 1 ? `${change >= 0 ? "+" : ""}${formatCount(change)} since ${formatLongDay(first.date)}` : undefined}
            />
            <StatTile label="New in period" value={formatCount(newTotal)} />
            <StatTile label="Closed in period" value={formatCount(closedTotal)} />
          </Box>
          {data?.history_starts && points.length < days && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              History starts on {formatLongDay(data.history_starts)}, when job tracking began, so these charts fill in as each daily run
              adds a day.
            </Typography>
          )}
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 1.5 }}>
            <ChartCard
              title="Open jobs"
              subtitle="Jobs listed at the end of each day"
              kind="line"
              dates={dates}
              series={[{ key: "open", label: "Open jobs", color: chartColors.primary, values: points.map((point) => point.total_open) }]}
            />
            <ChartCard
              title="New and closed"
              subtitle="Jobs that appeared or disappeared each day"
              kind="grouped"
              dates={dates}
              series={[
                { key: "new", label: "New", color: chartColors.primary, values: points.map((point) => point.new) },
                { key: "closed", label: "Closed", color: chartColors.secondary, values: points.map((point) => point.closed) },
              ]}
            />
            <ChartShell
              title="Open jobs by seniority"
              subtitle={`Level read from the job title, as of ${formatLongDay(last.date)}`}
              chart={<PieChart title="Open jobs by seniority" slices={seniority} />}
              table={
                <ChartTable
                  label="Open jobs by seniority data"
                  headers={["Level", "Jobs", "Share"]}
                  rows={seniority.map((slice) => [slice.label, formatCount(slice.value), formatShare(slice.value, seniorityTotal)])}
                />
              }
            />
            <ChartShell
              title="Open jobs by source"
              subtitle="Where each open job was found"
              chart={<PieChart title="Open jobs by source" slices={sourceSlices} />}
              table={
                <ChartTable
                  label="Open jobs by source data"
                  headers={["Source", "Jobs", "Share"]}
                  rows={sourceSlices.map((slice) => [slice.label, formatCount(slice.value), formatShare(slice.value, sourceTotal)])}
                />
              }
            />
            <ChartShell
              title="Jobs by location"
              subtitle={
                regions.length
                  ? `Open jobs across ${regions.length} regions; ${regions[0].region} has ${formatShare(regions[0].count, locations?.total_open ?? 0)}`
                  : "Open jobs by region"
              }
              chart={<HorizontalBarChart title="Jobs by location" bars={bars} total={locations?.total_open ?? 0} />}
              table={
                <ChartTable
                  label="Jobs by location data"
                  headers={["Region", "Jobs", "Share"]}
                  rows={regions.map((item) => [item.region, formatCount(item.count), formatShare(item.count, locations?.total_open ?? 0)])}
                />
              }
            />
          </Box>
        </Box>
      )}
    </Box>
  );
}
