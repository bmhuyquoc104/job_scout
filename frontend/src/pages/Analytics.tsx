import { useState } from "react";
import { Box, Link, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import JobComparisonCharts from "../components/JobComparisonCharts";
import TitlePicker from "../components/TitlePicker";

export default function Analytics() {
  const [title, setTitle] = useState("");
  const query = title.trim();
  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: 3, overflow: "auto" }}>
      <Link component={RouterLink} to="/" underline="hover" sx={{ display: "inline-block", mb: 1.75 }}>
        ← Dashboard
      </Link>
      <Typography component="h1" variant="h4" sx={{ mb: 1, fontSize: 24, fontWeight: 700 }}>
        Analytics: compare a job across countries
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 760 }}>
        Pick a role or type a job title to compare how many open jobs there are, what they pay and where they were found in New Zealand,
        Australia, Canada and Germany.
      </Typography>
      <TitlePicker title={title} onChange={setTitle} />
      {query ? (
        <Box sx={{ mt: 2 }}>
          <JobComparisonCharts title={query} />
        </Box>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
          The charts appear here once you pick or enter a job title.
        </Typography>
      )}
    </Box>
  );
}
