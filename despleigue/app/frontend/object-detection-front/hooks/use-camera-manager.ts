"use client";

import { useState } from "react";
import { useCreateCamera, useRotateCameraToken, useUpdateCamera } from "@/hooks/queries/use-cameras";
import { useEditDialog } from "@/hooks/use-edit-dialog";
import type { Camera } from "@/lib/api/types";

export interface CameraDraft {
  name: string;
  location: string;
  shelf_id: string;
  active: boolean;
}

const toDraft = (c: Camera | null): CameraDraft => ({
  name: c?.name ?? "",
  location: c?.location ?? "",
  shelf_id: c?.shelf_id ?? "",
  active: c ? c.status === "active" : true,
});

/** Camera screen logic: create/edit, rotate token, and show the token once. */
export function useCameraManager(storeId: string) {
  const dialog = useEditDialog<Camera, CameraDraft>(toDraft);
  const [rotating, setRotating] = useState<Camera | null>(null);
  const [token, setToken] = useState<{ value: string; camera: string } | null>(null);

  const create = useCreateCamera(storeId);
  const update = useUpdateCamera(storeId);
  const rotate = useRotateCameraToken(storeId);

  async function save() {
    const { name, location, shelf_id, active } = dialog.draft;
    const body = { name: name.trim(), location: location.trim() || null, shelf_id: shelf_id || null };
    try {
      if (dialog.item) {
        await update.mutateAsync({ id: dialog.item.id, ...body, status: active ? "active" : "inactive" });
      } else {
        const created = await create.mutateAsync(body);
        setToken({ value: created.token, camera: created.name });
      }
      dialog.close();
    } catch {
      /* toast global */
    }
  }

  async function confirmRotate() {
    if (!rotating) return;
    const res = await rotate.mutateAsync(rotating.id);
    setToken({ value: res.token, camera: res.name });
  }

  return {
    dialog,
    save,
    saving: create.isPending || update.isPending,
    rotating,
    setRotating,
    confirmRotate,
    token,
    clearToken: () => setToken(null),
  };
}
