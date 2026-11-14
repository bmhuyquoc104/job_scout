import { useState } from "react";
import { Box, Typography } from "@mui/material";
import ImmigrationRoutes from "./ImmigrationRoutes";
import TitlePicker from "./TitlePicker";

/** Pick or type a job title and see how each country's immigration routes treat it. */
export default function RoutesLookup() {
  const [title, setTitle] = useState("");
  const query = title.trim();
  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 760 }}>
        Pick a role from the list, or type any job title, to compare New Zealand, Australia, Canada and Germany: whether the role is on each
        country&apos;s priority list, the routes that apply to any job, and Germany&apos;s salary thresholds.
      </Typography>
      <TitlePicker title={title} onChange={setTitle} />
      {query ? (
        <ImmigrationRoutes title={query} />
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
          The comparison appears here once you pick or enter a job title.
        </Typography>
      )}
    </Box>
  );
}
