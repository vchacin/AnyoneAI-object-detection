import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Segmento dibujado sobre la imagen de referencia de la camera.
 * Coordenadas normalizadas 0–1 respecto al ancho/alto de la imagen,
 * para sobrevivir a cualquier resolución de capture.
 */
export interface Zone {
  id: string;
  name: string;
  labelId: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ZoneLabel {
  id: string;
  name: string;
  unitPrice: string;
  margin: string;
}

/** Preserve legacy segments while sharing identical labels. */
export function migrateZones(state: unknown): { zones: Zone[]; labels: ZoneLabel[] } {
  const old = state as { zones?: Zone[]; labels?: ZoneLabel[] } | null;
  if (old?.labels) return { zones: old.zones ?? [], labels: old.labels };
  const labels: ZoneLabel[] = [];
  const zones = (old?.zones ?? []).map((zone) => {
    let label = labels.find((item) => item.name === zone.name);
    if (!label) {
      label = { id: `legacy:${zone.id}`, name: zone.name, unitPrice: "", margin: "" };
      labels.push(label);
    }
    return { ...zone, labelId: label.id };
  });
  return { zones, labels };
}

interface ZonesState {
  zones: Zone[];
  labels: ZoneLabel[];
  addZone: (zone: Omit<Zone, "id" | "labelId">) => void;
  addLabel: (name: string) => void;
  updateLabel: (id: string, update: Partial<Pick<ZoneLabel, "name" | "unitPrice" | "margin">>) => void;
  assignLabel: (zoneId: string, labelId: string) => void;
  resizeZone: (id: string, rect: Pick<Zone, "x" | "y" | "w" | "h">) => void;
  removeZone: (id: string) => void;
  clear: () => void;
}

export const useZones = create<ZonesState>()(
  persist(
    (set) => ({
      zones: [],
      labels: [],
      addZone: (zone) => set((s) => {
        const label = { id: crypto.randomUUID(), name: zone.name, unitPrice: "", margin: "" };
        return { labels: [...s.labels, label], zones: [...s.zones, { ...zone, id: crypto.randomUUID(), labelId: label.id }] };
      }),
      addLabel: (name) => set((s) => ({ labels: [...s.labels, { id: crypto.randomUUID(), name, unitPrice: "", margin: "" }] })),
      updateLabel: (id, update) => set((s) => ({
        labels: s.labels.map((label) => label.id === id ? { ...label, ...update } : label),
        zones: update.name === undefined ? s.zones : s.zones.map((zone) => zone.labelId === id ? { ...zone, name: update.name! } : zone),
      })),
      assignLabel: (zoneId, labelId) => set((s) => {
        const label = s.labels.find((item) => item.id === labelId);
        return label ? { zones: s.zones.map((zone) => zone.id === zoneId ? { ...zone, labelId, name: label.name } : zone) } : {};
      }),
      resizeZone: (id, rect) =>
        set((s) => ({ zones: s.zones.map((z) => (z.id === id ? { ...z, ...rect } : z)) })),
      removeZone: (id) => set((s) => ({ zones: s.zones.filter((z) => z.id !== id) })),
      clear: () => set({ zones: [] }),
    }),
    { name: "shelfvision.demo.zones", skipHydration: true, version: 1, migrate: (state) => migrateZones(state) },
  ),
);
