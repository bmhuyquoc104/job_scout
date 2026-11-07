import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { getGreenList, getGreenListChanges, type GreenListChange, type GreenListRole } from "../api/client";
import { useApi } from "../api/useApi";

type TierFilter = "all" | "1" | "2";
const CHANGE_DAYS = 90;
const shortDate = (iso: string) => new Date(iso).toLocaleDateString("en-NZ", { day: "numeric", month: "short", year: "numeric" });

function TierChip({ tier }: { tier: number }) {
  return <Chip size="small" variant="outlined" color={tier === 1 ? "primary" : "secondary"} label={`Tier ${tier}`} />;
}

function describeChange(change: GreenListChange): string {
  switch (change.event_type) {
    case "tier_changed":
      return `${change.title}: Tier ${change.from_tier} → Tier ${change.tier}`;
    case "new":
      return `${change.title} added to the list (Tier ${change.tier})`;
    case "removed":
      return `${change.title} removed from the list (was Tier ${change.tier})`;
    default:
      return `${change.title} is back on the list (Tier ${change.tier})`;
  }
}

const columns: GridColDef<GreenListRole>[] = [
  { field: "title", headerName: "Role", flex: 1.6, minWidth: 220 },
  { field: "anzsco_code", headerName: "ANZSCO", width: 110 },
  { field: "industry", headerName: "Industry", flex: 1, minWidth: 180 },
  {
    field: "tier",
    headerName: "Tier",
    width: 190,
    renderCell: ({ row }) => (
      <Stack direction="row" alignItems="center" gap={1}>
        <TierChip tier={row.tier} />
        {row.tier_changed_from && row.tier_changed_at && (
          <Tooltip title={`Moved from Tier ${row.tier_changed_from} on ${shortDate(row.tier_changed_at)}`}>
            <Chip size="small" color="warning" variant="outlined" label={`was ${row.tier_changed_from}`} />
          </Tooltip>
        )}
      </Stack>
    ),
  },
];

function RoleDialog({ role, onClose }: { role: GreenListRole | null; onClose: () => void }) {
  const sections: [string, string][] = role
    ? [
        ["Pathway to residence", role.pathway],
        ["Green List requirements", role.requirements],
        ["Engineering degrees (Washington and Sydney Accords)", role.engineering_degrees],
        ["Note", role.note],
      ]
    : [];
  return (
    <Dialog open={role !== null} onClose={onClose} fullWidth maxWidth="md" aria-labelledby="role-title">
      {role && (
        <>
          <DialogTitle id="role-title">
            <Stack direction="row" alignItems="center" gap={1.5} flexWrap="wrap">
              {role.title}
              <TierChip tier={role.tier} />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              ANZSCO {role.anzsco_code} · {role.industry}
            </Typography>
          </DialogTitle>
          <DialogContent dividers>
            {sections
              .filter(([, text]) => text)
              .map(([heading, text]) => (
                <Box key={heading} sx={{ mb: 2 }}>
                  <Typography variant="overline" color="text.secondary" fontWeight={700}>
                    {heading}
                  </Typography>
                  <Typography sx={{ whiteSpace: "pre-line" }}>{text}</Typography>
                </Box>
              ))}
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>Close</Button>
          </DialogActions>
        </>
      )}
    </Dialog>
  );
}

function ChangesPanel({ changes }: { changes: GreenListChange[] }) {
  const count = (type: string) => changes.filter((change) => change.event_type === type).length;
  return (
    <Paper component="section" aria-label="Recent changes" variant="outlined" sx={{ p: 2, mb: 2, bgcolor: "background.paper" }}>
      <Typography component="h2" variant="subtitle1" fontWeight={700}>
        Changes in the last {CHANGE_DAYS} days
      </Typography>
      {changes.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          No changes yet. The list is checked monthly, and any role that moves tier, is added or is removed will appear here.
        </Typography>
      ) : (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {count("tier_changed")} tier change(s), {count("new") + count("restored")} added, {count("removed")} removed
          </Typography>
          <Box component="ul" sx={{ m: 0, p: 0, listStyle: "none", maxHeight: 220, overflow: "auto" }}>
            {changes.map((change) => (
              <Box
                component="li"
                key={`${change.role_id}-${change.event_type}-${change.occurred_at}`}
                sx={{ display: "flex", justifyContent: "space-between", gap: 2, py: 0.5 }}
              >
                <Typography variant="body2">{describeChange(change)}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ flex: "none" }}>
                  {shortDate(change.occurred_at)}
                </Typography>
              </Box>
            ))}
          </Box>
        </>
      )}
    </Paper>
  );
}

export default function GreenList() {
  const { data, error } = useApi(getGreenList, [], "Unable to load the Green List.");
  const { data: changeData } = useApi(() => getGreenListChanges(CHANGE_DAYS), [], "Unable to load changes.");
  const [tier, setTier] = useState<TierFilter>("all");
  const [industry, setIndustry] = useState("");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<GreenListRole | null>(null);

  const roles = useMemo(() => data?.roles ?? [], [data]);
  const industries = useMemo(() => [...new Set(roles.map((role) => role.industry))].sort(), [roles]);
  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return roles.filter(
      (role) =>
        (tier === "all" || String(role.tier) === tier) &&
        (!industry || role.industry === industry) &&
        (!needle || `${role.title} ${role.anzsco_code} ${role.industry}`.toLowerCase().includes(needle)),
    );
  }, [roles, tier, industry, search]);

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: 3, overflow: "auto" }}>
      <Typography color="primary" variant="overline" fontWeight={700} letterSpacing={1}>
        Immigration New Zealand
      </Typography>
      <Typography component="h1" variant="h4" sx={{ mt: 0.5, mb: 0.5, fontSize: 24, fontWeight: 700 }}>
        Green List
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 760 }}>
        Roles New Zealand needs people for. <b>Tier 1</b> roles can lead to residence straight away (Straight to Residence); <b>Tier 2</b> roles
        after 2 years of work (Work to Residence).
        {data?.synced_at && ` Last checked ${shortDate(data.synced_at)}; it is refreshed monthly.`}
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}
      {data && data.total === 0 && (
        <Alert severity="info">The Green List has not been fetched yet. Run the monthly sync in Airflow to load it.</Alert>
      )}
      {data && data.total > 0 && (
        <>
          <ChangesPanel changes={changeData?.changes ?? []} />
          <Stack direction={{ xs: "column", md: "row" }} gap={1.5} alignItems={{ md: "center" }} sx={{ mb: 1.5 }}>
            <ToggleButtonGroup
              exclusive
              size="small"
              color="primary"
              value={tier}
              aria-label="Tier"
              onChange={(_, next: TierFilter | null) => next && setTier(next)}
            >
              <ToggleButton value="all" sx={{ textTransform: "none", px: 2 }}>
                All · {data.total}
              </ToggleButton>
              <ToggleButton value="1" sx={{ textTransform: "none", px: 2 }}>
                Tier 1 · {data.tier_1}
              </ToggleButton>
              <ToggleButton value="2" sx={{ textTransform: "none", px: 2 }}>
                Tier 2 · {data.tier_2}
              </ToggleButton>
            </ToggleButtonGroup>
            <TextField size="small" label="Search roles" value={search} onChange={(event) => setSearch(event.target.value)} sx={{ minWidth: 220 }} />
            <TextField select size="small" label="Industry" value={industry} onChange={(event) => setIndustry(event.target.value)} sx={{ minWidth: 260 }}>
              <MenuItem value="">All industries</MenuItem>
              {industries.map((name) => (
                <MenuItem key={name} value={name}>
                  {name}
                </MenuItem>
              ))}
            </TextField>
            <Typography variant="body2" color="text.secondary">
              {visible.length} role(s)
            </Typography>
          </Stack>
          <Box sx={{ height: 560 }}>
            <DataGrid
              aria-label="Green List roles"
              rows={visible}
              columns={columns}
              pageSizeOptions={[25, 50, 100]}
              initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
              onRowClick={({ row }) => setOpen(row)}
              disableRowSelectionOnClick
              disableColumnFilter
              getRowHeight={() => "auto"}
              getEstimatedRowHeight={() => 52}
              localeText={{ noRowsLabel: "No roles match these filters." }}
              sx={{
                bgcolor: "background.paper",
                borderColor: "divider",
                cursor: "pointer",
                "& .MuiDataGrid-cell": { display: "flex", alignItems: "center", py: 1, whiteSpace: "normal", lineHeight: 1.4 },
              }}
            />
          </Box>
        </>
      )}
      <RoleDialog role={open} onClose={() => setOpen(null)} />
    </Box>
  );
}
