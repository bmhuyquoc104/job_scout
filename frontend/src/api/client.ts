import type { components } from "./schema";

export type CategoryItem = components["schemas"]["CategoryItem"];
export type JobListItem = components["schemas"]["JobListItem"];
export type PaginatedJobs = components["schemas"]["PaginatedJobs"];
export type JobDetail = components["schemas"]["JobDetail"];
export type JobFacets = components["schemas"]["JobFacets"];
export type TrendSeries = components["schemas"]["TrendSeries"];
export type LocationBreakdown = components["schemas"]["LocationBreakdown"];
export type SourceBreakdown = components["schemas"]["SourceBreakdown"];
export type CategoryVisaStats = components["schemas"]["CategoryVisaStats"];
export type GreenListResponse = components["schemas"]["GreenListResponse"];
export type GreenListRole = components["schemas"]["GreenListRoleItem"];
export type GreenListChange = components["schemas"]["GreenListChange"];
export type GreenListChangesResponse = components["schemas"]["GreenListChangesResponse"];
export type RoutesResponse = components["schemas"]["RoutesResponse"];
export type CountryRoutes = components["schemas"]["CountryRoutes"];
export type JobComparison = components["schemas"]["JobComparison"];
export type CountryJobStats = components["schemas"]["CountryJobStats"];
export type CountryVisaStats = components["schemas"]["CountryVisaStats"];
export type CvSkills = components["schemas"]["CvSkills"];
export type JobMatch = components["schemas"]["JobMatch"];
export type JobStatus = "open" | "closed" | "all";
export type JobSource = JobListItem["source"];

export type SourceOption = components["schemas"]["SourceOption"];

/** Display names by source id, in display order. Filled once at startup by loadSources(). */
export const SOURCE_LABELS: Record<string, string> = {};
export const sourceLabel = (source: string): string => SOURCE_LABELS[source] ?? source;

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function get<T>(path: string): Promise<T> {
  return parse(await fetch(path));
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      body?.error?.code ?? "http_error",
      body?.error?.message ?? "The request could not be completed.",
    );
  }
  return response.json() as Promise<T>;
}

export function getCategories(): Promise<CategoryItem[]> {
  return get("/api/categories");
}

/** `query` is the already-encoded query string; see `toApiQuery` in jobParams.ts. */
export function getCategoryJobs(categoryId: string, query: string): Promise<PaginatedJobs> {
  return get(`/api/categories/${categoryId}/jobs?${query}`);
}

export function getTrends(categoryId: string, days: number): Promise<TrendSeries> {
  return get(`/api/categories/${categoryId}/stats/trends?days=${days}`);
}

/** Loads the backend's single list of job sources (id and name) into SOURCE_LABELS. */
export async function loadSources(): Promise<void> {
  for (const { source, label } of await get<SourceOption[]>("/api/sources")) SOURCE_LABELS[source] = label;
}

export function getSources(categoryId: string): Promise<SourceBreakdown> {
  return get(`/api/categories/${categoryId}/stats/sources`);
}

export function getCategoryVisaStats(categoryId: string): Promise<CategoryVisaStats> {
  return get(`/api/categories/${categoryId}/stats/visa-sponsorship`);
}

export function getLocations(categoryId: string): Promise<LocationBreakdown> {
  return get(`/api/categories/${categoryId}/stats/locations`);
}

/** A country's priority-occupation list (NZ: the Green List; AU: the skilled occupation lists). */
export function getGreenList(country: string): Promise<GreenListResponse> {
  return get(`/api/green-list?country=${country}`);
}

export function getJobComparison(title: string): Promise<JobComparison> {
  return get(`/api/compare/jobs?title=${encodeURIComponent(title)}`);
}

export function getRoleTitles(): Promise<string[]> {
  return get("/api/green-list/titles");
}

export function getImmigrationRoutes(title: string): Promise<RoutesResponse> {
  return get(`/api/green-list/routes?title=${encodeURIComponent(title)}`);
}

export function getGreenListChanges(days: number, country: string): Promise<GreenListChangesResponse> {
  return get(`/api/green-list/changes?days=${days}&country=${country}`);
}

export function getJobFacets(categoryId: string): Promise<JobFacets> {
  return get(`/api/categories/${categoryId}/jobs/facets`);
}

export function getJob(jobId: string): Promise<JobDetail> {
  return get(`/api/jobs/${jobId}`);
}

/** Uploads a PDF CV; the server reads it in memory and returns only the IT skills it names. */
export async function uploadCv(file: File): Promise<CvSkills> {
  const body = new FormData();
  body.append("file", file);
  return parse<CvSkills>(await fetch("/api/cv", { method: "POST", body }));
}

/** Every open job in a country ranked against the CV skills, best first. */
export async function getMatches(
  skills: string[],
  country: string,
  years: number | null,
  options: { limit?: number; visaOnly?: boolean } = {},
): Promise<JobMatch[]> {
  return parse(
    await fetch("/api/matches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skills, country, years, limit: options.limit, visa_only: options.visaOnly }),
    }),
  );
}

/** Open jobs and the ones offering visa sponsorship, per country. */
export function getVisaStats(): Promise<CountryVisaStats[]> {
  return get("/api/stats/visa-sponsorship");
}
