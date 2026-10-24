"use client";

import { BellOff } from "lucide-react";
import { useState } from "react";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { useAlerts, useTransitionAlert } from "@/hooks/queries/use-alerts";
import { useShelves } from "@/hooks/queries/use-shelves";
import { useStoreContext } from "@/hooks/use-store-context";
import { AlertFilters } from "./alert-filters";
import { AlertRow } from "./alert-row";

export function AlertsPanel({ storeId }: { storeId: string }) {
  const { canAck } = useStoreContext();
  const [status, setStatus] = useState("open");
  const [severity, setSeverity] = useState("");

  const shelves = useShelves(storeId);
  const alerts = useAlerts(storeId, { status: status === "all" ? "" : status, severity });
  const transition = useTransitionAlert();

  const shelfName = (id: string | null) => shelves.data?.find((s) => s.id === id)?.name ?? "Sin estante";

  return (
    <>
      <AlertFilters status={status} severity={severity} onStatus={setStatus} onSeverity={setSeverity} />
      <QueryBoundary
        query={alerts}
        skeleton={<RowsSkeleton rows={6} />}
        isEmpty={(rows) => !rows.length}
        empty={
          <EmptyState
            icon={BellOff}
            title="Sin alertas"
            description={status === "open" ? "No hay estantes por reponer. Buen trabajo." : "No hay alertas con este filtro."}
          />
        }
      >
        {(rows) => (
          <ul className="divide-y">
            {rows.map((a) => (
              <AlertRow
                key={a.id}
                alert={a}
                shelfName={shelfName(a.shelf_id)}
                canAck={canAck}
                busy={transition.isPending && transition.variables?.id === a.id}
                onTransition={(next) => transition.mutate({ id: a.id, status: next })}
              />
            ))}
          </ul>
        )}
      </QueryBoundary>
    </>
  );
}
