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
  const shelfName = (id: string | null) => shelves.data?.find((s) => s.id === id)?.name ?? "Sin estante";

  return (
    <>
      <StatStrip
        items={[
          { label: "Alertas abiertas", value: d?.open_alerts_count ?? "…", tone: d ? (d.open_alerts_count > 0 ? "gap" : "ok") : "default" },
          { label: "Inspecciones hoy", value: d?.inspections_today ?? "…" },
          { label: "Latencia p50 / p95", value: u ? `${formatMs(u.latency_p50_ms)} / ${formatMs(u.latency_p95_ms)}` : "…" },
          { label: "Imágenes procesadas", value: u?.images_processed ?? "…" },
        ]}
      />

      <div className="grid gap-x-12 lg:grid-cols-2">
        <Section title="Huecos por estante" description="Según la última inspección de cada uno">
          <QueryBoundary
            query={dashboard}
            skeleton={<RowsSkeleton rows={4} />}
            isEmpty={(x) => !x.latest_by_shelf.length}
            empty={<EmptyState title="Sin estantes" description="Crea estantes para seguir su nivel de reposición." />}
          >
            {(x) => <ShelfGaps shelves={x.latest_by_shelf} />}
          </QueryBoundary>
        </Section>

        <Section title="Cámaras" actions={<SectionLink href="/cameras">Gestionar</SectionLink>}>
          <QueryBoundary
            query={cameras}
            skeleton={<RowsSkeleton rows={4} />}
            isEmpty={(x) => !x.length}
            empty={<EmptyState title="Sin cámaras" description="Registra una cámara para recibir inspecciones automáticas." />}
          >
            {(x) => <CameraStatusList cameras={x} />}
          </QueryBoundary>
        </Section>
      </div>

      <Section title="Últimas inspecciones" actions={<SectionLink href="/inspections">Ver todas</SectionLink>}>
        <QueryBoundary query={dashboard}>
          {(x) => <RecentInspections rows={x.latest_inspections} labelFor={(i) => shelfName(i.shelf_id)} />}
        </QueryBoundary>
      </Section>
    </>
  );
}
