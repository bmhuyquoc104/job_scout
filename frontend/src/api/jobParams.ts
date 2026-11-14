import { SOURCE_LABELS, type JobSource, type JobStatus } from "./client";

export type SortKey =
  | "position"
  | "company"
  | "location"
  | "arrangement"
  | "work_type"
  | "status"
  | "salary"
  | "listed"
  | "source"
  | "visa";
export type SortOrder = "asc" | "desc";
export type SalaryFilter = "any" | "listed" | "unlisted";
export type VisaFilter = "any" | "offered" | "not_mentioned";

/** Everything that shapes the jobs table. It lives in the URL, so views can be shared and bookmarked. */
export interface JobParams {
  status: JobStatus;
  /** "" = every source. */
  source: JobSource | "";
  sort: SortKey;
  order: SortOrder;
  position: string;
  company: string;
  location: string;
  arrangement: string[];
  work_type: string[];
  salary: SalaryFilter;
  min_salary: string;
  visa: VisaFilter;
  listed_from: string;
  listed_to: string;
  offset: number;
}

export const PAGE_SIZE = 50;

export const DEFAULT_PARAMS: JobParams = {
  status: "all",
  source: "",
  sort: "listed",
  order: "desc",
  position: "",
  company: "",
  location: "",
  arrangement: [],
  work_type: [],
  salary: "any",
  min_salary: "",
  visa: "any",
  listed_from: "",
  listed_to: "",
  offset: 0,
};

const STATUSES: readonly JobStatus[] = ["open", "closed", "all"];
const SORT_KEYS: readonly SortKey[] = [
  "position",
  "company",
  "location",
  "arrangement",
  "work_type",
  "status",
  "salary",
  "listed",
  "source",
  "visa",
];
const ORDERS: readonly SortOrder[] = ["asc", "desc"];
const SALARIES: readonly SalaryFilter[] = ["any", "listed", "unlisted"];
const VISAS: readonly VisaFilter[] = ["any", "offered", "not_mentioned"];

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

export function parseParams(search: URLSearchParams): JobParams {
  return {
    status: pick(search.get("status"), STATUSES, DEFAULT_PARAMS.status),
    source: pick(search.get("source"), ["", ...Object.keys(SOURCE_LABELS)] as (JobSource | "")[], DEFAULT_PARAMS.source),
    sort: pick(search.get("sort"), SORT_KEYS, DEFAULT_PARAMS.sort),
    order: pick(search.get("order"), ORDERS, DEFAULT_PARAMS.order),
    position: search.get("position") ?? "",
    company: search.get("company") ?? "",
    location: search.get("location") ?? "",
    arrangement: search.getAll("arrangement"),
    work_type: search.getAll("work_type"),
    salary: pick(search.get("salary"), SALARIES, DEFAULT_PARAMS.salary),
    min_salary: search.get("min_salary") ?? "",
    visa: pick(search.get("visa"), VISAS, DEFAULT_PARAMS.visa),
    listed_from: search.get("listed_from") ?? "",
    listed_to: search.get("listed_to") ?? "",
    offset: Math.max(0, Number(search.get("offset")) || 0),
  };
}

/** Only values that differ from the defaults are written, which keeps URLs short. */
export function toSearchParams(params: JobParams): URLSearchParams {
  const search = new URLSearchParams();
  for (const key of Object.keys(DEFAULT_PARAMS) as (keyof JobParams)[]) {
    const value = params[key];
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else if (value !== DEFAULT_PARAMS[key]) search.set(key, String(value));
  }
  return search;
}

export function toApiQuery(params: JobParams): string {
  const search = toSearchParams(params);
  search.set("limit", String(PAGE_SIZE));
  return search.toString();
}

/** True when anything other than sorting and paging narrows the table. */
export function hasActiveFilters(params: JobParams): boolean {
  return (
    params.status !== DEFAULT_PARAMS.status ||
    params.source !== "" ||
    params.position !== "" ||
    params.company !== "" ||
    params.location !== "" ||
    params.arrangement.length > 0 ||
    params.work_type.length > 0 ||
    params.salary !== DEFAULT_PARAMS.salary ||
    params.min_salary !== "" ||
    params.visa !== DEFAULT_PARAMS.visa ||
    params.listed_from !== "" ||
    params.listed_to !== ""
  );
}
