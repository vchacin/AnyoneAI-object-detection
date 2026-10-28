import type { ComparisonEntry } from "@/lib/api/types";

function summarize(obj: Record<string, unknown>): [string, string][] {
  return Object.entries(obj)
    .filter(([, v]) => ["number", "string", "boolean"].includes(typeof v))
    .slice(0, 6)
    .map(([k, v]) => [k, typeof v === "number" ? String(Math.round(v * 1000) / 1000) : String(v)]);
}

export function ComparisonPair({ runId, entry }: { runId: string; entry: ComparisonEntry }) {
  const base = `/comparison-data/${runId}/`;
  const sides = [
    { title: "Model oficial", image: entry.official_image, meta: entry.official },
    { title: "ShelfVision", image: entry.shelfvision_image, meta: entry.shelfvision },
  ];
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {sides.map(({ title, image, meta }) => (
        <figure key={title}>
          <figcaption className="mb-2 text-sm font-semibold">{title}</figcaption>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={base + image} alt={title} className="w-full rounded-md bg-muted" />
          <p className="mt-2 flex flex-wrap gap-x-4 text-xs text-muted-foreground">
            {summarize(meta).map(([k, v]) => (
              <span key={k}>{k}: <b className="tnum font-medium text-foreground">{v}</b></span>
            ))}
          </p>
        </figure>
      ))}
    </div>
  );
}
