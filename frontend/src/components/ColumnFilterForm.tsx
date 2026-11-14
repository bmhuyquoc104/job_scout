import { useState } from "react";
import { Box, Button, Checkbox, FormControlLabel, FormGroup, Radio, RadioGroup, TextField, Typography } from "@mui/material";
import { SOURCE_LABELS, type JobSource, type JobStatus } from "../api/client";
import { FIELD_LABELS, clearFilter, isFilterActive, type FilterField } from "../api/jobFilterFields";
import type { SalaryFilter, VisaFilter } from "../api/jobParams";
import DebouncedField from "./DebouncedField";
import { useJobTable } from "./JobTableContext";

const STATUS_OPTIONS: { value: JobStatus; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
];
const VISA_OPTIONS: { value: VisaFilter; label: string }[] = [
  { value: "any", label: "Any" },
  { value: "offered", label: "Offered" },
  { value: "not_mentioned", label: "Not mentioned" },
];
const SALARY_OPTIONS: { value: SalaryFilter; label: string }[] = [
  { value: "any", label: "Any" },
  { value: "listed", label: "Has a figure" },
  { value: "unlisted", label: "No figure" },
];

/** The filter controls for one column, shown inside that column's menu. */
export default function ColumnFilterForm({ field }: { field: FilterField }) {
  const { params, facets, update } = useJobTable();
  const [resetCount, setResetCount] = useState(0); // remounts the text boxes after "Clear filter"
  const active = isFilterActive(params, field);

  function toggle(key: "arrangement" | "work_type", option: string) {
    const current = params[key];
    update({ [key]: current.includes(option) ? current.filter((value) => value !== option) : [...current, option] });
  }

  function checklist(key: "arrangement" | "work_type", known: string[] = []) {
    const options = [...new Set([...known, ...params[key]])].sort();
    return (
      <FormGroup>
        {options.map((option) => (
          <FormControlLabel
            key={option}
            label={option}
            control={<Checkbox size="small" checked={params[key].includes(option)} onChange={() => toggle(key, option)} />}
          />
        ))}
      </FormGroup>
    );
  }

  let control;
  switch (field) {
    case "position":
    case "company":
    case "location":
      control = (
        <DebouncedField
          key={resetCount}
          autoFocus
          label={`${FIELD_LABELS[field]} contains`}
          value={params[field]}
          onCommit={(value) => update({ [field]: value })}
        />
      );
      break;
    case "status":
      control = (
        <RadioGroup value={params.status} onChange={(event) => update({ status: event.target.value as JobStatus })}>
          {STATUS_OPTIONS.map((option) => (
            <FormControlLabel key={option.value} value={option.value} label={option.label} control={<Radio size="small" />} />
          ))}
        </RadioGroup>
      );
      break;
    case "source":
      control = (
        <RadioGroup value={params.source} onChange={(event) => update({ source: event.target.value as JobSource | "" })}>
          {[["", "All sources"], ...Object.entries(SOURCE_LABELS)].map(([value, label]) => (
            <FormControlLabel key={value} value={value} label={label} control={<Radio size="small" />} />
          ))}
        </RadioGroup>
      );
      break;
    case "visa":
      control = (
        <RadioGroup value={params.visa} onChange={(event) => update({ visa: event.target.value as VisaFilter })}>
          {VISA_OPTIONS.map((option) => (
            <FormControlLabel key={option.value} value={option.value} label={option.label} control={<Radio size="small" />} />
          ))}
        </RadioGroup>
      );
      break;
    case "arrangement":
      control = checklist("arrangement", facets?.arrangements);
      break;
    case "work_type":
      control = checklist("work_type", facets?.work_types);
      break;
    case "salary":
      control = (
        <>
          <RadioGroup value={params.salary} onChange={(event) => update({ salary: event.target.value as SalaryFilter })}>
            {SALARY_OPTIONS.map((option) => (
              <FormControlLabel key={option.value} value={option.value} label={option.label} control={<Radio size="small" />} />
            ))}
          </RadioGroup>
          <Box sx={{ mt: 1 }}>
            <DebouncedField
              key={resetCount}
              type="number"
              label="Min salary (NZD/yr)"
              value={params.min_salary}
              onCommit={(value) => update({ min_salary: value })}
            />
          </Box>
        </>
      );
      break;
    case "listed":
      control = (
        <Box sx={{ display: "grid", gap: 1.25 }}>
          <TextField
            size="small"
            type="date"
            label="Listed from"
            value={params.listed_from}
            onChange={(event) => update({ listed_from: event.target.value })}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            size="small"
            type="date"
            label="Listed to"
            value={params.listed_to}
            onChange={(event) => update({ listed_to: event.target.value })}
            slotProps={{ inputLabel: { shrink: true } }}
          />
        </Box>
      );
      break;
  }

  return (
    <Box
      // The menu list treats typed letters and Tab as navigation; keep them for the inputs (Escape still closes).
      onKeyDown={(event) => {
        if (event.key !== "Escape") event.stopPropagation();
      }}
      sx={{ px: 2, py: 1.25, width: 270 }}
    >
      <Typography variant="overline" color="text.secondary" fontWeight={700}>
        Filter
      </Typography>
      <Box sx={{ mt: 0.5 }}>{control}</Box>
      {active && (
        <Button
          size="small"
          sx={{ mt: 1 }}
          onClick={() => {
            update(clearFilter(field));
            setResetCount((count) => count + 1);
          }}
        >
          Clear filter
        </Button>
      )}
    </Box>
  );
}
