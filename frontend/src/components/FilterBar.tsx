import { useState, type MouseEvent } from "react";
import { Badge, Button, Popover, Stack } from "@mui/material";
import { FIELD_LABELS, isFilterActive, type FilterField } from "../api/jobFilterFields";
import ColumnFilterForm from "./ColumnFilterForm";
import DebouncedField from "./DebouncedField";
import { useJobTable } from "./JobTableContext";

// The filters people reach for most. Every column's own menu still has its filter too.
const QUICK: FilterField[] = ["status", "visa", "source", "arrangement", "work_type", "salary", "listed"];

/** Filters in plain sight above the table: a title search and one button per common filter. */
export default function FilterBar() {
  const { params, update } = useJobTable();
  const [open, setOpen] = useState<{ field: FilterField; anchor: HTMLElement } | null>(null);

  return (
    <Stack direction="row" flexWrap="wrap" alignItems="center" gap={1} sx={{ mb: 1.5 }}>
      <DebouncedField label="Search job titles" value={params.position} onCommit={(value) => update({ position: value })} />
      {QUICK.map((field) => (
        <Badge key={field} color="primary" variant="dot" invisible={!isFilterActive(params, field)}>
          <Button
            size="small"
            variant="outlined"
            color={isFilterActive(params, field) ? "primary" : "inherit"}
            onClick={(event: MouseEvent<HTMLElement>) => setOpen({ field, anchor: event.currentTarget })}
          >
            {FIELD_LABELS[field]}
          </Button>
        </Badge>
      ))}
      <Popover
        open={Boolean(open)}
        anchorEl={open?.anchor}
        onClose={() => setOpen(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        {open && <ColumnFilterForm field={open.field} />}
      </Popover>
    </Stack>
  );
}
