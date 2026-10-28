"use client";

import { Download, Trash2 } from "lucide-react";
import { useState } from "react";
import { ConfirmDialog } from "@/components/common/form";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useDeleteInspection, useExportInspection } from "@/hooks/queries/use-inspections";
import type { Inspection } from "@/lib/api/types";
import { formatFullDate } from "@/lib/format";
import { InspectionDetails } from "./inspection-details";
import { InspectionImage } from "./inspection-image";

interface Props {
  inspection: Inspection | null;
  shelfName: (id: string | null) => string | undefined;
  cameraName: (id: string | null) => string | undefined;
  canDelete: boolean;
  onClose: () => void;
}

export function InspectionSheet({ inspection, shelfName, cameraName, canDelete, onClose }: Props) {
  const [confirming, setConfirming] = useState(false);
  const remove = useDeleteInspection();
  const exportOne = useExportInspection();

  return (
    <>
      <Sheet open={!!inspection} onOpenChange={(o) => !o && onClose()}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-2xl">
          {inspection && (
            <>
              <SheetHeader className="border-b pb-4">
                <SheetTitle>Inspection · {formatFullDate(inspection.created_at)}</SheetTitle>
                <SheetDescription className="font-mono text-xs">{inspection.id}</SheetDescription>
              </SheetHeader>
              <div className="grid gap-6 px-4 pb-6">
                <InspectionImage key={inspection.id} inspection={inspection} />
                <InspectionDetails
                  inspection={inspection}
                  shelfName={shelfName(inspection.shelf_id)}
                  cameraName={cameraName(inspection.camera_id)}
                />
                <div className="flex gap-2 border-t pt-4">
                  <Button variant="outline" size="sm" disabled={exportOne.isPending} onClick={() => exportOne.mutate(inspection.id)}>
                    <Download /> Export JSON
                  </Button>
                  {canDelete && (
                    <Button variant="destructive" size="sm" className="ml-auto" onClick={() => setConfirming(true)}>
                      <Trash2 /> Delete
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Delete inspection?"
        description="This record and its detections will be deleted. This action cannot be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={async () => {
          await remove.mutateAsync(inspection!.id);
          onClose();
        }}
      />
    </>
  );
}
