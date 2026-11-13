import { MenuItem, TextField, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useCountry } from "../country/CountryContext";

interface CategorySwitcherProps {
  categoryId: string;
  /** Which view the user is on, so switching category keeps them there. */
  view: "postings" | "diagrams";
}

/** Names the current category; with several enabled categories it becomes a picker. */
export default function CategorySwitcher({ categoryId, view }: CategorySwitcherProps) {
  const navigate = useNavigate();
  const { countryCategories: categories } = useCountry();
  const current = categories?.find((category) => category.id === categoryId);

  if (categories.length < 2) {
    return (
      <Typography color="primary" variant="overline" fontWeight={700} letterSpacing={1}>
        {current?.name ?? "Job category"}
      </Typography>
    );
  }
  return (
    <TextField
      select
      size="small"
      label="Category"
      value={current ? categoryId : ""}
      onChange={(event) => navigate(`/categories/${event.target.value}${view === "diagrams" ? "/diagrams" : ""}`)}
      sx={{ width: 400, maxWidth: "100%", alignSelf: "flex-start", mb: 1 }}
    >
      {categories.map((category) => (
        <MenuItem key={category.id} value={category.id}>
          {category.name}
        </MenuItem>
      ))}
    </TextField>
  );
}
