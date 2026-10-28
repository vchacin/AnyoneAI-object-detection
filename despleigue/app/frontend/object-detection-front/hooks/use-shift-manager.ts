"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useDeleteShift, useSaveShift } from "@/hooks/queries/use-team";
import { useEditDialog } from "@/hooks/use-edit-dialog";
import type { Shift } from "@/lib/api/types";

export interface ShiftDraft {
  employee_id: string;
  weekday: string;
  start_time: string;
  end_time: string;
}

const toDraft = (s: Shift | null): ShiftDraft => ({
  employee_id: s?.employee_id ?? "",
  weekday: String(s?.weekday ?? 0),
  start_time: s?.start_time ?? "08:00",
  end_time: s?.end_time ?? "16:00",
});

export function useShiftManager(storeId: string) {
  const dialog = useEditDialog<Shift, ShiftDraft>(toDraft);
  const [removing, setRemoving] = useState<Shift | null>(null);
  const save = useSaveShift(storeId);
  const remove = useDeleteShift(storeId);

  async function submit() {
    const d = dialog.draft;
    if (!d.employee_id) return void toast.error("Choose an employee");
    try {
      await save.mutateAsync({
        id: dialog.item?.id,
        employee_id: d.employee_id,
        weekday: Number(d.weekday),
        start_time: d.start_time,
        end_time: d.end_time,
      });
      dialog.close();
    } catch {
      /* toast global */
    }
  }

  /** Cierra el dialogo de edicion y pide confirmacion para borrar ese shift. */
  function askRemove() {
    if (!dialog.item) return;
    setRemoving(dialog.item);
    dialog.close();
  }

  return {
    dialog,
    submit,
    saving: save.isPending,
    removing,
    cancelRemove: () => setRemoving(null),
    askRemove,
    confirmRemove: () => (removing ? remove.mutateAsync(removing.id) : Promise.resolve()),
  };
}
