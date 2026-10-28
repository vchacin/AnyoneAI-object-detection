"use client";

import { StatusPill } from "@/components/common/badges";
import { QueryBoundary } from "@/components/common/query-boundary";
import { Section, StatStrip } from "@/components/common/page-header";
import { useGlobalDashboard } from "@/hooks/queries/use-dashboard";
import { useStoresQuery } from "@/hooks/queries/use-stores";
import { RecentInspections } from "./recent-inspections";
import { SectionLink } from "./section-link";

export function GlobalView() {
  const dashboard = useGlobalDashboard();
  const stores = useStoresQuery();
  const storeName = (id: string) => stores.data?.find((s) => s.id === id)?.name ?? "Store";

  return (
    <>
      <StatStrip
        items={[
          { label: "Active stores", value: dashboard.data?.active_stores ?? "…" },
          { label: "Images this month", value: dashboard.data?.monthly_images_processed ?? "…" },
          { label: "Registered stores", value: stores.data?.length ?? "…" },
        ]}
      />

      <Section title="Latest inspections" description="Across all stores">
        <QueryBoundary query={dashboard}>
          {(d) => <RecentInspections rows={d.recent_inspections} labelFor={(i) => storeName(i.store_id)} />}
        </QueryBoundary>
      </Section>

      <Section title="Stores" actions={<SectionLink href="/stores">Manage</SectionLink>}>
        <ul className="divide-y">
          {(stores.data ?? []).slice(0, 8).map((s) => (
            <li key={s.id} className="flex items-center justify-between py-2.5 text-sm">
              <span>
                {s.name}
                {s.address && <span className="ml-2 text-xs text-muted-foreground">{s.address}</span>}
              </span>
              <StatusPill status={s.status} />
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}
