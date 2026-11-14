import { createTheme } from "@mui/material/styles";

// Catppuccin Mocha. Components use theme values; hex codes live only here.
const mocha = {
  base: "#1e1e2e",
  mantle: "#181825",
  surface0: "#313244",
  surface1: "#45475a",
  text: "#cdd6f4",
  subtext0: "#a6adc8",
  mauve: "#cba6f7",
  teal: "#94e2d5",
  red: "#f38ba8",
  green: "#a6e3a1",
  overlay0: "#6c7086",
};

/**
 * Chart colours, checked with the dataviz palette validator against the dark surface (#181825):
 * the two-series pair passes the colour-blind and contrast checks, and the seniority ramp is one
 * hue, light -> dark with visible steps. Catppuccin's own pastels fail those checks, so charts do
 * not use them.
 */
export const chartColors = {
  primary: "#3987e5",
  secondary: "#d95926",
  // Job sources take these in the backend's order (and cycle if there are more sources).
  sourcePalette: ["#3987e5", "#d95926", "#3aa76d", "#9b6ee0", "#d9a21f", "#2fa5b8"],
  // Ordered by seniority, graduate -> management; "unspecified" is a neutral gray, not a level.
  seniority: {
    graduate: "#cde2fb",
    junior: "#9ec5f4",
    mid: "#6da7ec",
    senior: "#3987e5",
    lead: "#256abf",
    management: "#184f95",
    unspecified: mocha.overlay0,
  } as Record<string, string>,
};

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: mocha.mauve },
    secondary: { main: mocha.teal, contrastText: mocha.base },
    error: { main: mocha.red },
    success: { main: mocha.green },
    background: { default: mocha.base, paper: mocha.mantle },
    text: { primary: mocha.text, secondary: mocha.subtext0 },
    divider: mocha.surface1,
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    // One scale for every page: h4 is a page title, h6 a section title, subtitle1 a card title.
    h4: { fontSize: 26, fontWeight: 700, lineHeight: 1.25, letterSpacing: "-0.01em" },
    h5: { fontSize: 20, fontWeight: 700, lineHeight: 1.3 },
    h6: { fontSize: 17, fontWeight: 700, lineHeight: 1.35 },
    subtitle1: { fontSize: 16, fontWeight: 650, lineHeight: 1.4 },
    overline: { fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", lineHeight: 1.5 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: { height: "100%" },
        body: { minWidth: 320, height: "100%" },
        "#root": { height: "100%" },
        a: { color: "inherit", textDecoration: "none" },
      },
    },
    MuiButton: { styleOverrides: { root: { textTransform: "none", fontWeight: 650 } } },
    MuiCard: { styleOverrides: { root: { backgroundColor: mocha.surface0 } } },
    MuiPaper: { styleOverrides: { outlined: { borderColor: mocha.surface1 } } },
  },
});

export default theme;
