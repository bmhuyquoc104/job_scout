import type { ReactNode } from "react";
import { useLocation, useParams } from "react-router-dom";
import { Alert, Box, Button, Chip, CircularProgress, Paper, Stack, Typography } from "@mui/material";
import { getJob, sourceLabel } from "../api/client";
import { useApi } from "../api/useApi";
import PageHeader from "../components/PageHeader";
import StatusChip from "../components/StatusChip";
import { formatRelativeDate } from "../utils/date";

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box>
      <Typography component="dt" variant="overline" color="text.secondary">
        {label}
      </Typography>
      <Typography component="dd" sx={{ m: 0, overflowWrap: "anywhere" }}>
        {children}
      </Typography>
    </Box>
  );
}

export default function JobDetailPage() {
  const { jobId = "" } = useParams();
  const location = useLocation();
  const { data: job, error, loading } = useApi(() => getJob(jobId), [jobId], "Unable to load job.");

  const from: string | undefined = location.state?.from;
  const back = { to: from ?? (job ? `/categories/${job.category_id}` : "/"), label: from ? "Back to results" : "All jobs in this category" };

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: { xs: 2, md: 3 }, overflow: "auto" }}>
      {loading && <CircularProgress aria-label="Loading job" size={24} />}
      {error && <Alert severity="error">{error}</Alert>}
      {job && (
        <>
          <PageHeader
            back={back}
            eyebrow={job.work_types.join(", ") || undefined}
            title={job.position}
            subtitle={`${job.company_name} · ${job.location || "Location not listed"} · Listed ${formatRelativeDate(job.listed_at)}`}
            actions={
              <Button href={job.url} target="_blank" rel="noreferrer" variant="contained">
                View original listing ↗
              </Button>
            }
          />
          <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: -1.5, mb: 3 }}>
            <StatusChip isActive={job.is_active} />
            {job.visa_sponsor && <Chip size="small" color="success" variant="outlined" label="Visa sponsorship mentioned" />}
            {job.required_years !== null && (
              <Chip size="small" variant="outlined" label={job.required_years === 0 ? "No experience needed" : `Asks ${job.required_years}+ years experience`} />
            )}
          </Stack>
          {!job.is_active && (
            <Alert severity="info" sx={{ mb: 2.5, maxWidth: 760 }}>
              This listing is closed: {sourceLabel(job.source)} no longer shows it
              {job.closed_at ? ` (${formatRelativeDate(job.closed_at)})` : ""}.
            </Alert>
          )}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 280px" }, gap: 3, alignItems: "start" }}>
            <Paper component="article" variant="outlined" sx={{ p: { xs: 2, md: 3 }, bgcolor: "background.paper" }}>
              <Typography variant="h6" component="h2" sx={{ mb: 1.5 }}>
                Job description
              </Typography>
              <Typography color="text.secondary" sx={{ lineHeight: 1.7, whiteSpace: "pre-wrap", maxWidth: 760 }}>
                {job.job_description || "No description available."}
              </Typography>
            </Paper>
            <Paper component="aside" variant="outlined" aria-label="Job details" sx={{ p: 2.25, bgcolor: "background.paper" }}>
              <Stack component="dl" spacing={1.5} sx={{ m: 0 }}>
                <Fact label="Salary">{job.salary_label || "Not listed"}</Fact>
                <Fact label="Pay period">{job.pay_period || "Not listed"}</Fact>
                <Fact label="Work arrangement">{job.work_arrangements.join(", ") || "Not listed"}</Fact>
                <Fact label="Work type">{job.work_types.join(", ") || "Not listed"}</Fact>
                <Fact label="Source">{sourceLabel(job.source)}</Fact>
                {/* Both come from the Immigration NZ lookup, so they are empty for other countries. */}
                {(job.nzbn || job.trading_name) && (
                  <>
                    <Fact label="NZBN">{job.nzbn || "Not listed"}</Fact>
                    <Fact label="Trading name">{job.trading_name || "Not listed"}</Fact>
                  </>
                )}
              </Stack>
            </Paper>
          </Box>
        </>
      )}
    </Box>
  );
}
