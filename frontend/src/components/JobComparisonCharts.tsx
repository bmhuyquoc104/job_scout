import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import { SOURCE_LABELS, getJobComparison, sourceLabel, type CountryJobStats } from "../api/client";
import { useApi } from "../api/useApi";
import { chartColors } from "../theme";
import ChartShell from "./charts/ChartShell";
import ChartTable from "./charts/ChartTable";
import HorizontalBarChart, { type BarItem } from "./charts/HorizontalBarChart";
import PieChart from "./charts/PieChart";
import { formatCount, formatShare } from "./charts/scale";

const thousands = (value: number, currency: string) => `${currency}${Math.round(value / 1000)}k`;

function salaryRange(stats: CountryJobStats): string {
  if (stats.median_salary_min == null || stats.median_salary_max == null) return "No salaries";
  const low = thousands(stats.median_salary_min, stats.currency);
  const high = thousands(stats.median_salary_max, stats.currency);
  return low === high ? low : `${low}–${high}`;
}

/** One job title compared across the countries, as charts with a table twin each. */
export default function JobComparisonCharts({ title }: { title: string }) {
  const { data, error, loading } = useApi(() => getJobComparison(title), [title], "Unable to load the comparison.");
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return loading ? <CircularProgress aria-label="Loading comparison" size={24} /> : null;

  const countries = data.countries;
  const total = countries.reduce((sum, item) => sum + item.open_jobs, 0);
  if (total === 0) {
    return <Alert severity="info">No open jobs match &ldquo;{title}&rdquo; in any country yet.</Alert>;
  }

  const bar = (item: CountryJobStats, value: number): BarItem => ({
    key: item.country,
    label: item.country_name,
    value,
    color: chartColors.primary,
  });
  const byJobs = [...countries].sort((a, b) => b.open_jobs - a.open_jobs);
  const withSalary = countries.filter((item) => item.median_salary_min != null && item.median_salary_max != null);
  const byPay = [...withSalary].sort((a, b) => (b.median_salary_max ?? 0) - (a.median_salary_max ?? 0));
  const visaRate = (item: CountryJobStats) => (item.open_jobs ? Math.round((1000 * item.visa_sponsor) / item.open_jobs) / 10 : 0);
  const byVisaRate = [...countries].sort((a, b) => visaRate(b) - visaRate(a));
  const listed = countries.filter((item) => item.open_jobs > 0);
  const percent = (item: CountryJobStats) => Math.round((100 * item.with_salary) / item.open_jobs);

  const sourceIds = Object.keys(SOURCE_LABELS);
  const sourceTotals = new Map<string, number>();
  countries.forEach((item) =>
    Object.entries(item.by_source).forEach(([source, count]) => sourceTotals.set(source, (sourceTotals.get(source) ?? 0) + count)),
  );
  const sourceSlices = [...sourceTotals].map(([source, value]) => ({
    key: source,
    label: sourceLabel(source),
    value,
    color: chartColors.sourcePalette[sourceIds.indexOf(source) % chartColors.sourcePalette.length],
  }));

  return (
    <Box sx={{ opacity: loading ? 0.55 : 1, transition: "opacity 120ms" }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        {formatCount(total)} open jobs whose title contains the words of &ldquo;{title}&rdquo;.
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 420px), 1fr))", gap: 1.5 }}>
        <ChartShell
          title="Open jobs by country"
          subtitle="Jobs listed now that match the title"
          chart={<HorizontalBarChart title="Open jobs by country" bars={byJobs.map((item) => bar(item, item.open_jobs))} total={total} />}
          table={
            <ChartTable
              label="Open jobs by country data"
              headers={["Country", "Jobs", "Share"]}
              rows={byJobs.map((item) => [item.country_name, formatCount(item.open_jobs), formatShare(item.open_jobs, total)])}
            />
          }
        />
        <ChartShell
          title="Typical salary by country"
          subtitle="Middle of the median low and high estimate, per year, in each country's own currency (not converted)"
          chart={
            byPay.length ? (
              <HorizontalBarChart
                title="Typical salary by country"
                bars={byPay.map((item) => bar(item, ((item.median_salary_min ?? 0) + (item.median_salary_max ?? 0)) / 2))}
                total={0}
                valueText={(item) => salaryRange(countries.find((c) => c.country === item.key) as CountryJobStats)}
              />
            ) : (
              <Typography variant="body2" color="text.secondary">No matching job lists a salary.</Typography>
            )
          }
          table={
            <ChartTable
              label="Typical salary by country data"
              headers={["Country", "Median range / yr", "Jobs with salary"]}
              rows={countries.map((item) => [item.country_name, salaryRange(item), formatCount(item.with_salary)])}
            />
          }
        />
        <ChartShell
          title="Jobs that list a salary"
          subtitle="Share of each country's matching jobs with a salary estimate"
          chart={
            <HorizontalBarChart
              title="Jobs that list a salary"
              bars={listed.map((item) => bar(item, percent(item)))}
              total={100}
              valueText={(item) => `${item.value}%`}
            />
          }
          table={
            <ChartTable
              label="Jobs that list a salary data"
              headers={["Country", "With salary", "Open jobs", "Share"]}
              rows={listed.map((item) => [item.country_name, formatCount(item.with_salary), formatCount(item.open_jobs), `${percent(item)}%`])}
            />
          }
        />
        <ChartShell
          title="Visa sponsorship rate"
          subtitle="Share of each country's matching open jobs whose ad mentions visa sponsorship or similar"
          chart={
            <HorizontalBarChart
              title="Visa sponsorship rate"
              bars={byVisaRate.map((item) => bar(item, visaRate(item)))}
              total={0}
              valueText={(entry) => {
                const stats = countries.find((c) => c.country === entry.key) as CountryJobStats;
                return `${visaRate(stats)}% (${formatCount(stats.visa_sponsor)} of ${formatCount(stats.open_jobs)})`;
              }}
            />
          }
          table={
            <ChartTable
              label="Visa sponsorship rate data"
              headers={["Country", "Sponsored", "Open jobs", "Rate"]}
              rows={byVisaRate.map((item) => [item.country_name, formatCount(item.visa_sponsor), formatCount(item.open_jobs), `${visaRate(item)}%`])}
            />
          }
        />
        <ChartShell
          title="Open jobs by source"
          subtitle="Where the matching jobs, across all countries, were found"
          chart={<PieChart title="Open jobs by source" slices={sourceSlices} />}
          table={
            <ChartTable
              label="Open jobs by source data"
              headers={["Source", "Jobs", "Share"]}
              rows={sourceSlices.map((slice) => [slice.label, formatCount(slice.value), formatShare(slice.value, total)])}
            />
          }
        />
      </Box>
    </Box>
  );
}
