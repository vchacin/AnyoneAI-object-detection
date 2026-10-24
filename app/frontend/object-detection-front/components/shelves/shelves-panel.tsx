"use client";

import { Plus, Rows3 } from "lucide-react";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { useShelves } from "@/hooks/queries/use-shelves";
import { useShelfManager } from "@/hooks/use-shelf-manager";
import { useStoreContext } from "@/hooks/use-store-context";
import { ShelfFormDialog } from "./shelf-form-dialog";
import { ShelvesTable } from "./shelves-table";

export function ShelvesPanel({ storeId }: { storeId: string }) {
  const { canManage } = useStoreContext();
  const shelves = useShelves(storeId);
  const m = useShelfManager(storeId);

  return (
    <>
      {canManage && (
        <div className="mb-4 flex justify-end">
          <Button size="sm" onClick={() => m.dialog.open("new")}>
            <Plus /> Nuevo estante
          </Button>
        </div>
      )}
      <QueryBoundary
        query={shelves}
        skeleton={<RowsSkeleton />}
        isEmpty={(rows) => !rows.length}
        empty={<EmptyState icon={Rows3} title="Sin estantes" description="Crea los estantes que quieres vigilar y define cuántos huecos toleras." />}
      >
        {(rows) => <ShelvesTable shelves={rows} canManage={canManage} onEdit={(s) => m.dialog.open(s)} />}
      </QueryBoundary>
      <ShelfFormDialog
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
