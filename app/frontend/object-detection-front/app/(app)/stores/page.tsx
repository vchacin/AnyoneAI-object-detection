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

  if (!isSuper) return <EmptyState title="Sin acceso" description="Solo un super admin puede administrar tiendas." />;

  return (
    <>
      <PageHeader
        title="Tiendas"
        description="Cada tienda tiene sus propios estantes, cámaras, usuarios e inspecciones."
        actions={<Button size="sm" onClick={() => m.dialog.open("new")}><Plus /> Nueva tienda</Button>}
      />
      <QueryBoundary
        query={stores}
        skeleton={<RowsSkeleton />}
        isEmpty={(rows) => !rows.length}
        empty={<EmptyState icon={StoreIcon} title="Aún no hay tiendas" description="Crea la primera y, opcionalmente, su administrador." />}
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
