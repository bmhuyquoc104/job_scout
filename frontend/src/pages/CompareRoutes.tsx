import { Box } from "@mui/material";
import PageHeader from "../components/PageHeader";
import RoutesLookup from "../components/RoutesLookup";

export default function CompareRoutes() {
  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: { xs: 2, md: 3 }, overflow: "auto" }}>
      <PageHeader
        title="Compare immigration routes"
        subtitle="Pick a job to see each country's priority list and the routes it opens."
      />
      <RoutesLookup />
    </Box>
  );
}
