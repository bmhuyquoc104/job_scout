import { useState } from "react";
import { Box } from "@mui/material";
import JobComparisonCharts from "../components/JobComparisonCharts";
import PageHeader from "../components/PageHeader";
import TitlePicker from "../components/TitlePicker";

export default function Analytics() {
  const [title, setTitle] = useState("");
  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: { xs: 2, md: 3 }, overflow: "auto" }}>
      <PageHeader
        title="Compare countries"
        subtitle="How open jobs differ between countries: size, visa sponsorship, seniority, work arrangement, pay and sources. Narrow it to one job title, or leave it empty for every job."
      />
      <TitlePicker title={title} onChange={setTitle} />
      <Box sx={{ mt: 2 }}>
        <JobComparisonCharts title={title.trim()} />
      </Box>
    </Box>
  );
}
