"use client";

import { Camera as CameraIcon, Plus } from "lucide-react";
import { ConfirmDialog } from "@/components/common/form";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { useCameras } from "@/hooks/queries/use-cameras";
import { useShelves } from "@/hooks/queries/use-shelves";
import { useCameraManager } from "@/hooks/use-camera-manager";
import { useStoreContext } from "@/hooks/use-store-context";
import { CameraFormDialog } from "./camera-form-dialog";
import { CamerasTable } from "./cameras-table";
import { TokenDialog } from "./token-dialog";

export function CamerasPanel({ storeId }: { storeId: string }) {
  const { canManage } = useStoreContext();
  const cameras = useCameras(storeId);
  const shelves = useShelves(storeId);
  const m = useCameraManager(storeId);

  const shelfName = (id: string | null) => shelves.data?.find((s) => s.id === id)?.name;

  return (
    <>
      {canManage && (
        <div className="mb-4 flex justify-end">
          <Button size="sm" onClick={() => m.dialog.open("new")}>
            <Plus /> Nueva cámara
          </Button>
        </div>
      )}

      <QueryBoundary
        query={cameras}
        skeleton={<RowsSkeleton />}
        isEmpty={(rows) => !rows.length}
        empty={<EmptyState icon={CameraIcon} title="Sin cámaras" description="Registra una cámara y vincúlala a un estante para inspecciones automáticas." />}
      >
        {(rows) => (
          <CamerasTable cameras={rows} shelfName={shelfName} canManage={canManage}
            onEdit={(c) => m.dialog.open(c)} onRotate={m.setRotating} />
        )}
      </QueryBoundary>

      <CameraFormDialog
        open={m.dialog.isOpen}
        isNew={m.dialog.isNew}
        draft={m.dialog.draft}
        shelves={shelves.data ?? []}
        busy={m.saving}
        onChange={m.dialog.patch}
        onSubmit={m.save}
        onClose={m.dialog.close}
      />
      <ConfirmDialog
        open={!!m.rotating}
        onOpenChange={(o) => !o && m.setRotating(null)}
        title="¿Rotar token?"
        description={`El token actual de «${m.rotating?.name}» dejará de funcionar de inmediato. Tendrás que configurar el nuevo en la cámara.`}
        confirmLabel="Rotar token"
        destructive
        onConfirm={m.confirmRotate}
      />
      <TokenDialog token={m.token} onClose={m.clearToken} />
    </>
  );
}
