import ChartShell from "./ChartShell";
import ChartTable from "./ChartTable";
import TimeSeriesChart, { type ChartKind, type ChartSeries } from "./TimeSeriesChart";
import { formatCount, formatLongDay } from "./scale";

interface ChartCardProps {
  title: string;
  subtitle: string;
  dates: string[];
  series: ChartSeries[];
  kind: ChartKind;
}

/** A day-by-day chart with its table twin. */
export default function ChartCard({ title, subtitle, dates, series, kind }: ChartCardProps) {
  const rows = [...dates.keys()]
    .reverse()
    .map((index) => [formatLongDay(dates[index]), ...series.map((item) => formatCount(item.values[index]))]);
  return (
    <ChartShell
      title={title}
      subtitle={subtitle}
      chart={<TimeSeriesChart title={title} dates={dates} series={series} kind={kind} />}
      table={<ChartTable label={`${title} data`} headers={["Date", ...series.map((item) => item.label)]} rows={rows} />}
    />
  );
}
