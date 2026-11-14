import { Box, Link, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import RoutesLookup from "../components/RoutesLookup";

export default function CompareRoutes() {
  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: 3, overflow: "auto" }}>
      <Link component={RouterLink} to="/" underline="hover" sx={{ display: "inline-block", mb: 1.75 }}>
        ← Dashboard
      </Link>
      <Typography component="h1" variant="h4" sx={{ mb: 1, fontSize: 24, fontWeight: 700 }}>
        Compare immigration routes for a job
      </Typography>
      <RoutesLookup />
    </Box>
  );
}
