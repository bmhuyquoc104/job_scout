const KEY = "cv-skills";

// The CV's skills stay in this browser only (the file itself is never kept anywhere).
export function loadCvSkills(): string[] {
  try {
    const skills = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(skills) ? skills.filter((skill) => typeof skill === "string") : [];
  } catch {
    return [];
  }
}

export function saveCvSkills(skills: string[] | null) {
  try {
    if (skills) localStorage.setItem(KEY, JSON.stringify(skills));
    else localStorage.removeItem(KEY);
  } catch {
    // Storage can be blocked; the CV then has to be uploaded again on the next visit.
  }
}
