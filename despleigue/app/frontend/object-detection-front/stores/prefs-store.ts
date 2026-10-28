import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PrefsState {
  /** Model elegido en /analyze ("" = el active del servidor). */
  model: string;
  /** Confidence threshold; null = el del modelo/store. */
  conf: number | null;
  persist: boolean;
  showObjects: boolean;
  showMissing: boolean;
  showLabels: boolean;
  set: (patch: Partial<Omit<PrefsState, "set">>) => void;
}

export const usePrefs = create<PrefsState>()(
  persist(
    (set) => ({
      model: "",
      conf: null,
      persist: true,
      showObjects: true,
      showMissing: true,
      showLabels: false,
      set: (patch) => set(patch),
    }),
    { name: "shelfvision.prefs", skipHydration: true },
  ),
);
