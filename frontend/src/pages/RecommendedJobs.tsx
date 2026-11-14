import { useMemo, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  FormControlLabel,
  LinearProgress,
  Pagination,
  Paper,
  Stack,
  Switch,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import { getMatches } from "../api/client";
import { useApi } from "../api/useApi";
import ChartShell from "../components/charts/ChartShell";
import ChartTable from "../components/charts/ChartTable";
import HorizontalBarChart, { type BarItem } from "../components/charts/HorizontalBarChart";
import JobRow, { STRONG } from "../components/JobMatchRow";
import PageHeader from "../components/PageHeader";
import { useCountry } from "../country/CountryContext";
import { chartColors } from "../theme";
import { loadCvSkills, loadCvYears } from "../utils/cvSkills";

const PAGE_SIZE = 20;
const CLOSEST_JOBS = 50; // the skill chart looks at the jobs you are closest to
const TOP_SKILLS = 10;

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.75, flex: "1 1 150px" }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h5" component="p">
        {value}
      </Typography>
    </Paper>
  );
}

export default function RecommendedJobs() {
  const [skills] = useState(loadCvSkills);
  const [years] = useState(loadCvYears);
  const [page, setPage] = useState(1);
  const { countries, country, countryName, setCountry, loading: countryLoading } = useCountry();
  const [search, setSearch] = useSearchParams();
  const visaOnly = search.get("visa") === "1";
  const { data: ranked, error, loading } = useApi(
    () => (skills.length && !countryLoading ? getMatches(skills, country, years) : Promise.resolve([])),
    [skills, years, country, countryLoading],
    "Unable to load recommended jobs.",
  );

  const matches = useMemo(() => (visaOnly ? ranked?.filter((match) => match.visa_sponsor) : ranked) ?? null, [ranked, visaOnly]);
  const { missing, strong } = useMemo(() => {
    const counts = new Map<string, number>();
    for (const match of (matches ?? []).slice(0, CLOSEST_JOBS))
      for (const skill of match.missing_skills) counts.set(skill, (counts.get(skill) ?? 0) + 1);
    return {
      missing: [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, TOP_SKILLS),
      strong: (matches ?? []).filter((match) => match.score >= STRONG).length,
    };
  }, [matches]);
  const closest = Math.min(CLOSEST_JOBS, matches?.length ?? 0);
  const bars: BarItem[] = missing.map(([skill, count]) => ({ key: skill, label: skill, value: count, color: chartColors.primary }));

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: { xs: 2, md: 3 }, overflow: "auto" }}>
      <PageHeader
        title="Recommended jobs"
        subtitle="Open jobs ranked against the CV saved in this browser."
        actions={
          <Button component={RouterLink} to="/cv" variant="outlined" size="small">
            Update CV
          </Button>
        }
      />
      {skills.length === 0 ? (
        <Alert
          severity="info"
          sx={{ maxWidth: 640 }}
          action={
            <Button component={RouterLink} to="/cv" color="inherit" size="small">
              Upload CV
            </Button>
          }
        >
          Upload your CV once to see open jobs ranked for it.
        </Alert>
      ) : (
        <Stack spacing={2.5}>
          <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ md: "center" }} sx={{ borderBottom: 1, borderColor: "divider" }}>
            <Tabs
              value={country}
              onChange={(_, next: string) => {
                setCountry(next);
                setPage(1);
              }}
              variant="scrollable"
              scrollButtons="auto"
              aria-label="Country"
            >
              {countries.map((option) => (
                <Tab key={option.code} value={option.code} label={option.name} sx={{ textTransform: "none" }} />
              ))}
            </Tabs>
            <FormControlLabel
              sx={{ mr: 0 }}
              label="Visa sponsorship only"
              control={
                <Switch
                  checked={visaOnly}
                  onChange={(event) => {
                    setSearch(event.target.checked ? { visa: "1" } : {}, { replace: true });
                    setPage(1);
                  }}
                />
              }
            />
          </Stack>

          <Accordion variant="outlined" disableGutters sx={{ bgcolor: "background.paper", "&::before": { display: "none" } }}>
            <AccordionSummary>
              <Typography variant="body2" color="primary">
                How is the score worked out?
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" color="text.secondary" component="div">
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  <li>The score is how much of a job&apos;s listed IT skills your CV covers, counting rarer skills more.</li>
                  <li>It is lowered when the job asks for more years of experience than your CV states, and a little when it asks for far fewer.</li>
                  <li>It is raised when the ad offers visa sponsorship, but only if you match at least one skill.</li>
                  <li>It is a guide to skill overlap, not a judgement of fit.</li>
                </ul>
              </Typography>
            </AccordionDetails>
          </Accordion>

          {years === null && (
            <Alert
              severity="info"
              action={
                <Button component={RouterLink} to="/cv" color="inherit" size="small">
                  Add years
                </Button>
              }
            >
              Your CV does not state years of experience, so seniority is not part of the ranking. Add it to push jobs that ask for much more (or much less) down.
            </Alert>
          )}
          {loading && <LinearProgress aria-label="Ranking jobs" />}
          {error && <Alert severity="error">{error}</Alert>}

          {matches && matches.length > 0 && (
            <>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
                <Stat label={visaOnly ? `Open jobs with sponsorship in ${countryName}` : `Open jobs in ${countryName}`} value={matches.length.toLocaleString()} />
                <Stat label={`Strong matches (${STRONG}%+)`} value={String(strong)} />
                <Stat label="Best match" value={`${matches[0].score}%`} />
              </Box>

              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 380px" }, alignItems: "start" }}>
                <Box component="section" aria-label="Best matches">
                  <Typography variant="h6" component="h2" gutterBottom>
                    Best matches
                  </Typography>
                  <Stack component="ol" spacing={1} sx={{ m: 0, p: 0, listStyle: "none" }}>
                    {matches.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((match) => (
                      <JobRow key={match.id} match={match} cvYears={years} />
                    ))}
                  </Stack>
                  <Pagination count={Math.ceil(matches.length / PAGE_SIZE)} page={page} onChange={(_, value) => setPage(value)} sx={{ mt: 2 }} />
                </Box>
                <ChartShell
                  title="Skills to add first"
                  subtitle={`Skills most often missing from your ${closest} closest jobs. Add the ones that are true for you.`}
                  chart={
                    bars.length ? (
                      <HorizontalBarChart title="Skills to add first" bars={bars} total={closest} />
                    ) : (
                      <Typography color="text.secondary">Your CV already covers your closest jobs.</Typography>
                    )
                  }
                  table={
                    <ChartTable label="Skills to add first data" headers={["Skill", "Jobs"]} rows={missing.map(([skill, count]) => [skill, String(count)])} />
                  }
                />
              </Box>
            </>
          )}
          {matches && matches.length === 0 && !loading && (
            <Alert severity="info">{visaOnly ? `No open jobs in ${countryName} mention visa sponsorship.` : "No open jobs right now."}</Alert>
          )}
        </Stack>
      )}
    </Box>
  );
}
