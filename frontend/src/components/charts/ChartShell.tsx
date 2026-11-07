import { useState, type ReactNode } from "react";
import { Box, Paper, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";

interface ChartShellProps {
  title: string;
  subtitle: string;
  chart: ReactNode;
  /** The same numbers as plain text, so no value is readable only through the picture. */
  table: ReactNode;
}

/** Card frame shared by every chart: title, a Chart / Table switch, and the chosen view. */
export default function ChartShell({ title, subtitle, chart, table }: ChartShellProps) {
  const [view, setView] = useState<"chart" | "table">("chart");

  return (
    <Paper component="section" variant="outlined" aria-label={title} sx={{ p: 2, bgcolor: "background.paper", minWidth: 0 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 1, mb: 1.5 }}>
        <Box>
          <Typography component="h3" variant="subtitle1" fontWeight={700}>
            {title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {subtitle}
          </Typography>
        </Box>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={view}
          aria-label={`${title} view`}
          onChange={(_, next: "chart" | "table" | null) => next && setView(next)}
        >
          <ToggleButton value="chart" sx={{ textTransform: "none", px: 1.25, py: 0.25 }}>
            Chart
          </ToggleButton>
          <ToggleButton value="table" sx={{ textTransform: "none", px: 1.25, py: 0.25 }}>
            Table
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>
      {view === "chart" ? chart : table}
    </Paper>
  );
}
