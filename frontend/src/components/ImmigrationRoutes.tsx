import { Alert, Box, Chip, CircularProgress, Paper, Stack, Typography } from "@mui/material";
import { getImmigrationRoutes, type CountryRoutes } from "../api/client";
import { useApi } from "../api/useApi";

function CountryCard({ routes }: { routes: CountryRoutes }) {
  return (
    <Paper variant="outlined" sx={{ p: 2, bgcolor: "background.paper" }}>
      <Typography component="h3" variant="subtitle1" fontWeight={700}>
        {routes.country_name}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {routes.list_name}
      </Typography>
      {routes.roles.length > 0 ? (
        <Stack gap={1} sx={{ my: 1.25 }}>
          {routes.roles.map((role) => (
            <Box key={`${role.code}-${role.title}`}>
              <Stack direction="row" gap={0.75} flexWrap="wrap" alignItems="center">
                <Typography variant="body2" fontWeight={600}>{role.title}</Typography>
                {role.tier != null && <Chip size="small" color="success" label={`Tier ${role.tier}`} />}
                {role.lists.map((list) => (
                  <Chip key={list} size="small" variant="outlined" label={list} />
                ))}
              </Stack>
              {role.pathway && (
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", whiteSpace: "pre-line" }}>
                  {role.pathway.length > 220 ? `${role.pathway.slice(0, 220)}…` : role.pathway}
                </Typography>
              )}
            </Box>
          ))}
        </Stack>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ my: 1.25 }}>
          Not on this country&apos;s priority list.
        </Typography>
      )}
      <Typography variant="overline" color="text.secondary">Routes for any job</Typography>
      <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
        {routes.general_routes.map((route) => (
          <Typography key={route} component="li" variant="body2">{route}</Typography>
        ))}
      </Box>
    </Paper>
  );
}

/** Every country's immigration routes for one job title, side by side. */
export default function ImmigrationRoutes({ title }: { title: string }) {
  const { data, error, loading } = useApi(
    () => getImmigrationRoutes(title),
    [title],
    "Unable to load immigration routes.",
  );
  return (
    <Box component="section" aria-label="Immigration routes" sx={{ my: 2.5 }}>
      <Typography component="h2" variant="h6" fontWeight={700} sx={{ mb: 1.5 }}>
        Immigration routes for &ldquo;{title}&rdquo;
      </Typography>
      {loading && !data && <CircularProgress aria-label="Loading routes" size={24} />}
      {error && <Alert severity="error">{error}</Alert>}
      {data && (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)", xl: "repeat(4, 1fr)" }, gap: 1.5 }}>
          {data.countries.map((routes) => (
            <CountryCard key={routes.country} routes={routes} />
          ))}
        </Box>
      )}
    </Box>
  );
}
