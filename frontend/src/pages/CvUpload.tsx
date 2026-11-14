import { useState, type DragEvent } from "react";
import { Alert, Box, Button, Chip, LinearProgress, Paper, Stack, SvgIcon, TextField, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { ApiError, uploadCv } from "../api/client";
import PageHeader from "../components/PageHeader";
import { loadCvSkills, loadCvYears, saveCvSkills } from "../utils/cvSkills";

const MAX_BYTES = 5 * 1024 * 1024;
// Material "upload file" icon path, inlined to avoid a whole icon package.
const UPLOAD = "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm1 11h-2v3h-2v-3H9l3-3.5 3 3.5zM13 9V3.5L18.5 9H13z";

const STEPS = [
  ["1", "Upload", "Choose your CV as a PDF."],
  ["2", "We find your skills", "Only the IT skills it names, such as Python or Azure, are read."],
  ["3", "See your jobs", "Open jobs are ranked for you, with skills worth adding."],
];

export default function CvUpload() {
  const [skills, setSkills] = useState(loadCvSkills);
  const [years, setYears] = useState<number | null>(loadCvYears);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);

  async function upload(file: File) {
    setError("");
    if (file.type !== "application/pdf" || file.size > MAX_BYTES) {
      setError("Upload a PDF file of 5 MB or less.");
      return;
    }
    setLoading(true);
    try {
      const { skills: found, years: foundYears } = await uploadCv(file);
      saveCvSkills(found, foundYears ?? null);
      setYears(foundYears ?? null);
      setSkills(found);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Unable to read your CV.");
    } finally {
      setLoading(false);
    }
  }

  function onDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file && !loading) void upload(file);
  }

  return (
    <Box component="main" sx={{ flex: 1, minWidth: 0, minHeight: 0, p: { xs: 2, md: 3 }, overflow: "auto" }}>
      <Stack spacing={3} sx={{ maxWidth: 720 }}>
        <PageHeader
          title="My CV"
          subtitle="Upload your CV once to see which open jobs fit it, and what to add to improve the rest."
        />

        <Box
          component="label"
          onDragOver={(event: DragEvent<HTMLElement>) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 1,
            p: 4,
            textAlign: "center",
            cursor: loading ? "progress" : "pointer",
            border: 2,
            borderStyle: "dashed",
            borderRadius: 2,
            borderColor: dragging ? "primary.main" : "divider",
            bgcolor: dragging ? "action.hover" : "background.paper",
            transition: "border-color 150ms, background-color 150ms",
            "&:hover, &:focus-within": { borderColor: "primary.main" },
            "@media (prefers-reduced-motion: reduce)": { transition: "none" },
          }}
        >
          <SvgIcon color="primary" sx={{ fontSize: 40 }}>
            <path d={UPLOAD} />
          </SvgIcon>
          <Typography fontWeight={600}>
            {skills.length > 0 ? "Drop a new CV here to replace it" : "Drop your CV here"}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            or click to choose a PDF (up to 5 MB, text based, not a scan)
          </Typography>
          <input
            hidden
            type="file"
            accept="application/pdf"
            disabled={loading}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = ""; // lets the same file be chosen again
              if (file) void upload(file);
            }}
          />
        </Box>

        {loading && <LinearProgress aria-label="Reading your CV" />}
        {error && <Alert severity="error">{error}</Alert>}

        {skills.length > 0 && (
          <Paper component="section" variant="outlined" aria-label="Skills found" sx={{ p: 2.5 }}>
            <Typography component="h2" variant="h6">
              {skills.length} skills found in your CV
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              These are what jobs are matched on. If one is missing, check that your CV names it in
              text.
            </Typography>
            <TextField
              label="Years of experience"
              type="number"
              size="small"
              value={years ?? ""}
              onChange={(event) => {
                const next = event.target.value === "" ? null : Math.min(60, Math.max(0, Math.floor(Number(event.target.value))));
                setYears(next);
                saveCvSkills(skills, next);
              }}
              helperText={years === null ? "Not found in your CV. Add it so jobs asking for more experience rank lower." : "Read from your CV; change it if it is wrong."}
              slotProps={{ htmlInput: { min: 0, max: 60 } }}
              sx={{ mb: 2, width: 280 }}
            />
            <Stack direction="row" gap={0.75} flexWrap="wrap">
              {skills.map((skill) => (
                <Chip key={skill} size="small" label={skill} />
              ))}
            </Stack>
            <Stack direction="row" gap={1} sx={{ mt: 2.5 }}>
              <Button component={RouterLink} to="/recommended-jobs" variant="contained">
                See recommended jobs
              </Button>
              <Button
                color="inherit"
                onClick={() => {
                  saveCvSkills(null);
                  setSkills([]);
                  setYears(null);
                }}
              >
                Remove saved CV
              </Button>
            </Stack>
          </Paper>
        )}

        {skills.length === 0 && (
          <Box
            component="ol"
            sx={{ m: 0, p: 0, listStyle: "none", display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" } }}
          >
            {STEPS.map(([number, title, text]) => (
              <Paper component="li" key={number} variant="outlined" sx={{ p: 2 }}>
                <Typography variant="caption" color="primary" fontWeight={700}>
                  Step {number}
                </Typography>
                <Typography fontWeight={600}>{title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {text}
                </Typography>
              </Paper>
            ))}
          </Box>
        )}

        <Typography variant="caption" color="text.secondary">
          Privacy: the PDF is read in memory and discarded. Only the skill names and years above are kept, in this
          browser, so they are gone if you clear site data or use another device.
        </Typography>
      </Stack>
    </Box>
  );
}
