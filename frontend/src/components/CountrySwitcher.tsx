import { MenuItem, TextField } from "@mui/material";
import { useLocation, useMatch, useNavigate } from "react-router-dom";
import { useCountry } from "../country/CountryContext";

/** The app's country, visible on every page. On a category page it also moves to that country's category. */
export default function CountrySwitcher() {
  const { categories, countries, country, setCountry } = useCountry();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const onCategory = useMatch("/categories/:categoryId/*");

  if (countries.length < 2) return null;
  return (
    <TextField
      select
      size="small"
      label="Country"
      value={country}
      fullWidth
      onChange={(event) => {
        const code = event.target.value;
        setCountry(code);
        const first = categories.find((category) => category.country === code);
        if (onCategory && first) navigate(`/categories/${first.id}${pathname.endsWith("/diagrams") ? "/diagrams" : ""}`);
      }}
    >
      {countries.map((option) => (
        <MenuItem key={option.code} value={option.code}>
          {option.name}
        </MenuItem>
      ))}
    </TextField>
  );
}
