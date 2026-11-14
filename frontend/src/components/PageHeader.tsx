import type { ReactNode } from "react";
import { Box, Link, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  /** Small label above the title, such as the category name. */
  eyebrow?: string;
  /** Where "back" goes; omit on top-level pages. */
  back?: { to: string; label: string };
  /** Controls that belong to the page as a whole, shown on the right. */
  actions?: ReactNode;
}

/** The same title block on every page, so people always know where they are and how to go back. */
export default function PageHeader({ title, subtitle, eyebrow, back, actions }: PageHeaderProps) {
  return (
    <Box component="header" sx={{ mb: 3 }}>
      {back && (
        <Link component={RouterLink} to={back.to} underline="hover" variant="body2" color="text.secondary" sx={{ display: "inline-block", mb: 1 }}>
          ← {back.label}
        </Link>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "flex-end" }} gap={2}>
        <Box sx={{ minWidth: 0 }}>
          {eyebrow && (
            <Typography variant="overline" color="primary" component="p" sx={{ m: 0 }}>
              {eyebrow}
            </Typography>
          )}
          <Typography variant="h4" component="h1">
            {title}
          </Typography>
          {subtitle && (
            <Typography color="text.secondary" sx={{ mt: 0.75, maxWidth: 720 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
        {actions && <Box sx={{ flex: "none" }}>{actions}</Box>}
      </Stack>
    </Box>
  );
}
