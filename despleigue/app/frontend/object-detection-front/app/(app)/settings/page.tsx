"use client";

import { PageHeader } from "@/components/common/page-header";
import { QueryBoundary } from "@/components/common/query-boundary";
import { RequireStore } from "@/components/common/require-store";
import { RowsSkeleton } from "@/components/common/states";
import { SettingsForm } from "@/components/settings/settings-form";
import { useStoreSettings } from "@/hooks/queries/use-stores";

function SettingsLoader({ storeId }: { storeId: string }) {
  const settings = useStoreSettings(storeId);
  return (
    <QueryBoundary query={settings} skeleton={<RowsSkeleton rows={4} />}>
      {(data) => <SettingsForm storeId={storeId} initial={data} />}
    </QueryBoundary>
  );
}

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Store operating hours and detection rules." />
      <RequireStore>{(storeId) => <SettingsLoader key={storeId} storeId={storeId} />}</RequireStore>
    </>
  );
}
