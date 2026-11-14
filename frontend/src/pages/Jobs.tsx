import { useMemo, useState } from "react";
import { Alert, Box, useMediaQuery } from "@mui/material";
import { DataGrid, type GridColumnVisibilityModel, type GridPaginationModel, type GridSortModel } from "@mui/x-data-grid";
import { useParams, useSearchParams } from "react-router-dom";
import { getCategoryJobs, getJobFacets } from "../api/client";
import {
  PAGE_SIZE,
  hasActiveFilters,
  parseParams,
  toApiQuery,
  toSearchParams,
  type JobParams,
  type SortKey,
} from "../api/jobParams";
import { useApi } from "../api/useApi";
import ActiveFilters from "../components/ActiveFilters";
import CategorySwitcher from "../components/CategorySwitcher";
import FilterBar from "../components/FilterBar";
import PageHeader from "../components/PageHeader";
import { useCountry } from "../country/CountryContext";
import ImmigrationRoutes from "../components/ImmigrationRoutes";
import JobColumnMenu from "../components/JobColumnMenu";
import { JobTableContext } from "../components/JobTableContext";
import { jobColumns } from "../components/jobColumns";

export default function Jobs() {
  const { categoryId = "" } = useParams();
  const { country } = useCountry();
  // Source, arrangement and work type fit only on wide screens; their filters stay in the bar above.
  const wide = useMediaQuery("(min-width:1500px)");
  const compact = useMediaQuery("(max-width:700px)"); // phones: company and location move under the title
  const [chosenColumns, setChosenColumns] = useState<GridColumnVisibilityModel | null>(null);
  const columnVisibility = chosenColumns ?? {
    source: wide,
    arrangement: wide,
    work_type: wide,
    company: !compact,
    location: !compact,
    salary: !compact,
    listed: !compact,
  };
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useMemo(() => parseParams(searchParams), [searchParams]);
  const query = toApiQuery(params);

  const { data: result, error, loading } = useApi(
    () => getCategoryJobs(categoryId, query),
    [categoryId, query],
    "Unable to load jobs.",
  );
  const { data: facets } = useApi(() => getJobFacets(categoryId), [categoryId], "Unable to load filters.");

  /** Any change goes back to page 1 unless it sets the offset itself. */
  function update(changes: Partial<JobParams>) {
    setSearchParams(toSearchParams({ ...params, offset: 0, ...changes }));
  }

  // Stable objects: the grid reports a "change" when it is handed a new one, even if equal.
  const sortModel = useMemo<GridSortModel>(() => [{ field: params.sort, sort: params.order }], [params.sort, params.order]);
  const paginationModel = useMemo<GridPaginationModel>(
    () => ({ page: Math.floor(params.offset / PAGE_SIZE), pageSize: PAGE_SIZE }),
    [params.offset],
  );

  return (
    <JobTableContext.Provider value={{ params, facets, update }}>
      <Box
        component="main"
        sx={{ display: "flex", flex: 1, minWidth: 0, minHeight: 0, flexDirection: "column", p: { xs: 2, md: 3 }, overflow: "auto" }}
      >
        <CategorySwitcher categoryId={categoryId} view="postings" />
        <PageHeader
          title={country === "NZ" ? "Accredited jobs" : "Jobs"}
          subtitle={
            country === "NZ"
              ? "Open and closed ads from employers accredited by Immigration New Zealand."
              : "Open and closed ads for this category."
          }
        />
        <FilterBar />
        <ActiveFilters />
        {error && <Alert severity="error">{error}</Alert>}
        {params.position.trim() && <ImmigrationRoutes title={params.position.trim()} />}
        <Box sx={{ flex: 1, minHeight: 420 }}>
          <DataGrid
            aria-label={`${result?.category_name ?? "Job"} listings`}
            columns={jobColumns}
            rows={result?.items ?? []}
            rowCount={result?.total ?? 0}
            loading={loading}
            // Sorting, filtering and paging all run on the server, so they cover every job.
            sortingMode="server"
            sortingOrder={["asc", "desc"]}
            sortModel={sortModel}
            onSortModelChange={(model) => {
              const [item] = model;
              // Only a real change: update() goes back to page 1.
              if (item?.sort && (item.field !== params.sort || item.sort !== params.order)) {
                update({ sort: item.field as SortKey, order: item.sort });
              }
            }}
            filterMode="server"
            paginationMode="server"
            paginationModel={paginationModel}
            onPaginationModelChange={(model) => {
              if (model.page * PAGE_SIZE !== params.offset) update({ offset: model.page * PAGE_SIZE });
            }}
            pageSizeOptions={[PAGE_SIZE]}
            columnVisibilityModel={columnVisibility}
            onColumnVisibilityModelChange={setChosenColumns}
            slots={{ columnMenu: JobColumnMenu }}
            slotProps={{ row: { "data-testid": "job-row" } as object }}
            localeText={{ noRowsLabel: hasActiveFilters(params) ? "No jobs match these filters." : "No jobs found." }}
            getRowHeight={() => "auto"}
            getEstimatedRowHeight={() => 64}
            columnHeaderHeight={48}
            disableRowSelectionOnClick
            hideFooterSelectedRowCount
            sx={{
              bgcolor: "background.paper",
              borderColor: "divider",
              "& .MuiDataGrid-cell": { display: "flex", alignItems: "center", py: 1, whiteSpace: "normal", lineHeight: 1.4 },
              // Keep the column menu button visible so it is obvious where sort and filter live.
              "& .MuiDataGrid-columnHeader .MuiDataGrid-menuIcon": { visibility: "visible", width: "auto" },
            }}
          />
        </Box>
      </Box>
    </JobTableContext.Provider>
  );
}
