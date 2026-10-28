"use client";

import { BarChart3, Clock, Package } from "lucide-react";
import type { DemoMetrics } from "@/hooks/use-demo";

const ICONS = { estado: BarChart3, captures: Package, periodo: Clock } as const;

/** Tres KPIs del mockup: estado del anaquel, captures del día y periodo observado. */
export function DemoMetrics({ metrics }: { metrics: DemoMetrics }) {
  const items = [
    { icon: ICONS.estado, label: "Shelf status", value: metrics.estado, strong: true },
    { icon: ICONS.captures, label: "Images analyzed", value: metrics.captures.toString() },
    { icon: ICONS.periodo, label: "Analyzed times", value: metrics.observedHours },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {items.map((it) => (
        <div key={it.label} className="flex items-center gap-4 rounded-xl border border-border bg-card p-4 shadow-sm">
          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-primary/10 text-primary">
            <it.icon className="size-5" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium text-muted-foreground">{it.label}</p>
            <p
              className={
                it.strong
                  ? "truncate text-lg font-semibold tracking-tight text-card-foreground"
                  : "tnum text-lg font-semibold tracking-tight text-card-foreground"
              }
            >
              {it.value}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
