"use client";

import { AlertsPanel } from "@/components/alerts/alerts-panel";
import { PageHeader } from "@/components/common/page-header";
import { RequireStore } from "@/components/common/require-store";

export default function AlertsPage() {
  return (
    <>
      <PageHeader
        title="Alertas"
        description="Se crean cuando una inspección supera el umbral de huecos del estante. Atiéndelas y ciérralas al reponer."
      />
      <RequireStore>{(storeId) => <AlertsPanel key={storeId} storeId={storeId} />}</RequireStore>
    </>
  );
}
