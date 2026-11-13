import { useMemo, useState } from "react";
import { Alert, Box, Button, Chip, LinearProgress, Link, Pagination, Paper, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { getMatches, type JobMatch } from "../api/client";
import { useApi } from "../api/useApi";
import ChartShell from "../components/charts/ChartShell";
import ChartTable from "../components/charts/ChartTable";
import HorizontalBarChart, { type BarItem } from "../components/charts/HorizontalBarChart";
import { chartColors } from "../theme";
import { useCountry } from "../country/CountryContext";
import { loadCvSkills } from "../utils/cvSkills";

const PAGE_SIZE = 20;
const CLOSEST_JOBS = 50; // the skill chart looks at the jobs you are closest to
const QUICK_WINS = 5;
const TOP_SKILLS = 12;
const STRONG = 65;

const scoreColor = (score: number) => (score >= STRONG ? "success" : score >= 35 ? "warning" : "default");

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.75, flex: "1 1 160px" }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h5" fontWeight={700}>
        {value}
      </Typography>
    </Paper>
  );
}

function MissingChips({ skills }: { skills: string[] }) {
  if (skills.length === 0) return null;
  return (
    <Stack direction="row" gap={0.5} flexWrap="wrap" alignItems="center" sx={{ mt: 0.5 }}>
      <Typography variant="caption" color="text.secondary">
        Add to your CV:
      </Typography>
      {skills.map((skill) => (
        <Chip key={skill} size="small" variant="outlined" label={skill} />
      ))}
    </Stack>
  );
}

function JobRow({ match }: { match: JobMatch }) {
  return (
    <Paper component="li" variant="outlined" sx={{ p: 2, display: "flex", gap: 2, alignItems: "center" }}>
      <Chip label={`${match.score}%`} color={scoreColor(match.score)} />
      <Box sx={{ minWidth: 0 }}>
        <Link component={RouterLink} to={`/jobs/${match.id}`} underline="hover" fontWeight={600}>
          {match.position}
        </Link>
        <Typography variant="body2" color="text.secondary">
          {[match.company_name, match.location, match.salary_label].filter(Boolean).join(" · ")}
        </Typography>
        <MissingChips skills={match.missing_skills} />
      </Box>
    </Paper>
  );
}

export default function RecommendedJobs() {
  const [skills] = useState(loadCvSkills);
  const [page, setPage] = useState(1);
  const { country, countryName, loading: countryLoading } = useCountry();
  const { data: matches, error, loading } = useApi(
    () => (skills.length && !countryLoading ? getMatches(skills, country) : Promise.resolve([])),
    [skills, country, countryLoading],
    "Unable to load recommended jobs.",
  );

  const { missing, quickWins, strong } = useMemo(() => {
    const counts = new Map<string, number>();
    for (const match of (matches ?? []).slice(0, CLOSEST_JOBS))
      for (const skill of match.missing_skills) counts.set(skill, (counts.get(skill) ?? 0) + 1);
    return {
      missing: [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, TOP_SKILLS),
      quickWins: (matches ?? []).filter((match) => match.missing_skills.length > 0).slice(0, QUICK_WINS),
      strong: (matches ?? []).filter((match) => match.score >= STRONG).length,
    };
  }, [matches]);
  const closest = Math.min(CLOSEST_JOBS, matches?.length ?? 0);
  const bars: BarItem[] = missing.map(([skill, count]) => ({ key: skill, label: skill, value: count, color: chartColors.primary }));

  return (
    <Box component="main" sx={{ flex: 1, p: 3, overflow: "auto" }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Recommended jobs
      </Typography>
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
        <>
          {loading && <LinearProgress aria-label="Ranking jobs" />}
          {error && <Alert severity="error">{error}</Alert>}
          {matches && matches.length > 0 && (
            <Stack spacing={3}>
              <Typography color="text.secondary">
                Open jobs in {countryName}, based on the CV saved in this browser (
                <Link component={RouterLink} to="/cv">
                  change
                </Link>
                ). The score is how much of a job's listed IT skills your CV covers; it is not a judgement of fit. Change the country on the{" "}
                <Link component={RouterLink} to="/">
                  dashboard
                </Link>
                .
              </Typography>

              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
                <Stat label="Open jobs compared" value={String(matches.length)} />
                <Stat label={`Strong matches (${STRONG}%+)`} value={String(strong)} />
                <Stat label="Best match" value={`${matches[0].score}%`} />
              </Box>

              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" } }}>
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
                    <ChartTable
                      label="Skills to add first data"
                      headers={["Skill", "Jobs"]}
                      rows={missing.map(([skill, count]) => [skill, String(count)])}
                    />
                  }
                />
                <Paper component="section" variant="outlined" aria-label="Quick wins" sx={{ p: 2 }}>
                  <Typography component="h3" variant="subtitle1" fontWeight={700}>
                    Quick wins
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Your closest jobs that still name skills your CV lacks. Start here.
                  </Typography>
                  <Stack component="ol" spacing={1} sx={{ mt: 1.5, p: 0, listStyle: "none" }}>
                    {quickWins.map((match) => (
                      <JobRow key={match.id} match={match} />
                    ))}
                  </Stack>
                </Paper>
              </Box>

              <Box>
                <Typography component="h2" variant="h6" gutterBottom>
                  All open jobs, best match first
                </Typography>
                <Stack component="ol" spacing={1} sx={{ p: 0, listStyle: "none" }}>
                  {matches.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((match) => (
                    <JobRow key={match.id} match={match} />
                  ))}
                </Stack>
                <Pagination
                  count={Math.ceil(matches.length / PAGE_SIZE)}
                  page={page}
                  onChange={(_, value) => setPage(value)}
                  sx={{ mt: 2 }}
                />
              </Box>
            </Stack>
          )}
          {matches && matches.length === 0 && !loading && <Alert severity="info">No open jobs right now.</Alert>}
        </>
      )}
    </Box>
  );
}
