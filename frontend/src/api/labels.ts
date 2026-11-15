/** Seniority levels in order, graduate to management; "unspecified" means the title names none. */
export const SENIORITY_ORDER = ["graduate", "junior", "mid", "senior", "lead", "management", "unspecified"];

export const SENIORITY_LABELS: Record<string, string> = {
  graduate: "Graduate / intern",
  junior: "Junior",
  mid: "Mid-level",
  senior: "Senior",
  lead: "Lead / principal",
  management: "Management",
  unspecified: "Not stated",
};
