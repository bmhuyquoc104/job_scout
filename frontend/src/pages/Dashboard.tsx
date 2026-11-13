import { Alert, Box, Button, Card, CardContent, CircularProgress, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { useCountry } from "../country/CountryContext";

export default function Dashboard() {
  const { countryCategories: categories, countries, country, setCountry, error, loading } = useCountry();

  return (
    <Box component="main" sx={{ flex: 1, minHeight: 0, p: 3, overflow: "auto" }}>
      <Typography color="primary" variant="overline" fontWeight={700} letterSpacing={1}>
        Dashboard
      </Typography>
      <Typography component="h1" variant="h4" sx={{ mt: 0.5, mb: 2.25, fontSize: 24, fontWeight: 700 }}>
        Job categories
      </Typography>
      {countries.length > 1 && (
        <ToggleButtonGroup
          exclusive
          size="small"
          color="primary"
          value={country}
          aria-label="Country"
          onChange={(_, next: string | null) => next && setCountry(next)}
          sx={{ mb: 2.25 }}
        >
          {countries.map((option) => (
            <ToggleButton key={option.code} value={option.code} sx={{ textTransform: "none", px: 2 }}>
              {option.name}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      )}
      {loading && <CircularProgress aria-label="Loading categories" size={24} />}
      {error && <Alert severity="error">{error}</Alert>}
      {!loading && !error && categories.length === 0 && (
        <Typography color="text.secondary">No categories available.</Typography>
      )}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 500px))", gap: 1.5 }}>
        {categories.map((category) => (
          <Card key={category.id} variant="outlined">
            <CardContent>
              <Stack direction={{ xs: "column", sm: "row" }} alignItems={{ xs: "stretch", sm: "center" }} justifyContent="space-between" gap={2}>
                <Box>
                  <Typography variant="subtitle1" fontWeight={700}>{category.name}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {category.active_job_count.toLocaleString()} open jobs
                  </Typography>
                </Box>
                <Button
                  component={RouterLink}
                  to={`/categories/${category.id}`}
                  variant="contained"
                  color="secondary"
                  sx={{ flex: "none" }}
                >
                  View jobs
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
}
