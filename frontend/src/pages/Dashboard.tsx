import { Alert, Box, Button, Card, CardContent, CircularProgress, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { getCategories } from "../api/client";
import { useApi } from "../api/useApi";

export default function Dashboard() {
  const { data, error, loading } = useApi(getCategories, [], "Unable to load categories.");
  const categories = data ?? [];

  return (
    <Box component="main" sx={{ flex: 1, minHeight: 0, p: 3, overflow: "auto" }}>
      <Typography color="primary" variant="overline" fontWeight={700} letterSpacing={1}>
        Dashboard
      </Typography>
      <Typography component="h1" variant="h4" sx={{ mt: 0.5, mb: 2.25, fontSize: 24, fontWeight: 700 }}>
        Job categories
      </Typography>
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
