const STORAGE_KEY = "lakarra.content-creator.brief";

export interface SavedBrief {
  businessGoal: string;
  targetAudience: string;
  product: string;
  constraints: string;
}

export const DEFAULT_BRIEF: SavedBrief = {
  businessGoal: "Increase engagement",
  targetAudience: "Malaysian couples aged 23-35",
  product: "Digital Wedding Invitation",
  constraints: "Simple aesthetic\nLess than 15 seconds",
};

export function loadBrief(): SavedBrief {
  if (typeof window === "undefined") return DEFAULT_BRIEF;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_BRIEF;
    return { ...DEFAULT_BRIEF, ...JSON.parse(raw) } as SavedBrief;
  } catch {
    return DEFAULT_BRIEF;
  }
}

export function saveBrief(brief: SavedBrief): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(brief));
}
