const KEY = "cv-skills";
const YEARS_KEY = "cv-years";

// The CV's skills stay in this browser only (the file itself is never kept anywhere).
export function loadCvSkills(): string[] {
  try {
    const skills = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(skills) ? skills.filter((skill) => typeof skill === "string") : [];
  } catch {
    return [];
  }
}

/** Years of experience the CV states, or null when it states none. */
export function loadCvYears(): number | null {
  try {
    const years = Number(localStorage.getItem(YEARS_KEY));
    return localStorage.getItem(YEARS_KEY) && Number.isInteger(years) ? years : null;
  } catch {
    return null;
  }
}

export function saveCvSkills(skills: string[] | null, years: number | null = null) {
  try {
    if (skills) localStorage.setItem(KEY, JSON.stringify(skills));
    else localStorage.removeItem(KEY);
    if (skills && years !== null) localStorage.setItem(YEARS_KEY, String(years));
    else localStorage.removeItem(YEARS_KEY);
  } catch {
    // Storage can be blocked; the CV then has to be uploaded again on the next visit.
  }
}
