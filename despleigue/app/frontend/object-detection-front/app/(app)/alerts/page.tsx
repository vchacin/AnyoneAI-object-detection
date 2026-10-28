"use client";

import { AlertsPanel } from "@/components/alerts/alerts-panel";
import { PageHeader } from "@/components/common/page-header";
import { RequireStore } from "@/components/common/require-store";

export default function AlertsPage() {
  return (
    <>
      <PageHeader
        title="Alerts"
        description="Alerts are created when an inspection exceeds the shelf gap threshold. Acknowledge and close them after replenishment."
      />
      <RequireStore>{(storeId) => <AlertsPanel key={storeId} storeId={storeId} />}</RequireStore>
    </>
  );
}
