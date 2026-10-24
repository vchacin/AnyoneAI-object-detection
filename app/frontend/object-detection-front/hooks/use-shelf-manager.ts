"use client";

import { useCreateShelf, useUpdateShelf } from "@/hooks/queries/use-shelves";
import { useEditDialog } from "@/hooks/use-edit-dialog";
import type { Shelf } from "@/lib/api/types";

export interface ShelfDraft {
  name: string;
  zone: string;
  gap_threshold: string;
}

const toDraft = (s: Shelf | null): ShelfDraft => ({
  name: s?.name ?? "",
  zone: s?.zone ?? "",
  gap_threshold: String(s?.gap_threshold ?? 0),
});

export function useShelfManager(storeId: string) {
  const dialog = useEditDialog<Shelf, ShelfDraft>(toDraft);
  const create = useCreateShelf(storeId);
  const update = useUpdateShelf(storeId);

  async function save() {
    const { name, zone, gap_threshold } = dialog.draft;
    const body = {
      name: name.trim(),
      zone: zone.trim() || null,
      gap_threshold: Math.max(0, Number.parseInt(gap_threshold, 10) || 0),
    };
    try {
      if (dialog.item) await update.mutateAsync({ id: dialog.item.id, ...body });
      else await create.mutateAsync(body);
      dialog.close();
    } catch {
      /* toast global */
    }
  }

  return { dialog, save, saving: create.isPending || update.isPending };
}
