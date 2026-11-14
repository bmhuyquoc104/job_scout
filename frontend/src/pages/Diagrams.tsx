import { Box } from "@mui/material";
import { useParams } from "react-router-dom";
import CategorySwitcher from "../components/CategorySwitcher";
import PageHeader from "../components/PageHeader";
import TrendsPanel from "../components/TrendsPanel";

export default function Diagrams() {
  const { categoryId = "" } = useParams();

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: { xs: 2, md: 3 }, overflow: "auto" }}>
      <CategorySwitcher categoryId={categoryId} view="diagrams" />
      <PageHeader title="Diagrams" subtitle="How open jobs, sources, seniority, locations and visa sponsorship look right now." />
      <TrendsPanel categoryId={categoryId} />
    </Box>
  );
}
