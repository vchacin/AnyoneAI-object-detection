"use client";

import { useCreateUser, useUpdateUser } from "@/hooks/queries/use-team";
import { useEditDialog } from "@/hooks/use-edit-dialog";
import type { StoreUser } from "@/lib/api/types";

export interface UserDraft {
  email: string;
  password: string;
  role: string;
  active: boolean;
}

const toDraft = (u: StoreUser | null): UserDraft => ({
  email: u?.email ?? "",
  password: "",
  role: u?.role ?? "employee",
  active: u?.is_active ?? true,
});

export function useUserManager(storeId: string) {
  const dialog = useEditDialog<StoreUser, UserDraft>(toDraft);
  const create = useCreateUser(storeId);
  const update = useUpdateUser(storeId);

  async function save() {
    const { email, password, role, active } = dialog.draft;
    try {
      if (dialog.item) {
        await update.mutateAsync({ id: dialog.item.id, role, is_active: active, ...(password ? { password } : {}) });
      } else {
        await create.mutateAsync({ email: email.trim(), password, role });
      }
      dialog.close();
    } catch {
      /* toast global */
    }
  }

  return { dialog, save, saving: create.isPending || update.isPending };
}
