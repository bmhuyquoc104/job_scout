import { Autocomplete, Chip, Stack, TextField, Typography } from "@mui/material";
import { getRoleTitles } from "../api/client";
import { useApi } from "../api/useApi";

const EXAMPLES = ["Software Engineer", "Registered Nurse", "Electrician", "Accountant", "Chef"];

interface TitlePickerProps {
  title: string;
  onChange: (title: string) => void;
}

/** A job-title box: pick a role from every country's list, or type any title; example chips fill it. */
export default function TitlePicker({ title, onChange }: TitlePickerProps) {
  const { data: titles } = useApi(() => getRoleTitles(), [], "Unable to load job titles.");
  return (
    <>
      <Autocomplete
        freeSolo
        autoHighlight
        options={titles ?? []}
        value={title}
        // Typing or picking both set the title; clearing the box clears the result.
        onInputChange={(_, text) => onChange(text)}
        sx={{ maxWidth: 420, mb: 1.25 }}
        renderInput={(params) => <TextField {...params} label="Job title" autoFocus />}
      />
      <Stack direction="row" gap={0.75} flexWrap="wrap" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="caption" color="text.secondary">Try:</Typography>
        {EXAMPLES.map((example) => (
          <Chip key={example} size="small" variant="outlined" label={example} onClick={() => onChange(example)} />
        ))}
      </Stack>
    </>
  );
}
