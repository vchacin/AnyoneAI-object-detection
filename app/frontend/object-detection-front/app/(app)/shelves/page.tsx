"use client";

import { PageHeader } from "@/components/common/page-header";
import { RequireStore } from "@/components/common/require-store";
import { ShelvesPanel } from "@/components/shelves/shelves-panel";

export default function ShelvesPage() {
  return (
    <>
      <PageHeader title="Estantes" description="Define las góndolas vigiladas y cuántos huecos tolera cada una antes de alertar." />
      <RequireStore>{(storeId) => <ShelvesPanel key={storeId} storeId={storeId} />}</RequireStore>
    </>
  );
}
