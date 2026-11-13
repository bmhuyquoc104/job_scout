import type { CategoryItem } from "../api/client";

const KEY = "country";

export interface CountryOption {
  code: string;
  name: string;
}

/** The distinct countries of the enabled categories, in the order the API lists them. */
export function countriesOf(categories: CategoryItem[]): CountryOption[] {
  const seen = new Map<string, CountryOption>();
  for (const { country, country_name } of categories)
    if (!seen.has(country)) seen.set(country, { code: country, name: country_name });
  return [...seen.values()];
}

/** The saved country if it is still offered, else the first one. */
export function chooseCountry(options: CountryOption[]): string {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved && options.some((option) => option.code === saved)) return saved;
  } catch {
    // Storage can be blocked; the first country is a fine default.
  }
  return options[0]?.code ?? "NZ";
}

export function saveCountry(code: string) {
  try {
    localStorage.setItem(KEY, code);
  } catch {
    // Not remembered; the choice still applies for this visit.
  }
}
