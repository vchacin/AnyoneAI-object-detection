"use client";

import { Plus, Store as StoreIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/common/page-header";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { StoreFormDialog } from "@/components/stores/store-form-dialog";
import { StoresTable } from "@/components/stores/stores-table";
import { Button } from "@/components/ui/button";
import { useStoresQuery } from "@/hooks/queries/use-stores";
import { useStoreContext } from "@/hooks/use-store-context";
import { useStoreManager } from "@/hooks/use-store-manager";
import { useAuth } from "@/stores/auth-store";

export default function StoresPage() {
  const router = useRouter();
  const { isSuper, storeId } = useStoreContext();
  const setActiveStore = useAuth((s) => s.setActiveStore);
  const stores = useStoresQuery(isSuper);
  const m = useStoreManager();

  if (!isSuper) return <EmptyState title="Access denied" description="Only a super admin can manage stores." />;

  return (
    <>
      <PageHeader
        title="Stores"
        description="Each store has its own shelves, cameras, users, and inspections."
        actions={<Button size="sm" onClick={() => m.dialog.open("new")}><Plus /> New store</Button>}
      />
      <QueryBoundary
        query={stores}
        skeleton={<RowsSkeleton />}
        isEmpty={(rows) => !rows.length}
        empty={<EmptyState icon={StoreIcon} title="No stores yet" description="Create the first one and optionally its administrator." />}
      >
        {(rows) => (
          <StoresTable
            stores={rows}
            activeId={storeId}
            onEdit={(s) => m.dialog.open(s)}
            onOpen={(s) => {
              setActiveStore(s.id);
              router.push("/");
            }}
          />
        )}
      </QueryBoundary>
      <StoreFormDialog
        open={m.dialog.isOpen}
        isNew={m.dialog.isNew}
        draft={m.dialog.draft}
        busy={m.saving}
        onChange={m.dialog.patch}
        onSubmit={m.save}
        onClose={m.dialog.close}
      />
    </>
  );
}
