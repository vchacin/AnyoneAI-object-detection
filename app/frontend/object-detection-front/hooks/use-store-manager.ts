"use client";

import { useCreateStore, useUpdateStore } from "@/hooks/queries/use-stores";
import { useEditDialog } from "@/hooks/use-edit-dialog";
import type { Store } from "@/lib/api/types";

export interface StoreDraft {
  name: string;
  address: string;
  admin_email: string;
  admin_password: string;
  status: string;
}

const toDraft = (s: Store | null): StoreDraft => ({
  name: s?.name ?? "",
  address: s?.address ?? "",
  admin_email: "",
  admin_password: "",
  status: s?.status ?? "active",
});

export function useStoreManager() {
  const dialog = useEditDialog<Store, StoreDraft>(toDraft);
  const create = useCreateStore();
  const update = useUpdateStore();

  async function save() {
    const d = dialog.draft;
    const common = { name: d.name.trim(), address: d.address.trim() || null };
    try {
      if (dialog.item) {
        await update.mutateAsync({ id: dialog.item.id, ...common, status: d.status });
      } else {
        const withAdmin = d.admin_email.trim() && d.admin_password;
        await create.mutateAsync({
          ...common,
          admin_email: withAdmin ? d.admin_email.trim() : null,
          admin_password: withAdmin ? d.admin_password : null,
        });
      }
      dialog.close();
    } catch {
      /* toast global */
    }
  }

  return { dialog, save, saving: create.isPending || update.isPending };
}
