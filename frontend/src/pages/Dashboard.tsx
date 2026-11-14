import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import { getVisaStats } from "../api/client";
import { useApi } from "../api/useApi";
import EntryCard from "../components/EntryCard";
import PageHeader from "../components/PageHeader";
import { useCountry } from "../country/CountryContext";

const TOOLS = [
  { to: "/recommended-jobs", title: "Recommended jobs", text: "Open jobs ranked against your CV, in every country." },
  { to: "/recommended-jobs?visa=1", title: "Jobs with visa sponsorship", text: "Your best matches among ads that offer sponsorship." },
  { to: "/analytics", title: "Compare a job across countries", text: "Open jobs, pay and sources for one job title." },
  { to: "/compare-routes", title: "Compare immigration routes", text: "Each country's priority list and routes for a job." },
];

const GRID = { display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" }, gap: 1.5 };

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <Box component="section" sx={{ mb: 4 }}>
      <Typography variant="h5" component="h2">
        {title}
      </Typography>
      {hint && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
          {hint}
        </Typography>
      )}
      <Box sx={{ mt: 1.5 }}>{children}</Box>
    </Box>
  );
}

export default function Dashboard() {
  const { categories, countryCategories, countries, country, countryName, setCountry, error, loading } = useCountry();
  const { data: visa } = useApi(getVisaStats, [], "Unable to load visa sponsorship counts.");

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: { xs: 2, md: 3 }, overflow: "auto" }}>
      <PageHeader
        title="Dashboard"
        subtitle="Open jobs and immigration routes across countries. Pick a country to browse its jobs."
      />
      {loading && <CircularProgress aria-label="Loading categories" size={24} />}
      {error && <Alert severity="error">{error}</Alert>}

      <Section title="Countries at a glance" hint="Open jobs now, and how many ads mention visa sponsorship.">
        <Box sx={GRID}>
          {countries.map((option) => {
            const stats = visa?.find((item) => item.country === option.code);
            const first = categories.find((category) => category.country === option.code);
            return (
              <EntryCard
                key={option.code}
                to={first ? `/categories/${first.id}` : "/"}
                title={option.name}
                highlighted={option.code === country}
                onClick={() => setCountry(option.code)}
              >
                <Typography variant="h5" component="p">
                  {stats ? stats.open_jobs.toLocaleString() : "…"}
                  <Typography component="span" variant="body2" color="text.secondary">
                    {" "}open jobs
                  </Typography>
                </Typography>
                {stats && stats.open_jobs > 0 && (
                  <Typography variant="caption" color="success.main" component="p" sx={{ mt: 0.75 }}>
                    {stats.visa_sponsor.toLocaleString()} offer visa sponsorship ({((100 * stats.visa_sponsor) / stats.open_jobs).toFixed(1)}%)
                  </Typography>
                )}
              </EntryCard>
            );
          })}
        </Box>
      </Section>

      <Section title="Tools" hint="Compare countries and match jobs to your CV.">
        <Box sx={GRID}>
          {TOOLS.map((tool) => (
            <EntryCard key={tool.to} {...tool} />
          ))}
        </Box>
      </Section>

      <Section title={`Job categories in ${countryName}`}>
        {!loading && !error && countryCategories.length === 0 && (
          <Typography color="text.secondary">No categories available.</Typography>
        )}
        <Box sx={GRID}>
          {countryCategories.map((category) => (
            <EntryCard
              key={category.id}
              to={`/categories/${category.id}`}
              title={category.name}
              text={`${category.active_job_count.toLocaleString()} open jobs`}
            />
          ))}
        </Box>
      </Section>
    </Box>
  );
}
