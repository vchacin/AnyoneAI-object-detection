"use client";

import { QueryBoundary } from "@/components/common/query-boundary";
import { Section, StatStrip } from "@/components/common/page-header";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { useCameraSummary } from "@/hooks/queries/use-cameras";
import { useStoreDashboard, useUsage } from "@/hooks/queries/use-dashboard";
import { useShelves } from "@/hooks/queries/use-shelves";
import { formatMs } from "@/lib/format";
import { CameraStatusList } from "./camera-status-list";
import { RecentInspections } from "./recent-inspections";
import { SectionLink } from "./section-link";
import { ShelfGaps } from "./shelf-gaps";

export function StoreView({ storeId }: { storeId: string }) {
  const dashboard = useStoreDashboard(storeId);
  const cameras = useCameraSummary(storeId);
  const shelves = useShelves(storeId);
  const usage = useUsage(storeId);

  const d = dashboard.data;
  const u = usage.data;
  const shelfName = (id: string | null) => shelves.data?.find((s) => s.id === id)?.name ?? "No shelf";

  return (
    <>
      <StatStrip
        items={[
          { label: "Open alerts", value: d?.open_alerts_count ?? "…", tone: d ? (d.open_alerts_count > 0 ? "gap" : "ok") : "default" },
          { label: "Inspections today", value: d?.inspections_today ?? "…" },
          { label: "Latency p50 / p95", value: u ? `${formatMs(u.latency_p50_ms)} / ${formatMs(u.latency_p95_ms)}` : "…" },
          { label: "Images processed", value: u?.images_processed ?? "…" },
        ]}
      />

      <div className="grid gap-x-12 lg:grid-cols-2">
        <Section title="Gaps by shelf" description="Based on the latest inspection for each shelf">
          <QueryBoundary
            query={dashboard}
            skeleton={<RowsSkeleton rows={4} />}
            isEmpty={(x) => !x.latest_by_shelf.length}
            empty={<EmptyState title="No shelves" description="Create shelves to track their replenishment status." />}
          >
            {(x) => <ShelfGaps shelves={x.latest_by_shelf} />}
          </QueryBoundary>
        </Section>

        <Section title="Cameras" actions={<SectionLink href="/cameras">Manage</SectionLink>}>
          <QueryBoundary
            query={cameras}
            skeleton={<RowsSkeleton rows={4} />}
            isEmpty={(x) => !x.length}
            empty={<EmptyState title="No cameras" description="Register a camera to receive automatic inspections." />}
          >
            {(x) => <CameraStatusList cameras={x} />}
          </QueryBoundary>
        </Section>
      </div>

      <Section title="Latest inspections" actions={<SectionLink href="/inspections">View all</SectionLink>}>
        <QueryBoundary query={dashboard}>
          {(x) => <RecentInspections rows={x.latest_inspections} labelFor={(i) => shelfName(i.shelf_id)} />}
        </QueryBoundary>
      </Section>
    </>
  );
}
