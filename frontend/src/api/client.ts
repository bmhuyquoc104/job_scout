import type { components } from "./schema";

export type CategoryItem = components["schemas"]["CategoryItem"];
export type JobListItem = components["schemas"]["JobListItem"];
export type PaginatedJobs = components["schemas"]["PaginatedJobs"];
export type JobDetail = components["schemas"]["JobDetail"];
export type JobFacets = components["schemas"]["JobFacets"];
export type TrendSeries = components["schemas"]["TrendSeries"];
export type LocationBreakdown = components["schemas"]["LocationBreakdown"];
export type SourceBreakdown = components["schemas"]["SourceBreakdown"];
export type GreenListResponse = components["schemas"]["GreenListResponse"];
export type GreenListRole = components["schemas"]["GreenListRoleItem"];
export type GreenListChange = components["schemas"]["GreenListChange"];
export type GreenListChangesResponse = components["schemas"]["GreenListChangesResponse"];
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

export function getLocations(categoryId: string): Promise<LocationBreakdown> {
  return get(`/api/categories/${categoryId}/stats/locations`);
}

export function getGreenList(): Promise<GreenListResponse> {
  return get("/api/green-list");
}

export function getGreenListChanges(days: number): Promise<GreenListChangesResponse> {
  return get(`/api/green-list/changes?days=${days}`);
}

export function getJobFacets(categoryId: string): Promise<JobFacets> {
  return get(`/api/categories/${categoryId}/jobs/facets`);
}

export function getJob(jobId: string): Promise<JobDetail> {
  return get(`/api/jobs/${jobId}`);
}

/** Uploads a PDF CV; the server reads it in memory and returns only the IT skills it names. */
export async function uploadCv(file: File): Promise<string[]> {
  const body = new FormData();
  body.append("file", file);
  return (await parse<CvSkills>(await fetch("/api/cv", { method: "POST", body }))).skills;
}

/** Every open job ranked against the CV skills, best first. */
export async function getMatches(skills: string[]): Promise<JobMatch[]> {
  return parse(
    await fetch("/api/matches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skills }),
    }),
  );
}
