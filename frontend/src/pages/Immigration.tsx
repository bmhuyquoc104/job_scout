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
import { Link as RouterLink } from "react-router-dom";
import { useApi } from "../api/useApi";
import { useCountry } from "../country/CountryContext";

const CHANGE_DAYS = 90;
const shortDate = (iso: string) => new Date(iso).toLocaleDateString("en-NZ", { day: "numeric", month: "short", year: "numeric" });
// Australia's lists in the order that matters for employers: CSOL first.
const LIST_ORDER = ["CSOL", "MLTSSL", "STSOL", "ROL", "RSMS ROL"];
const LIST_HELP: Record<string, string> = {
  CSOL: "Core Skills Occupation List: occupations an employer can sponsor (Skills in Demand 482 and Employer Nomination 186 visas)",
  MLTSSL: "Medium and Long-term Strategic Skills List",
  STSOL: "Short-term Skilled Occupation List",
  ROL: "Regional Occupation List",
  "RSMS ROL": "Regional Sponsored Migration Scheme occupation list",
};

function TierChip({ tier }: { tier: number }) {
  return <Chip size="small" variant="outlined" color={tier === 1 ? "primary" : "secondary"} label={`Tier ${tier}`} />;
}

function ListChips({ lists }: { lists: string[] }) {
  return (
    <Stack direction="row" gap={0.5} flexWrap="wrap">
      {lists.map((name) => (
        <Tooltip key={name} title={LIST_HELP[name] ?? name}>
          <Chip size="small" variant="outlined" color={name === "CSOL" ? "primary" : "default"} label={name} />
        </Tooltip>
      ))}
    </Stack>
  );
}

function describeChange(change: GreenListChange): string {
  const tier = change.tier ? ` (Tier ${change.tier})` : "";
  switch (change.event_type) {
    case "tier_changed":
      return `${change.title}: Tier ${change.from_tier} → Tier ${change.tier}`;
    case "new":
      return `${change.title} added to the list${tier}`;
    case "removed":
      return `${change.title} removed from the list${tier ? ` (was Tier ${change.tier})` : ""}`;
    default:
      return `${change.title} is back on the list${tier}`;
  }
}

const baseColumns: GridColDef<GreenListRole>[] = [
  { field: "title", headerName: "Role", flex: 1.6, minWidth: 220 },
  { field: "anzsco_code", headerName: "ANZSCO", width: 110 },
  { field: "industry", headerName: "Industry", flex: 1, minWidth: 180 },
];

const tierColumn: GridColDef<GreenListRole> = {
  field: "tier",
  headerName: "Tier",
  width: 190,
  renderCell: ({ row }) => (
    <Stack direction="row" alignItems="center" gap={1}>
      {row.tier !== null && <TierChip tier={row.tier} />}
      {row.tier_changed_from && row.tier_changed_at && (
        <Tooltip title={`Moved from Tier ${row.tier_changed_from} on ${shortDate(row.tier_changed_at)}`}>
          <Chip size="small" color="warning" variant="outlined" label={`was ${row.tier_changed_from}`} />
        </Tooltip>
      )}
    </Stack>
  ),
};

const listsColumn: GridColDef<GreenListRole> = {
  field: "lists",
  headerName: "Lists",
  flex: 1,
  minWidth: 200,
  sortable: false,
  renderCell: ({ row }) => <ListChips lists={row.lists} />,
};

function RoleDialog({ role, hasTiers, onClose }: { role: GreenListRole | null; hasTiers: boolean; onClose: () => void }) {
  const sections: [string, string][] = role
    ? hasTiers
      ? [
          ["Pathway to residence", role.pathway],
          ["Green List requirements", role.requirements],
          ["Engineering degrees (Washington and Sydney Accords)", role.engineering_degrees],
          ["Note", role.note],
        ]
      : [
          ["Visas this occupation can be used for", role.pathway.replaceAll("; ", "\n")],
          ["Skills assessment", role.requirements],
        ]
    : [];
  return (
    <Dialog open={role !== null} onClose={onClose} fullWidth maxWidth="md" aria-labelledby="role-title">
      {role && (
        <>
          <DialogTitle id="role-title">
            <Stack direction="row" alignItems="center" gap={1.5} flexWrap="wrap">
              {role.title}
              {role.tier !== null && <TierChip tier={role.tier} />}
              {role.lists.length > 0 && <ListChips lists={role.lists} />}
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

function ChangesPanel({ changes, hasTiers }: { changes: GreenListChange[]; hasTiers: boolean }) {
  const count = (type: string) => changes.filter((change) => change.event_type === type).length;
  return (
    <Paper component="section" aria-label="Recent changes" variant="outlined" sx={{ p: 2, mb: 2, bgcolor: "background.paper" }}>
      <Typography component="h2" variant="subtitle1" fontWeight={700}>
        Changes in the last {CHANGE_DAYS} days
      </Typography>
      {changes.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          No changes yet. The list is checked monthly, and any role that {hasTiers ? "moves tier, " : ""}is added or is removed will appear here.
        </Typography>
      ) : (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {hasTiers ? `${count("tier_changed")} tier change(s), ` : ""}
            {count("new") + count("restored")} added, {count("removed")} removed
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

export default function Immigration() {
  const { country, countryName } = useCountry();
  const { data, error } = useApi(() => getGreenList(country), [country], "Unable to load the immigration list.");
  const { data: changeData } = useApi(() => getGreenListChanges(CHANGE_DAYS, country), [country], "Unable to load changes.");
  // "all", a tier ("1"/"2", New Zealand) or a list name ("CSOL", Australia).
  const [filter, setFilter] = useState<{ country: string; value: string | null }>({ country, value: null });
  const [industry, setIndustry] = useState("");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<GreenListRole | null>(null);

  const roles = useMemo(() => data?.roles ?? [], [data]);
  const hasTiers = (data?.tier_1 ?? 0) + (data?.tier_2 ?? 0) > 0;
  const listNames = useMemo(
    () => Object.keys(data?.list_counts ?? {}).sort((a, b) => (LIST_ORDER.indexOf(a) + 1 || 99) - (LIST_ORDER.indexOf(b) + 1 || 99)),
    [data],
  );
  // Australia opens on CSOL, the employer-sponsored list; a country switch resets the choice.
  const defaultFilter = listNames.includes("CSOL") ? "CSOL" : "all";
  const active = (filter.country === country ? filter.value : null) ?? defaultFilter;
  const industries = useMemo(() => [...new Set(roles.map((role) => role.industry))].filter(Boolean).sort(), [roles]);
  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return roles.filter(
      (role) =>
        (active === "all" || String(role.tier) === active || role.lists.includes(active)) &&
        (!industry || role.industry === industry) &&
        (!needle || `${role.title} ${role.anzsco_code} ${role.industry} ${role.lists.join(" ")}`.toLowerCase().includes(needle)),
    );
  }, [roles, active, industry, search]);

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: 3, overflow: "auto" }}>
      <Typography color="primary" variant="overline" fontWeight={700} letterSpacing={1}>
        {data?.source_name ?? countryName}
      </Typography>
      <Typography component="h1" variant="h4" sx={{ mt: 0.5, mb: 0.5, fontSize: 24, fontWeight: 700 }}>
        {data?.list_name ?? "Immigration occupations"}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 760 }}>
        {hasTiers ? (
          <>
            Roles {countryName} needs people for. <b>Tier 1</b> roles can lead to residence straight away (Straight to Residence); <b>Tier 2</b>{" "}
            roles after 2 years of work (Work to Residence).
          </>
        ) : (
          <>
            Occupations {countryName} lists for skilled migration. <b>CSOL</b> roles can be sponsored by an employer; the other lists relate to
            skilled and regional visas. Select a role to see its visas.
          </>
        )}
        {data?.synced_at && ` Last checked ${shortDate(data.synced_at)}; it is refreshed monthly.`}
      </Typography>
      <Button component={RouterLink} to="/compare-routes" variant="outlined" size="small" sx={{ mb: 2 }}>
        Compare routes for a job across countries →
      </Button>
      {error && <Alert severity="error">{error}</Alert>}
      {data && data.total === 0 && (
        <Alert severity="info">The {countryName} list has not been fetched yet. Run the monthly sync in Airflow to load it.</Alert>
      )}
      {data && data.total > 0 && (
        <>
          <ChangesPanel changes={changeData?.changes ?? []} hasTiers={hasTiers} />
          <Stack direction={{ xs: "column", md: "row" }} gap={1.5} alignItems={{ md: "center" }} flexWrap="wrap" sx={{ mb: 1.5 }}>
            <ToggleButtonGroup
              exclusive
              size="small"
              color="primary"
              value={active}
              aria-label={hasTiers ? "Tier" : "List"}
              onChange={(_, next: string | null) => next && setFilter({ country, value: next })}
            >
              <ToggleButton value="all" sx={{ textTransform: "none", px: 2 }}>
                All · {data.total}
              </ToggleButton>
              {hasTiers
                ? [
                    <ToggleButton key="1" value="1" sx={{ textTransform: "none", px: 2 }}>
                      Tier 1 · {data.tier_1}
                    </ToggleButton>,
                    <ToggleButton key="2" value="2" sx={{ textTransform: "none", px: 2 }}>
                      Tier 2 · {data.tier_2}
                    </ToggleButton>,
                  ]
                : listNames.map((name) => (
                    <ToggleButton key={name} value={name} sx={{ textTransform: "none", px: 2 }}>
                      {name} · {data.list_counts[name]}
                    </ToggleButton>
                  ))}
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
              aria-label={`${data.list_name} roles`}
              rows={visible}
              columns={[...baseColumns, hasTiers ? tierColumn : listsColumn]}
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
      <RoleDialog role={open} hasTiers={hasTiers} onClose={() => setOpen(null)} />
    </Box>
  );
}
