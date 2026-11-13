import { useState, type ReactNode } from "react";
import { useMatch } from "react-router-dom";
import { getCategories } from "../api/client";
import { useApi } from "../api/useApi";
import { chooseCountry, countriesOf, saveCountry } from "../utils/country";
import { CountryContext } from "./CountryContext";

/**
 * The one place the app's country is decided. Every page reads it from here, so none of them
 * needs its own country filter. Opening a category link switches to that category's country.
 */
export default function CountryProvider({ children }: { children: ReactNode }) {
  const { data, error, loading } = useApi(getCategories, [], "Unable to load categories.");
  const categories = data ?? [];
  const countries = countriesOf(categories);
  const [picked, setPicked] = useState<string | null>(null);
  const routeCategoryId = useMatch("/categories/:categoryId/*")?.params.categoryId;
  const routeCountry = categories.find((category) => category.id === routeCategoryId)?.country;
  const chosen = picked && countries.some((option) => option.code === picked) ? picked : null;
  const country = routeCountry ?? chosen ?? chooseCountry(countries);

  return (
    <CountryContext.Provider
      value={{
        categories,
        countries,
        country,
        countryName: countries.find((option) => option.code === country)?.name ?? country,
        countryCategories: categories.filter((category) => category.country === country),
        loading,
        error,
        setCountry: (code) => {
          saveCountry(code);
          setPicked(code);
        },
      }}
    >
      {children}
    </CountryContext.Provider>
  );
}
