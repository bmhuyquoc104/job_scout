import { createContext, useContext } from "react";
import type { JobFacets } from "../api/client";
import type { JobParams } from "../api/jobParams";

/** What the grid's column menus and headers need from the page: current filters and how to change them. */
export interface JobTableState {
  params: JobParams;
  facets: JobFacets | null;
  update: (changes: Partial<JobParams>) => void;
}

export const JobTableContext = createContext<JobTableState | null>(null);

export function useJobTable(): JobTableState {
  const state = useContext(JobTableContext);
  if (!state) throw new Error("useJobTable must be used inside the jobs table");
  return state;
}
