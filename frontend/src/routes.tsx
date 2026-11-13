import { lazy, Suspense } from "react";
import { Box, LinearProgress, Typography } from "@mui/material";
import { Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Diagrams from "./pages/Diagrams";
import JobDetailPage from "./pages/JobDetail";
// The postings page carries the data grid, the heaviest dependency, so it loads on demand.
const Jobs = lazy(() => import("./pages/Jobs"));
const Immigration = lazy(() => import("./pages/Immigration"));
const CvUpload = lazy(() => import("./pages/CvUpload"));
const RecommendedJobs = lazy(() => import("./pages/RecommendedJobs"));

export default function AppRoutes() {
  return (
    <Suspense fallback={<LinearProgress aria-label="Loading page" sx={{ flex: 1, alignSelf: "flex-start" }} />}>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/categories/:categoryId" element={<Jobs />} />
      <Route path="/categories/:categoryId/diagrams" element={<Diagrams />} />
      <Route path="/immigration" element={<Immigration />} />
      <Route path="/green-list" element={<Navigate to="/immigration" replace />} />
      <Route path="/cv" element={<CvUpload />} />
      <Route path="/recommended-jobs" element={<RecommendedJobs />} />
      <Route path="/jobs/:jobId" element={<JobDetailPage />} />
      <Route
        path="*"
        element={
          <Box component="main" sx={{ flex: 1, p: 3, overflow: "auto" }}>
            <Typography>Page not found.</Typography>
          </Box>
        }
      />
    </Routes>
    </Suspense>
  );
}
