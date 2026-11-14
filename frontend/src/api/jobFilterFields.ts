import { sourceLabel } from "./client";
import { DEFAULT_PARAMS, type JobParams } from "./jobParams";

/** The columns that can be filtered, in table order. Each owns one or more URL parameters. */
export const FILTER_FIELDS = [
  "position",
  "status",
  "company",
  "location",
  "arrangement",
  "work_type",
  "salary",
  "listed",
  "source",
  "visa",
] as const;
export type FilterField = (typeof FILTER_FIELDS)[number];

const KEYS: Record<FilterField, (keyof JobParams)[]> = {
  position: ["position"],
  status: ["status"],
  company: ["company"],
  location: ["location"],
  arrangement: ["arrangement"],
  work_type: ["work_type"],
  salary: ["salary", "min_salary"],
  listed: ["listed_from", "listed_to"],
  source: ["source"],
  visa: ["visa"],
};

export const FIELD_LABELS: Record<FilterField, string> = {
  position: "Position",
  status: "Status",
  company: "Company",
  location: "Location",
  arrangement: "Arrangement",
  work_type: "Work type",
  salary: "Salary",
  listed: "Date",
  source: "Source",
  visa: "Visa",
};

export function isFilterField(field: string): field is FilterField {
  return (FILTER_FIELDS as readonly string[]).includes(field);
}

export function isFilterActive(params: JobParams, field: FilterField): boolean {
  return KEYS[field].some((key) => {
    const value = params[key];
    return Array.isArray(value) ? value.length > 0 : value !== DEFAULT_PARAMS[key];
  });
}

/** Parameter values that remove one column's filter. */
export function clearFilter(field: FilterField): Partial<JobParams> {
  return Object.fromEntries(KEYS[field].map((key) => [key, DEFAULT_PARAMS[key]]));
}

export function clearAllFilters(): Partial<JobParams> {
  return Object.assign({}, ...FILTER_FIELDS.map(clearFilter));
}

const STATUS_LABELS = { open: "Open", closed: "Closed", all: "All" };
const SALARY_LABELS = { any: "any", listed: "has a figure", unlisted: "no figure" };
const VISA_LABELS = { any: "any", offered: "offered", not_mentioned: "not mentioned" };

/** Short text for the active-filter chip of a column. */
export function describeFilter(params: JobParams, field: FilterField): string {
  switch (field) {
    case "position":
    case "company":
    case "location":
      return `contains "${params[field]}"`;
    case "status":
      return STATUS_LABELS[params.status];
    case "arrangement":
    case "work_type":
      return params[field].join(", ");
    case "salary":
      return [
        params.salary !== "any" ? SALARY_LABELS[params.salary] : "",
        params.min_salary ? `at least $${Number(params.min_salary).toLocaleString("en-NZ")}/yr` : "",
      ]
        .filter(Boolean)
        .join(", ");
    case "source":
      return params.source ? sourceLabel(params.source) : "";
    case "visa":
      return VISA_LABELS[params.visa];
    case "listed":
      return `${params.listed_from || "…"} to ${params.listed_to || "…"}`;
  }
}
