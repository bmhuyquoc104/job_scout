import { Box, Typography } from "@mui/material";
import { useParams } from "react-router-dom";
import CategorySwitcher from "../components/CategorySwitcher";
import TrendsPanel from "../components/TrendsPanel";

export default function Diagrams() {
  const { categoryId = "" } = useParams();

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: 3, overflow: "auto" }}>
      <CategorySwitcher categoryId={categoryId} view="diagrams" />
      <Typography component="h1" variant="h4" sx={{ mt: 0.5, mb: 2, fontSize: 24, fontWeight: 700 }}>
        Diagrams
      </Typography>
      <TrendsPanel categoryId={categoryId} />
    </Box>
  );
}
