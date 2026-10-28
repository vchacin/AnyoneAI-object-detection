"use client";

import { PageHeader } from "@/components/common/page-header";
import { RequireStore } from "@/components/common/require-store";
import { ShelvesPanel } from "@/components/shelves/shelves-panel";

export default function ShelvesPage() {
  return (
    <>
      <PageHeader title="Shelves" description="Set up monitored shelves and the number of gaps allowed before an alert is triggered." />
      <RequireStore>{(storeId) => <ShelvesPanel key={storeId} storeId={storeId} />}</RequireStore>
    </>
  );
}
