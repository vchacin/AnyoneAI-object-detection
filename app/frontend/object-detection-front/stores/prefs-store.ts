import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PrefsState {
  /** Modelo elegido en /analyze ("" = el activo del servidor). */
  model: string;
  /** Umbral de confianza; null = el del modelo/tienda. */
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
