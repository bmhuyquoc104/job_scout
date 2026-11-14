import { useState } from "react";
import {
  Box,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  ListSubheader,
  Paper,
  Stack,
  SvgIcon,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { Link as RouterLink, useLocation, useMatch } from "react-router-dom";
import { useCountry } from "../country/CountryContext";
import CountrySwitcher from "./CountrySwitcher";

const WIDTH = 248;
// Material icon paths, inlined to avoid a whole icon package.
const ICONS = {
  home: "M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z",
  work: "M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z",
  chart: "M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z",
  trend: "M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z",
  cv: "M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
  star: "M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z",
  check: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
  swap: "M9.01 14H2v2h7.01v3L13 15l-3.99-4v3zm5.98-1v-3H22V8h-7.01V5L11 9l3.99 4z",
  menu: "M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z",
};

function NavIcon({ path }: { path: string }) {
  return (
    <SvgIcon fontSize="small">
      <path d={path} />
    </SvgIcon>
  );
}

interface NavItem {
  label: string;
  icon: string;
  to: string;
  selected: boolean;
  /** Needs a job category, so it is disabled until the categories load. */
  needsCategory?: boolean;
}

/** Labelled navigation that is always visible on wide screens and opens from a top bar on narrow ones. */
export default function SideNav() {
  const theme = useTheme();
  const wide = useMediaQuery(theme.breakpoints.up("md"));
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const { countryCategories } = useCountry();

  // Inside a category use that one; elsewhere fall back to the first of the chosen country.
  const categoryId = useMatch("/categories/:categoryId/*")?.params.categoryId ?? countryCategories[0]?.id;
  const groups: { title: string; items: NavItem[] }[] = [
    {
      title: "Explore",
      items: [
        { label: "Dashboard", icon: ICONS.home, to: "/", selected: pathname === "/" },
        {
          label: "Job postings",
          icon: ICONS.work,
          to: `/categories/${categoryId}`,
          selected: pathname === `/categories/${categoryId}` || pathname.startsWith("/jobs/"),
          needsCategory: true,
        },
        { label: "Diagrams", icon: ICONS.chart, to: `/categories/${categoryId}/diagrams`, selected: pathname.endsWith("/diagrams"), needsCategory: true },
        { label: "Compare a job", icon: ICONS.trend, to: "/analytics", selected: pathname === "/analytics" },
      ],
    },
    {
      title: "For you",
      items: [
        { label: "My CV", icon: ICONS.cv, to: "/cv", selected: pathname === "/cv" },
        {
          label: "Recommended",
          icon: ICONS.star,
          to: "/recommended-jobs",
          selected: ["/recommended-jobs", "/top-jobs", "/top-visa-jobs"].includes(pathname),
        },
      ],
    },
    {
      title: "Immigration",
      items: [
        { label: "Priority lists", icon: ICONS.check, to: "/immigration", selected: pathname.startsWith("/immigration") },
        { label: "Compare routes", icon: ICONS.swap, to: "/compare-routes", selected: pathname === "/compare-routes" },
      ],
    },
  ];

  const content = (
    <Box component="nav" aria-label="Main" sx={{ p: 1.5, width: "100%" }}>
      <Box
        component={RouterLink}
        to="/"
        onClick={() => setOpen(false)}
        sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 0.5, py: 0.5, mb: 2 }}
      >
        <Box
          aria-hidden
          sx={{
            flex: "none",
            width: 34,
            height: 34,
            borderRadius: 1.5,
            bgcolor: "primary.main",
            color: "background.default",
            display: "grid",
            placeItems: "center",
            fontWeight: 800,
            fontSize: 14,
          }}
        >
          JS
        </Box>
        <Box>
          <Typography variant="subtitle1" fontWeight={750} lineHeight={1.2}>
            Job Scout
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Jobs &amp; immigration
          </Typography>
        </Box>
      </Box>
      <Box sx={{ mb: 1 }}>
        <CountrySwitcher />
      </Box>
      {groups.map((group) => (
        <List
          key={group.title}
          disablePadding
          subheader={
            <ListSubheader disableSticky sx={{ bgcolor: "transparent", lineHeight: 2.5, px: 1.5, fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase" }}>
              {group.title}
            </ListSubheader>
          }
        >
          {group.items.map((item) => (
            <ListItemButton
              key={item.label}
              component={RouterLink}
              to={item.to}
              selected={item.selected}
              aria-current={item.selected ? "page" : undefined}
              disabled={item.needsCategory && !categoryId}
              onClick={() => setOpen(false)}
              sx={{ borderRadius: 1.5, mb: 0.25, px: 1.5, py: 0.75 }}
            >
              <ListItemIcon sx={{ minWidth: 36, color: item.selected ? "primary.main" : "text.secondary" }}>
                <NavIcon path={item.icon} />
              </ListItemIcon>
              <ListItemText primary={item.label} slotProps={{ primary: { fontWeight: item.selected ? 700 : 500, fontSize: 14.5 } }} />
            </ListItemButton>
          ))}
        </List>
      ))}
    </Box>
  );

  if (wide) {
    return (
      <Paper variant="outlined" sx={{ flex: "none", width: WIDTH, overflowY: "auto", bgcolor: "background.paper" }}>
        {content}
      </Paper>
    );
  }
  return (
    <>
      <Stack direction="row" alignItems="center" gap={1}>
        <IconButton aria-label="Open menu" onClick={() => setOpen(true)} edge="start" color="primary">
          <NavIcon path={ICONS.menu} />
        </IconButton>
        <Typography variant="subtitle1" fontWeight={750}>
          Job Scout
        </Typography>
      </Stack>
      <Drawer open={open} onClose={() => setOpen(false)} slotProps={{ paper: { sx: { width: WIDTH } } }}>
        {content}
      </Drawer>
    </>
  );
}
