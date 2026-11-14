import { useState } from "react";
import {
  Box,
  Button,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  SvgIcon,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { Link as RouterLink, useLocation, useMatch } from "react-router-dom";
import { useCountry } from "../country/CountryContext";

const COLLAPSED = 64;
const EXPANDED = 220;
// Material "work" (briefcase) and "bar chart" icon paths, inlined to avoid a whole icon package.
const WORK = "M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z";
const BAR_CHART = "M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z";
const DESCRIPTION = "M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z";
const STAR = "M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z";
const CHECK_CIRCLE = "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z";

function NavIcon({ path }: { path: string }) {
  return (
    <SvgIcon fontSize="small">
      <path d={path} />
    </SvgIcon>
  );
}

/**
 * Main navigation. On wide screens it is a slim icon rail that grows over the page (no layout shift)
 * while hovered or focused, to show the names. On narrow screens it opens from a Menu button.
 */
export default function SideNav() {
  const theme = useTheme();
  const wide = useMediaQuery(theme.breakpoints.up("md"));
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const { countryCategories } = useCountry();

  // Inside a category use that one; elsewhere (dashboard, job detail) fall back to the first.
  const categoryId = useMatch("/categories/:categoryId/*")?.params.categoryId ?? countryCategories[0]?.id;
  const items = [
    {
      label: "Job postings",
      icon: WORK,
      to: `/categories/${categoryId}`,
      selected: pathname === `/categories/${categoryId}` || pathname.startsWith("/jobs/"),
    },
    { label: "Diagrams", icon: BAR_CHART, to: `/categories/${categoryId}/diagrams`, selected: pathname.endsWith("/diagrams") },
    { label: "My CV", icon: DESCRIPTION, to: "/cv", selected: pathname === "/cv", standalone: true },
    { label: "Recommended", icon: STAR, to: "/recommended-jobs", selected: pathname === "/recommended-jobs", standalone: true },
    // Each country's priority-occupation list is not tied to a job category.
    { label: "Immigration", icon: CHECK_CIRCLE, to: "/immigration", selected: pathname.startsWith("/immigration"), standalone: true },
  ];

  // The names stay in the DOM (just invisible while collapsed) so links keep their accessible names.
  const content = (
    <Box component="nav" aria-label="Main" sx={{ p: 1, width: "100%" }}>
      <Box
        component={RouterLink}
        to="/"
        title="Job Scout"
        onClick={() => setOpen(false)}
        sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 1, py: 1, mb: 1, whiteSpace: "nowrap" }}
      >
        <Box
          aria-hidden
          sx={{
            flex: "none",
            width: 32,
            height: 32,
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
        <Box className="nav-label">
          <Typography variant="subtitle1" fontWeight={750} lineHeight={1.2}>
            Job Scout
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Jobs &amp; immigration
          </Typography>
        </Box>
      </Box>
      <List disablePadding>
        {items.map((item) => (
          <ListItemButton
            key={item.label}
            component={RouterLink}
            to={item.to}
            title={item.label}
            selected={item.selected}
            disabled={!categoryId && !item.standalone}
            onClick={() => setOpen(false)}
            sx={{ borderRadius: 1.5, mb: 0.5, px: 1.5, whiteSpace: "nowrap" }}
          >
            <ListItemIcon sx={{ minWidth: 36, color: item.selected ? "primary.main" : "text.secondary" }}>
              <NavIcon path={item.icon} />
            </ListItemIcon>
            <ListItemText
              className="nav-label"
              primary={item.label}
              slotProps={{ primary: { fontWeight: item.selected ? 700 : 500 } }}
            />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  if (wide) {
    return (
      // The wrapper reserves the collapsed width; the panel inside grows over the content.
      <Box sx={{ position: "relative", flex: "none", width: COLLAPSED }}>
        <Paper
          variant="outlined"
          sx={{
            position: "absolute",
            inset: "0 auto 0 0",
            width: COLLAPSED,
            overflow: "hidden",
            bgcolor: "background.paper",
            zIndex: theme.zIndex.drawer,
            transition: theme.transitions.create(["width", "box-shadow"], { duration: 150 }),
            "& .nav-label": { opacity: 0, transition: theme.transitions.create("opacity", { duration: 150 }) },
            "&:hover, &:focus-within": { width: EXPANDED, boxShadow: 6 },
            "&:hover .nav-label, &:focus-within .nav-label": { opacity: 1 },
            "@media (prefers-reduced-motion: reduce)": { transition: "none", "& .nav-label": { transition: "none" } },
          }}
        >
          {content}
        </Paper>
      </Box>
    );
  }
  return (
    <>
      <Button onClick={() => setOpen(true)} sx={{ alignSelf: "flex-start" }}>
        Menu
      </Button>
      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        slotProps={{ paper: { sx: { width: EXPANDED } } }}
      >
        {content}
      </Drawer>
    </>
  );
}
