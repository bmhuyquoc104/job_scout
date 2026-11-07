import { useLocation, Link as RouterLink, useParams } from "react-router-dom";
import {
  Alert,
  Box,
  CircularProgress,
  Divider,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { getJob, sourceLabel } from "../api/client";
import { useApi } from "../api/useApi";
import StatusChip from "../components/StatusChip";
import { formatRelativeDate } from "../utils/date";

export default function JobDetailPage() {
  const { jobId = "" } = useParams();
  const location = useLocation();
  const { data: job, error, loading } = useApi(() => getJob(jobId), [jobId], "Unable to load job.");

  const backTo = location.state?.from ?? (job ? `/categories/${job.category_id}` : "/");

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: 3, overflow: "auto" }}>
      <Link component={RouterLink} to={backTo} underline="hover" sx={{ display: "inline-block", mb: 1.75 }}>
        ← Category jobs
      </Link>
      {loading && <CircularProgress aria-label="Loading job" size={24} />}
      {error && <Alert severity="error">{error}</Alert>}
      {job && (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) 250px" }, gap: 3 }}>
          <Box component="article">
            <Stack direction="row" alignItems="center" gap={1}>
              <Typography color="primary" variant="overline" fontWeight={700}>{job.work_types.join(", ")}</Typography>
              <StatusChip isActive={job.is_active} />
            </Stack>
            <Typography component="h1" variant="h4" sx={{ mt: 0.5, mb: 0.5, fontSize: 24, fontWeight: 700 }}>
              {job.position}
            </Typography>
            {!job.is_active && (
              <Alert severity="info" sx={{ my: 1.5 }}>
                This listing is closed: {sourceLabel(job.source)} no longer shows it
                {job.closed_at ? ` (${formatRelativeDate(job.closed_at)})` : ""}.
              </Alert>
            )}
            <Typography color="text.secondary" variant="body2">
              {job.company_name} · {job.location || "Location not listed"} · Listed {formatRelativeDate(job.listed_at)}
            </Typography>
            <Divider sx={{ my: 2.25 }} />
            <Typography component="h2" variant="h6" fontWeight={700} sx={{ mb: 1.5 }}>Job description</Typography>
            <Typography color="text.secondary" sx={{ lineHeight: 1.65, whiteSpace: "pre-wrap", mb: 2.5 }}>
              {job.job_description || "No description available."}
            </Typography>
            <Link href={job.url} target="_blank" rel="noreferrer" underline="hover">
              Open original {sourceLabel(job.source)} listing ↗
            </Link>
          </Box>
          <Paper component="aside" variant="outlined" aria-label="Job details" sx={{ p: 2.25, alignSelf: "start", bgcolor: "background.paper" }}>
            <Stack component="dl" spacing={1.75} sx={{ m: 0 }}>
              <Box><Typography component="dt" variant="overline" color="text.secondary">Source</Typography><Typography component="dd" sx={{ m: 0 }}>{sourceLabel(job.source)}</Typography></Box>
              <Box><Typography component="dt" variant="overline" color="text.secondary">Salary</Typography><Typography component="dd" sx={{ m: 0 }}>{job.salary_label || "Not listed"}</Typography></Box>
              <Box><Typography component="dt" variant="overline" color="text.secondary">Pay period</Typography><Typography component="dd" sx={{ m: 0 }}>{job.pay_period || "Not listed"}</Typography></Box>
              <Box><Typography component="dt" variant="overline" color="text.secondary">Work arrangement</Typography><Typography component="dd" sx={{ m: 0 }}>{job.work_arrangements.join(", ") || "Not listed"}</Typography></Box>
              <Box><Typography component="dt" variant="overline" color="text.secondary">Work type</Typography><Typography component="dd" sx={{ m: 0 }}>{job.work_types.join(", ") || "Not listed"}</Typography></Box>
              <Box><Typography component="dt" variant="overline" color="text.secondary">NZBN</Typography><Typography component="dd" sx={{ m: 0 }}>{job.nzbn || "Not listed"}</Typography></Box>
              <Box><Typography component="dt" variant="overline" color="text.secondary">Trading name</Typography><Typography component="dd" sx={{ m: 0, overflowWrap: "anywhere" }}>{job.trading_name || "Not listed"}</Typography></Box>
            </Stack>
          </Paper>
        </Box>
      )}
    </Box>
  );
}
