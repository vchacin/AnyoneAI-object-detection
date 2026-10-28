"use client";

import type { Rolee } from "@/lib/api/types";
import { useAuth } from "@/stores/auth-store";
import { useStoresQuery } from "./queries/use-stores";

const WRITE_ROLES: Rolee[] = ["super_admin", "store_admin"];

/** Store activa + permisos derivados del rol. */
export function useStoreContext() {
  const user = useAuth((s) => s.user);
  const storeId = useAuth((s) => s.activeStoreId);

  return {
    user,
    storeId,
    isSuper: user?.role === "super_admin",
    canManage: user ? WRITE_ROLES.includes(user.role) : false,
    canAck: user ? user.role !== "viewer" : false,
  };
}

/** Store list for the context selector (super admins only). */
export function useContextStores() {
  const { isSuper } = useStoreContext();
  return useStoresQuery(isSuper);
}
