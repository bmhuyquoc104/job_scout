import { useEffect, useState } from "react";
import { Alert, CircularProgress } from "@mui/material";
import { useCountry } from "../country/CountryContext";

const SLOW_MS = 4000;

/** The free host sleeps when idle, so the first visit waits up to a minute; say so instead of looking broken. */
export default function WakingNotice() {
  const { loading } = useCountry();
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!loading) return;
    const timer = setTimeout(() => setSlow(true), SLOW_MS);
    return () => clearTimeout(timer);
  }, [loading]);

  if (!loading || !slow) return null;
  return (
    <Alert
      role="status"
      severity="info"
      icon={<CircularProgress size={18} />}
      sx={{ position: "fixed", top: 16, left: "50%", transform: "translateX(-50%)", zIndex: 1400, maxWidth: "calc(100% - 32px)" }}
    >
      Waking up the server. The first visit can take up to a minute, thanks for waiting.
    </Alert>
  );
}
