import { createContext, useContext } from "react";
import type { CategoryItem } from "../api/client";
import type { CountryOption } from "../utils/country";

export interface CountryState {
  /** Every enabled category, all countries. */
  categories: CategoryItem[];
  countries: CountryOption[];
  /** The country the whole app is showing. */
  country: string;
  countryName: string;
  /** Only the categories of the chosen country. */
  countryCategories: CategoryItem[];
  /** True until the category list has loaded. */
  loading: boolean;
  error: string;
  setCountry: (code: string) => void;
}

export const CountryContext = createContext<CountryState | null>(null);

export function useCountry(): CountryState {
  const state = useContext(CountryContext);
  if (!state) throw new Error("useCountry must be used inside CountryProvider");
  return state;
}
