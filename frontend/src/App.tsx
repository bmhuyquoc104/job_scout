import { Box, ThemeProvider, CssBaseline } from "@mui/material";
import AppRoutes from "./routes";
import SideNav from "./components/SideNav";
import theme from "./theme";

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        data-testid="app-shell"
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: { xs: 1, md: 2 },
          width: "min(100%, 1600px)",
          height: "100vh",
          "@supports (height: 100dvh)": { height: "100dvh" },
          minHeight: 480,
          mx: "auto",
          p: { xs: 1.25, sm: 2 },
          overflow: "hidden",
        }}
      >
        <SideNav />
        <Box sx={{ display: "flex", flex: 1, minWidth: 0, minHeight: 0 }}>
          <AppRoutes />
        </Box>
      </Box>
    </ThemeProvider>
  );
}
