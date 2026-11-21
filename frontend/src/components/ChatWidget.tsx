import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  Box,
  Chip,
  CircularProgress,
  Fab,
  Grow,
  IconButton,
  Link,
  Paper,
  Stack,
  SvgIcon,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { ApiError, sendChat, type ChatResponse } from "../api/client";
import { useCountry } from "../country/CountryContext";

// Material icon paths, inlined to avoid a whole icon package.
const ICONS = {
  chat: "M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z",
  close: "M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
  send: "M2.01 21 23 12 2.01 3 2 10l15 2-15 2z",
  restart:
    "M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
};

const SUGGESTIONS = [
  "Senior python jobs with visa sponsorship above 80k",
  "Which country sponsors data engineers the most?",
  "Is hiring growing this month?",
  "How can I immigrate to New Zealand?",
];

type Turn = { question: string; answer: ChatResponse };

function Icon({ path }: { path: string }) {
  return (
    <SvgIcon fontSize="small">
      <path d={path} />
    </SvgIcon>
  );
}

const bubble = { px: 1.5, py: 1, maxWidth: "88%", borderRadius: 2.5, fontSize: 14.5, lineHeight: 1.5 } as const;

/** A launcher button that opens a small assistant panel on every page. Answers come from the site's own data. */
export default function ChatWidget() {
  const { country, countryName } = useCountry();
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const launcher = useRef<HTMLButtonElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const lastTurn = useRef<HTMLDivElement>(null);
  const behavior = reduceMotion ? "auto" : "smooth";

  // A new answer scrolls to its start so long results are read from the top; waiting and
  // errors scroll to the bottom.
  useEffect(() => {
    lastTurn.current?.scrollIntoView({ block: "start", behavior });
  }, [turns, behavior]);
  useEffect(() => {
    if (pending || error) end.current?.scrollIntoView({ block: "end", behavior });
  }, [pending, error, behavior]);
  // Opening the panel shows the latest message, not the oldest.
  useEffect(() => {
    if (open) end.current?.scrollIntoView({ block: "end" });
  }, [open]);

  function startNewChat() {
    setTurns([]);
    setError("");
  }

  function toggle(next: boolean) {
    setOpen(next);
    // Focus follows the panel: into the question box on open, back to the launcher on close.
    if (next) setTimeout(() => input.current?.focus(), 0);
    else launcher.current?.focus();
  }

  async function ask(text: string) {
    const question = text.trim();
    if (!question || pending) return;
    setPending(question);
    setDraft("");
    setError("");
    try {
      const answer = await sendChat(question, country, turns.slice(-5).map((turn) => turn.question));
      setTurns((previous) => [...previous, { question, answer }]);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "I couldn't reach the server. Try again.");
    } finally {
      setPending("");
      input.current?.focus();
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void ask(draft);
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape") toggle(false);
  }

  const asking = turns.length === 0 && !pending;

  return (
    <>
      <Grow in={open} timeout={reduceMotion ? 0 : 180} style={{ transformOrigin: "bottom right" }} unmountOnExit>
        <Paper
          role="dialog"
          aria-label="Job assistant"
          elevation={8}
          onKeyDown={onKeyDown}
          sx={{
            position: "fixed",
            zIndex: (theme) => theme.zIndex.speedDial,
            right: { xs: 8, sm: 20 },
            left: { xs: 8, sm: "auto" },
            bottom: { xs: 8, sm: 88 },
            width: { sm: 380 },
            height: { xs: "min(75dvh, 600px)", sm: "min(560px, calc(100dvh - 112px))" },
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            border: 1,
            borderColor: "divider",
            borderRadius: 3,
          }}
        >
          <Stack direction="row" alignItems="center" gap={1} sx={{ px: 2, py: 1.25, borderBottom: 1, borderColor: "divider" }}>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="subtitle1" fontWeight={750} lineHeight={1.2}>
                Job assistant
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap component="p">
                Ask about any country · defaults to {countryName}
              </Typography>
            </Box>
            <Tooltip title="New chat">
              <span>
                <IconButton size="small" aria-label="Start a new chat" disabled={asking} onClick={startNewChat}>
                  <Icon path={ICONS.restart} />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="Close">
              <IconButton size="small" aria-label="Close assistant" onClick={() => toggle(false)}>
                <Icon path={ICONS.close} />
              </IconButton>
            </Tooltip>
          </Stack>

          <Stack role="log" aria-live="polite" spacing={1.25} sx={{ flex: 1, minHeight: 0, overflowY: "auto", p: 2 }}>
            <Box sx={{ ...bubble, bgcolor: "action.hover", alignSelf: "flex-start" }}>
              Hi! Ask me about jobs, salaries, visa sponsorship or immigration routes. I use {countryName} unless you name another country, and I’ll filter by any level, salary or “visa” you mention.
            </Box>
            {asking && (
              <Stack direction="row" gap={0.75} flexWrap="wrap" aria-label="Suggested questions">
                {SUGGESTIONS.map((suggestion) => (
                  <Chip key={suggestion} label={suggestion} variant="outlined" size="small" onClick={() => void ask(suggestion)} sx={{ height: "auto", "& .MuiChip-label": { whiteSpace: "normal", py: 0.5 } }} />
                ))}
              </Stack>
            )}
            {turns.map(({ question, answer }, index) => (
              <Stack key={index} spacing={1.25} ref={index === turns.length - 1 ? lastTurn : undefined}>
                <Box sx={{ ...bubble, bgcolor: "primary.main", color: "primary.contrastText", alignSelf: "flex-end", ml: "auto" }}>{question}</Box>
                <Box sx={{ ...bubble, bgcolor: "action.hover", alignSelf: "flex-start", whiteSpace: "pre-wrap" }}>
                  {answer.reply}
                  {answer.jobs.length > 0 && (
                    <Stack component="ul" spacing={0.75} sx={{ m: 0, mt: 1, pl: 2, whiteSpace: "normal" }}>
                      {answer.jobs.map((job) => (
                        <li key={job.id}>
                          <Link component={RouterLink} to={`/jobs/${job.id}`} fontWeight={600} underline="hover">
                            {job.position}
                          </Link>
                          <Typography variant="caption" color="text.secondary" component="div">
                            {[job.company_name, job.location, job.salary_label].filter(Boolean).join(" · ")}
                          </Typography>
                        </li>
                      ))}
                    </Stack>
                  )}
                  {answer.more_url && (
                    <Link component={RouterLink} to={answer.more_url} onClick={() => toggle(false)} fontWeight={600} underline="hover" sx={{ display: "block", mt: 1, whiteSpace: "normal" }}>
                      See all matching jobs →
                    </Link>
                  )}
                  {answer.understood.length > 0 && (
                    <Stack direction="row" gap={0.5} flexWrap="wrap" sx={{ mt: 1 }} aria-label="What I understood">
                      {answer.understood.map((part) => (
                        <Chip key={part} size="small" variant="outlined" label={part} />
                      ))}
                    </Stack>
                  )}
                </Box>
              </Stack>
            ))}
            {pending && (
              <>
                <Box sx={{ ...bubble, bgcolor: "primary.main", color: "primary.contrastText", alignSelf: "flex-end", ml: "auto" }}>{pending}</Box>
                <Stack direction="row" alignItems="center" gap={1} sx={{ color: "text.secondary" }}>
                  <CircularProgress size={14} aria-hidden />
                  <Typography variant="caption">Looking that up…</Typography>
                </Stack>
              </>
            )}
            {error && (
              <Box role="alert" sx={{ ...bubble, bgcolor: "action.hover", color: "error.main", alignSelf: "flex-start" }}>
                {error}
              </Box>
            )}
            <div ref={end} />
          </Stack>

          <Stack component="form" direction="row" alignItems="center" gap={1} onSubmit={onSubmit} sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Ask about jobs…"
              value={draft}
              inputRef={input}
              onChange={(event) => setDraft(event.target.value)}
              slotProps={{ htmlInput: { maxLength: 500, "aria-label": "Your question", autoComplete: "off" } }}
            />
            <Tooltip title="Send">
              <span>
                <IconButton type="submit" color="primary" aria-label="Send question" disabled={!!pending || !draft.trim()}>
                  <Icon path={ICONS.send} />
                </IconButton>
              </span>
            </Tooltip>
          </Stack>
        </Paper>
      </Grow>

      <Tooltip title={open ? "Close assistant" : "Ask the assistant"} placement="left">
        <Fab
          ref={launcher}
          color="primary"
          aria-label={open ? "Close assistant" : "Open assistant"}
          aria-expanded={open}
          onClick={() => toggle(!open)}
          sx={{
            position: "fixed",
            zIndex: (theme) => theme.zIndex.speedDial,
            right: { xs: 16, sm: 20 },
            bottom: "max(16px, env(safe-area-inset-bottom))",
            // On phones the open panel covers the launcher; its own close button takes over.
            display: { xs: open ? "none" : "inline-flex", sm: "inline-flex" },
          }}
        >
          <Icon path={open ? ICONS.close : ICONS.chat} />
        </Fab>
      </Tooltip>
    </>
  );
}
