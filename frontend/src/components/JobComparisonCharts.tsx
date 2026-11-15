import { useState } from "react";
import { Alert, Box, CircularProgress, Tab, Tabs, Typography } from "@mui/material";
import { SOURCE_LABELS, getJobComparison, sourceLabel, type CountryJobStats } from "../api/client";
import { SENIORITY_LABELS, SENIORITY_ORDER } from "../api/labels";
import { useApi } from "../api/useApi";
import { chartColors } from "../theme";
import ChartShell from "./charts/ChartShell";
import ChartTable from "./charts/ChartTable";
import HorizontalBarChart, { type BarItem } from "./charts/HorizontalBarChart";
import StackedShareChart, { type Segment, type StackedRow } from "./charts/StackedShareChart";
import { formatCount, formatShare } from "./charts/scale";

const thousands = (value: number, currency: string) => `${currency}${Math.round(value / 1000)}k`;
const percent = (part: number, whole: number) => (whole ? Math.round((1000 * part) / whole) / 10 : 0);
const sum = (counts: Record<string, number>) => Object.values(counts).reduce((total, count) => total + count, 0);

function salaryRange(stats: CountryJobStats): string {
  if (stats.median_salary_min == null || stats.median_salary_max == null) return "No salaries";
  const low = thousands(stats.median_salary_min, stats.currency);
  const high = thousands(stats.median_salary_max, stats.currency);
  return low === high ? low : `${low}–${high}`;
}

/** "X is highest (a) and Y lowest (b)": the one-line answer to what the chart shows. */
function extremes(items: CountryJobStats[], value: (item: CountryJobStats) => number, show: (item: CountryJobStats) => string): string {
  const ranked = items.filter((item) => item.open_jobs > 0).sort((a, b) => value(b) - value(a));
  if (ranked.length < 2) return "";
  const [high, low] = [ranked[0], ranked[ranked.length - 1]];
  return `${high.country_name} is highest (${show(high)}) and ${low.country_name} lowest (${show(low)}).`;
}

/** One stacked chart plus its table twin; the table lists counts and shares per category. */
function mixChart(title: string, subtitle: string, unit: string, rows: StackedRow[], categories: Segment[]) {
  return (
    <ChartShell
      title={title}
      subtitle={subtitle}
      chart={<StackedShareChart title={title} rows={rows} unit={unit} />}
      table={
        <ChartTable
          label={`${title} data`}
          headers={["Country", ...categories.map((category) => category.label)]}
          rows={rows.map((row) => {
            const total = row.segments.reduce((acc, segment) => acc + segment.value, 0);
            return [
              row.label,
              ...categories.map((category) => {
                const value = row.segments.find((segment) => segment.key === category.key)?.value ?? 0;
                return total ? `${formatCount(value)} (${formatShare(value, total)})` : "–";
              }),
            ];
          })}
        />
      }
    />
  );
}

const TABS = ["Jobs", "Visa sponsorship", "Seniority", "Work arrangement", "Pay", "Sources"] as const;
const GRID = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 420px), 1fr))", gap: 1.5 };

/** Countries compared on the open jobs matching a title (all jobs when it is empty). */
export default function JobComparisonCharts({ title }: { title: string }) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Jobs");
  const { data, error, loading } = useApi(() => getJobComparison(title), [title], "Unable to load the comparison.");
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return loading ? <CircularProgress aria-label="Loading comparison" size={24} /> : null;

  const countries = data.countries;
  const total = countries.reduce((acc, item) => acc + item.open_jobs, 0);
  if (total === 0) {
    return <Alert severity="info">No open jobs match &ldquo;{title}&rdquo; in any country yet.</Alert>;
  }

  const bar = (item: CountryJobStats, value: number): BarItem => ({ key: item.country, label: item.country_name, value, color: chartColors.primary });
  const byJobs = [...countries].sort((a, b) => b.open_jobs - a.open_jobs);
  const visaRate = (item: CountryJobStats) => percent(item.visa_sponsor, item.open_jobs);
  const byVisa = [...countries].sort((a, b) => visaRate(b) - visaRate(a));
  const listed = countries.filter((item) => item.open_jobs > 0);
  const salaryRate = (item: CountryJobStats) => Math.round((100 * item.with_salary) / item.open_jobs);
  const withSalary = countries.filter((item) => item.median_salary_min != null && item.median_salary_max != null);
  const byPay = [...withSalary].sort((a, b) => (b.median_salary_max ?? 0) - (a.median_salary_max ?? 0));
  const withYears = countries.filter((item) => item.median_required_years != null);
  const byYears = [...withYears].sort((a, b) => (b.median_required_years ?? 0) - (a.median_required_years ?? 0));
  // Titles state a level, and ads state an arrangement, for only some jobs; judge countries on those
  // jobs, and skip countries with too few to say anything.
  const stated = (item: CountryJobStats) => sum(item.by_seniority) - (item.by_seniority.unspecified ?? 0);
  const arranged = (item: CountryJobStats) => sum(item.by_arrangement) - (item.by_arrangement["Not listed"] ?? 0);
  const levelCovered = countries.filter((item) => stated(item) >= 20);
  const arrangementCovered = countries.filter((item) => arranged(item) >= 0.25 * item.open_jobs && arranged(item) >= 20);
  const gaps = (covered: CountryJobStats[]) => {
    const missing = countries.filter((item) => !covered.includes(item)).map((item) => item.country_name);
    return missing.length ? ` ${missing.join(", ")} rarely state this, so they are left out.` : "";
  };
  const seniorShare = (item: CountryJobStats) =>
    percent((item.by_seniority.senior ?? 0) + (item.by_seniority.lead ?? 0) + (item.by_seniority.management ?? 0), stated(item));
  const remoteShare = (item: CountryJobStats) => percent(item.by_arrangement.Remote ?? 0, arranged(item));

  const seniorityCategories: Segment[] = SENIORITY_ORDER.map((level) => ({
    key: level,
    label: SENIORITY_LABELS[level] ?? level,
    value: 0,
    color: chartColors.seniority[level],
  }));
  const seniorityRows: StackedRow[] = countries.map((item) => ({
    key: item.country,
    label: item.country_name,
    segments: seniorityCategories.map((category) => ({ ...category, value: item.by_seniority[category.key] ?? 0 })),
  }));

  const arrangementKeys = ["Remote", "Hybrid", "On-site", "Not listed"];
  const arrangementCategories: Segment[] = arrangementKeys.map((key, index) => ({
    key,
    label: key,
    value: 0,
    color: key === "Not listed" ? chartColors.seniority.unspecified : chartColors.sourcePalette[index],
  }));
  const arrangementRows: StackedRow[] = countries.map((item) => ({
    key: item.country,
    label: item.country_name,
    segments: arrangementCategories.map((category) => ({ ...category, value: item.by_arrangement[category.key] ?? 0 })),
  }));

  const sourceIds = Object.keys(SOURCE_LABELS);
  const sourceCategories: Segment[] = sourceIds.map((id, index) => ({
    key: id,
    label: sourceLabel(id),
    value: 0,
    color: chartColors.sourcePalette[index % chartColors.sourcePalette.length],
  }));
  const sourceRows: StackedRow[] = countries.map((item) => ({
    key: item.country,
    label: item.country_name,
    segments: sourceCategories.map((category) => ({ ...category, value: item.by_source[category.key] ?? 0 })),
  }));

  const takeaway: Record<(typeof TABS)[number], string> = {
    Jobs: extremes(countries, (item) => item.open_jobs, (item) => formatCount(item.open_jobs)),
    "Visa sponsorship": `Share of open jobs whose ad mentions visa sponsorship. ${extremes(countries, visaRate, (item) => `${visaRate(item)}%`)}`,
    Seniority: `Senior, lead and management jobs as a share of the jobs whose title states a level. ${extremes(levelCovered, seniorShare, (item) => `${seniorShare(item)}%`)}${gaps(levelCovered)}`,
    "Work arrangement": `Remote jobs as a share of the arrangements ads state. ${extremes(arrangementCovered, remoteShare, (item) => `${remoteShare(item)}%`)}${gaps(arrangementCovered)}`,
    Pay: "Pay is in each country's own currency and is not converted, so compare how many jobs show a salary, and read each country's range on its own.",
    Sources: "Where each country's open jobs were found.",
  };

  return (
    <Box sx={{ opacity: loading ? 0.55 : 1, transition: "opacity 120ms" }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        {formatCount(total)} open jobs {title ? <>whose title contains the words of &ldquo;{title}&rdquo;</> : "across every country"}.
      </Typography>
      <Tabs
        value={tab}
        onChange={(_, next: (typeof TABS)[number]) => setTab(next)}
        variant="scrollable"
        scrollButtons="auto"
        aria-label="Comparison"
        sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}
      >
        {TABS.map((name) => (
          <Tab key={name} value={name} label={name} sx={{ textTransform: "none" }} />
        ))}
      </Tabs>
      <Typography sx={{ mb: 2, maxWidth: 760 }}>{takeaway[tab]}</Typography>

      <Box sx={GRID}>
        {tab === "Jobs" && (
          <ChartShell
            title="Open jobs by country"
            subtitle="Count of jobs listed now. Bigger markets have more jobs, so use the other tabs to compare mix."
            chart={<HorizontalBarChart title="Open jobs by country" bars={byJobs.map((item) => bar(item, item.open_jobs))} total={total} />}
            table={
              <ChartTable
                label="Open jobs by country data"
                headers={["Country", "Jobs", "Share"]}
                rows={byJobs.map((item) => [item.country_name, formatCount(item.open_jobs), formatShare(item.open_jobs, total)])}
              />
            }
          />
        )}
        {tab === "Visa sponsorship" && (
          <ChartShell
            title="Visa sponsorship rate"
            subtitle="Share of each country's open jobs whose ad mentions visa sponsorship or similar"
            chart={
              <HorizontalBarChart
                title="Visa sponsorship rate"
                bars={byVisa.map((item) => bar(item, visaRate(item)))}
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
                rows={byVisa.map((item) => [item.country_name, formatCount(item.visa_sponsor), formatCount(item.open_jobs), `${visaRate(item)}%`])}
              />
            }
          />
        )}
        {tab === "Seniority" && (
          <>
            {mixChart("Seniority mix", "Level read from the job title, as a share of each country's jobs", "jobs", seniorityRows, seniorityCategories)}
            <ChartShell
              title="Typical experience asked"
              subtitle="Middle of the years of experience ads ask for, among ads that say or imply a number"
              chart={
                byYears.length ? (
                  <HorizontalBarChart
                    title="Typical experience asked"
                    bars={byYears.map((item) => bar(item, item.median_required_years ?? 0))}
                    total={0}
                    valueText={(entry) => `${entry.value} yrs`}
                  />
                ) : (
                  <Typography variant="body2" color="text.secondary">No matching job states years of experience.</Typography>
                )
              }
              table={
                <ChartTable
                  label="Typical experience asked data"
                  headers={["Country", "Median years"]}
                  rows={countries.map((item) => [item.country_name, item.median_required_years == null ? "–" : String(item.median_required_years)])}
                />
              }
            />
          </>
        )}
        {tab === "Work arrangement" &&
          mixChart("Work arrangement mix", "Remote, hybrid and on-site as a share of listed arrangements (a job can list more than one)", "mentions", arrangementRows, arrangementCategories)}
        {tab === "Pay" && (
          <>
            <ChartShell
              title="Typical salary by country"
              subtitle="Middle of the median low and high estimate, per year, in each country's own currency (not converted)"
              chart={
                byPay.length ? (
                  <HorizontalBarChart
                    title="Typical salary by country"
                    bars={byPay.map((item) => bar(item, ((item.median_salary_min ?? 0) + (item.median_salary_max ?? 0)) / 2))}
                    total={0}
                    valueText={(entry) => salaryRange(countries.find((c) => c.country === entry.key) as CountryJobStats)}
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
                  bars={listed.map((item) => bar(item, salaryRate(item)))}
                  total={100}
                  valueText={(entry) => `${entry.value}%`}
                />
              }
              table={
                <ChartTable
                  label="Jobs that list a salary data"
                  headers={["Country", "With salary", "Open jobs", "Share"]}
                  rows={listed.map((item) => [item.country_name, formatCount(item.with_salary), formatCount(item.open_jobs), `${salaryRate(item)}%`])}
                />
              }
            />
          </>
        )}
        {tab === "Sources" && mixChart("Sources by country", "Where each country's open jobs were found, as a share of its jobs", "jobs", sourceRows, sourceCategories)}
      </Box>
    </Box>
  );
}
