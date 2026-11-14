import { useState } from "react";
import { Box, Typography } from "@mui/material";
import JobComparisonCharts from "../components/JobComparisonCharts";
import PageHeader from "../components/PageHeader";
import TitlePicker from "../components/TitlePicker";

export default function Analytics() {
  const [title, setTitle] = useState("");
  const query = title.trim();
  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: { xs: 2, md: 3 }, overflow: "auto" }}>
      <PageHeader
        title="Compare a job across countries"
        subtitle="Pick a role or type a job title to compare open jobs, pay, visa sponsorship and sources in every country."
      />
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
