import { Box, Chip, Link, Paper, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import type { JobMatch } from "../api/client";

export const STRONG = 65;
const scoreColor = (score: number) => (score >= STRONG ? "success" : score >= 35 ? "warning" : "text");

function Score({ value }: { value: number }) {
  const color = scoreColor(value);
  return (
    <Box
      aria-label={`${value}% match`}
      sx={{
        flex: "none",
        width: 56,
        textAlign: "center",
        py: 0.75,
        borderRadius: 1.5,
        border: 1,
        borderColor: `${color}.main`,
        color: `${color}.main`,
      }}
    >
      <Typography component="span" variant="h6" color="inherit">
        {value}
      </Typography>
      <Typography component="span" variant="caption" color="inherit">
        %
      </Typography>
    </Box>
  );
}

/** One ranked job: the score, the job, and the reasons behind the score (what matched, what to add). */
export default function JobRow({ match, cvYears }: { match: JobMatch; cvYears?: number | null }) {
  const short = match.required_years !== null && cvYears != null && match.required_years > cvYears;
  return (
    <Paper component="li" variant="outlined" sx={{ p: 2, display: "flex", gap: 2, alignItems: "flex-start" }}>
      <Score value={match.score} />
      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Link component={RouterLink} to={`/jobs/${match.id}`} underline="hover" fontWeight={650} color="text.primary">
          {match.position}
        </Link>
        <Typography variant="body2" color="text.secondary">
          {[match.company_name, match.location, match.salary_label].filter(Boolean).join(" · ")}
        </Typography>
        {(match.visa_sponsor || match.required_years !== null) && (
          <Stack direction="row" gap={0.75} flexWrap="wrap" sx={{ mt: 1 }}>
            {match.visa_sponsor && <Chip size="small" color="success" variant="outlined" label="Visa sponsorship" />}
            {match.required_years !== null && (
              <Chip
                size="small"
                variant="outlined"
                color={short ? "warning" : "default"}
                label={
                  short
                    ? `Asks ${match.required_years}+ yrs · your CV: ${cvYears}`
                    : match.required_years === 0
                      ? "No experience needed"
                      : `Asks ${match.required_years}+ yrs`
                }
              />
            )}
          </Stack>
        )}
        {match.matched_skills.length > 0 && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            <Box component="span" sx={{ color: "success.main", fontWeight: 600 }}>You have:</Box> {match.matched_skills.join(", ")}
          </Typography>
        )}
        {match.missing_skills.length > 0 && (
          <Stack direction="row" gap={0.5} flexWrap="wrap" alignItems="center" sx={{ mt: 0.75 }}>
            <Typography variant="caption" color="text.secondary">
              Add to your CV:
            </Typography>
            {match.missing_skills.map((skill) => (
              <Chip key={skill} size="small" variant="outlined" label={skill} />
            ))}
          </Stack>
        )}
      </Box>
    </Paper>
  );
}
