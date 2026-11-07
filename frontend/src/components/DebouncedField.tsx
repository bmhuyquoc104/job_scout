import { useEffect, useRef, useState } from "react";
import { TextField } from "@mui/material";

const DEBOUNCE_MS = 300;

interface DebouncedFieldProps {
  label: string;
  value: string;
  onCommit: (value: string) => void;
  type?: "text" | "number";
  autoFocus?: boolean;
}

/**
 * Text input that reports its value shortly after typing stops, so each keystroke is not a request.
 * It also reports on Enter, on blur and when it unmounts (e.g. the menu closes), so nothing typed is lost.
 */
export default function DebouncedField({ label, value, onCommit, type = "text", autoFocus }: DebouncedFieldProps) {
  const [text, setText] = useState(value);
  const timer = useRef<number | undefined>(undefined);
  const pending = useRef<string | null>(null);
  const commitRef = useRef(onCommit);

  useEffect(() => {
    commitRef.current = onCommit;
  });

  function flush() {
    window.clearTimeout(timer.current);
    if (pending.current !== null) {
      const next = pending.current;
      pending.current = null;
      commitRef.current(next);
    }
  }

  // Unmounting counts as "done typing".
  useEffect(() => flush, []);

  return (
    <TextField
      size="small"
      fullWidth
      label={label}
      type={type}
      autoFocus={autoFocus}
      value={text}
      onChange={(event) => {
        setText(event.target.value);
        pending.current = event.target.value.trim();
        window.clearTimeout(timer.current);
        timer.current = window.setTimeout(flush, DEBOUNCE_MS);
      }}
      onBlur={flush}
      onKeyDown={(event) => {
        if (event.key === "Enter") flush();
      }}
      slotProps={type === "number" ? { htmlInput: { min: 0, step: 5000 } } : undefined}
    />
  );
}
