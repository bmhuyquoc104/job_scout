import { Button, Chip, Stack } from "@mui/material";
import {
  FIELD_LABELS,
  FILTER_FIELDS,
  clearAllFilters,
  clearFilter,
  describeFilter,
  isFilterActive,
} from "../api/jobFilterFields";
import { useJobTable } from "./JobTableContext";

/** One removable chip per filtered column, so the filters hidden in the column menus stay visible. */
export default function ActiveFilters() {
  const { params, update } = useJobTable();
  const active = FILTER_FIELDS.filter((field) => isFilterActive(params, field));
  if (active.length === 0) return null;

  return (
    <Stack direction="row" flexWrap="wrap" alignItems="center" gap={1} role="list" aria-label="Active filters" sx={{ mb: 1.5 }}>
      {active.map((field) => (
        <Chip
          key={field}
          role="listitem"
          size="small"
          variant="outlined"
          color="primary"
          label={`${FIELD_LABELS[field]}: ${describeFilter(params, field)}`}
          onDelete={() => update(clearFilter(field))}
        />
      ))}
      <Button size="small" onClick={() => update(clearAllFilters())}>
        Clear all
      </Button>
    </Stack>
  );
}
