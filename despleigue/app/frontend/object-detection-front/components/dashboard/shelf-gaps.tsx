import type { StoreDashboard } from "@/lib/api/types";

/** Barras horizontales de gaps por shelf (ultima inspeccion de cada uno). */
export function ShelfGaps({ shelves }: { shelves: StoreDashboard["latest_by_shelf"] }) {
  const max = Math.max(1, ...shelves.map((s) => s.n_missing));
  return (
    <ul className="grid gap-3">
      {[...shelves]
        .sort((a, b) => b.n_missing - a.n_missing)
        .map((s) => (
          <li key={s.shelf_id} className="grid grid-cols-[minmax(0,10rem)_1fr_2rem] items-center gap-3 text-sm">
            <span className="truncate">{s.name}</span>
            <span className="h-1.5 overflow-hidden rounded-full bg-muted">
              <span
                className="block h-full rounded-full bg-gap transition-[width]"
                style={{ width: `${(s.n_missing / max) * 100}%` }}
              />
            </span>
            <span className="tnum text-right font-medium">{s.n_missing}</span>
          </li>
        ))}
    </ul>
  );
}
