import { Box, Chip, Link, Typography, useMediaQuery } from "@mui/material";
import type { GridColDef } from "@mui/x-data-grid";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { sourceLabel, type JobListItem } from "../api/client";
import { FIELD_LABELS, isFilterActive, type FilterField } from "../api/jobFilterFields";
import { formatRelativeDate } from "../utils/date";
import { formatAnnualRange } from "../utils/salary";
import { useJobTable } from "./JobTableContext";
import StatusChip from "./StatusChip";

function PositionCell({ job }: { job: JobListItem }) {
  const compact = useMediaQuery("(max-width:700px)");
  const location = useLocation();
  return (
    <Box>
      <Link
        component={RouterLink}
        to={`/jobs/${job.id}`}
        state={{ from: `${location.pathname}${location.search}` }}
        underline="hover"
        fontWeight={650}
      >
        {job.position}
      </Link>
      <Box>
        <Chip size="small" variant="outlined" label={sourceLabel(job.source)} sx={{ height: 18, fontSize: 11 }} />
      </Box>
      {compact && (
        <Typography variant="caption" color="text.secondary" display="block">
          {[job.company_name, job.location].filter(Boolean).join(" · ")}
        </Typography>
      )}
    </Box>
  );
}

/** Column title plus a dot when that column is filtered. */
function Header({ field }: { field: FilterField }) {
  const { params } = useJobTable();
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
      <span>{FIELD_LABELS[field]}</span>
      {isFilterActive(params, field) && (
        <Box component="span" role="img" aria-label="filtered" sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: "primary.main" }} />
      )}
    </Box>
  );
}

function column(field: FilterField, rest: Omit<GridColDef<JobListItem>, "field">): GridColDef<JobListItem> {
  return { field, headerName: FIELD_LABELS[field], renderHeader: () => <Header field={field} />, filterable: false, ...rest };
}

/** Field names double as the API's sort keys, so a sort click maps straight to `?sort=`. */
export const jobColumns: GridColDef<JobListItem>[] = [
  column("position", { flex: 1.6, minWidth: 170, renderCell: ({ row }) => <PositionCell job={row} /> }),
  column("status", {
    width: 100,
    renderCell: ({ row }) => (
      <Box>
        <StatusChip isActive={row.is_active} />
        {!row.is_active && row.closed_at && (
          <Typography variant="caption" color="text.secondary" display="block">
            {formatRelativeDate(row.closed_at)}
          </Typography>
        )}
      </Box>
    ),
  }),
  column("company", { flex: 1, minWidth: 110, valueGetter: (_, row) => row.company_name }),
  column("source", { width: 150, valueGetter: (_, row) => sourceLabel(row.source) }),
  column("location", { flex: 1.2, minWidth: 120, valueGetter: (_, row) => row.location || "Not listed" }),
  column("arrangement", { width: 142, valueGetter: (_, row) => row.work_arrangements.join(", ") || "Not listed" }),
  column("work_type", { width: 125, valueGetter: (_, row) => row.work_types.join(", ") || "Not listed" }),
  column("salary", {
    flex: 1.2,
    minWidth: 140,
    renderCell: ({ row }) => {
      const estimate = formatAnnualRange(
        row.annual_salary_min,
        row.annual_salary_max,
        row.salary_label.includes("€") ? "€" : "$",
      );
      return (
        <Box>
          {row.salary_label || "Not listed"}
          {estimate && (
            <Typography variant="caption" color="text.secondary" display="block">
              ≈ {estimate}
            </Typography>
          )}
        </Box>
      );
    },
  }),
  column("visa", {
    width: 120,
    renderCell: ({ row }) =>
      row.visa_sponsor ? <Chip size="small" color="success" variant="outlined" label="Offered" /> : "Not mentioned",
  }),
  column("listed", { width: 110, valueGetter: (_, row) => formatRelativeDate(row.listed_at) }),
];
