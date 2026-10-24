"use client";

import { Download, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Pagination } from "@/components/common/pagination";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { InspectionSheet } from "@/components/inspections/inspection-sheet";
import { InspectionsFilters } from "@/components/inspections/inspections-filters";
import { InspectionsTable } from "@/components/inspections/inspections-table";
import { Button } from "@/components/ui/button";
import { useCameras } from "@/hooks/queries/use-cameras";
import { useExportInspections, useInspections } from "@/hooks/queries/use-inspections";
import { useShelves } from "@/hooks/queries/use-shelves";
import { INSPECTIONS_PAGE_SIZE, useInspectionFilters } from "@/hooks/use-inspection-filters";
import { useOpenInspection } from "@/hooks/use-open-inspection";
import { useStoreContext } from "@/hooks/use-store-context";

export default function InspectionsPage() {
  const { storeId, canManage } = useStoreContext();
  const f = useInspectionFilters(storeId);
  const selected = useOpenInspection();
  const exportAll = useExportInspections();

  const cameras = useCameras(storeId);
  const shelves = useShelves(storeId);
  const list = useInspections(f.filters, f.page, INSPECTIONS_PAGE_SIZE);

  const shelfName = (id: string | null) => shelves.data?.find((s) => s.id === id)?.name;
  const cameraName = (id: string | null) => cameras.data?.find((c) => c.id === id)?.name;

  return (
    <>
      <PageHeader
        title="Inspecciones"
        description="Historial de imágenes analizadas, con sus productos y huecos detectados."
        actions={
          <Button variant="outline" size="sm" disabled={exportAll.isPending} onClick={() => exportAll.mutate(f.filters)}>
            {exportAll.isPending ? <Loader2 className="animate-spin" /> : <Download />} Exportar JSONL
          </Button>
        }
      />

      <InspectionsFilters
        showScope={!!storeId}
        cameras={cameras.data}
        shelves={shelves.data}
        values={f.values}
        onCamera={f.setCameraId}
        onShelf={f.setShelfId}
        onFrom={f.setFrom}
        onTo={f.setTo}
      />

      <QueryBoundary
        query={list}
        skeleton={<RowsSkeleton rows={8} />}
        isEmpty={(rows) => !rows.length}
        empty={<EmptyState title="Sin inspecciones" description="No hay resultados para estos filtros." />}
      >
        {(rows) => (
          <>
            <InspectionsTable
              rows={rows}
              dimmed={list.isPlaceholderData}
              shelfName={shelfName}
              cameraName={cameraName}
              onSelect={(i) => selected.open(i.id)}
            />
            <Pagination page={f.page} hasNext={rows.length >= INSPECTIONS_PAGE_SIZE} onChange={f.setPage} />
          </>
        )}
      </QueryBoundary>

      <InspectionSheet
        inspection={selected.inspection}
        shelfName={shelfName}
        cameraName={cameraName}
        canDelete={canManage}
        onClose={selected.close}
      />
    </>
  );
}
