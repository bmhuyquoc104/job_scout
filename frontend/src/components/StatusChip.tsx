import { Chip } from "@mui/material";

/** Open = still listed on SEEK; Closed = the scraper no longer sees the listing. */
export default function StatusChip({ isActive }: { isActive: boolean }) {
  return (
    <Chip
      size="small"
      variant="outlined"
      label={isActive ? "Open" : "Closed"}
      color={isActive ? "success" : "default"}
    />
  );
}
