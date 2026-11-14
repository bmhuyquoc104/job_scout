import type { ReactNode } from "react";
import { Box, Card, CardActionArea, CardContent, Stack, SvgIcon, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

const ARROW = "M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z";

interface EntryCardProps {
  to: string;
  title: string;
  text?: string;
  /** Extra content under the text, such as a number or a chip. */
  children?: ReactNode;
  highlighted?: boolean;
  onClick?: () => void;
}

/** A whole-card link that opens a page. The arrow is the cue that the card is clickable. */
export default function EntryCard({ to, title, text, children, highlighted, onClick }: EntryCardProps) {
  return (
    <Card variant="outlined" sx={{ height: "100%", borderColor: highlighted ? "primary.main" : undefined }}>
      <CardActionArea component={RouterLink} to={to} onClick={onClick} sx={{ height: "100%" }}>
        <CardContent sx={{ height: "100%" }}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
            <Typography variant="subtitle1">{title}</Typography>
            <SvgIcon fontSize="small" color="primary" sx={{ flex: "none", mt: 0.25 }}>
              <path d={ARROW} />
            </SvgIcon>
          </Stack>
          {text && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {text}
            </Typography>
          )}
          {children && <Box sx={{ mt: 1.5 }}>{children}</Box>}
        </CardContent>
      </CardActionArea>
    </Card>
  );
}
