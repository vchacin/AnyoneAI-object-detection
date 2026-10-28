"use client";

import { Choice } from "@/components/common/choice";
import { useStoreQuery } from "@/hooks/queries/use-stores";
import { useContextStores, useStoreContext } from "@/hooks/use-store-context";
import { useAuth } from "@/stores/auth-store";

const LABEL = "mb-1 px-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase";

/** Super admin: store context selector. Others: their assigned store name. */
export function StoreSwitcher() {
  const { isSuper, storeId } = useStoreContext();
  const setActiveStore = useAuth((s) => s.setActiveStore);
  const stores = useContextStores();
  const own = useStoreQuery(!isSuper ? storeId : null);

  if (isSuper) {
    return (
      <div className="px-3">
        <p className={LABEL}>Store</p>
        <Choice
          size="sm"
          value={storeId ?? ""}
          onChange={(v) => setActiveStore(v || null)}
          emptyLabel="Global overview"
          options={(stores.data ?? []).map((s) => ({ value: s.id, label: s.name }))}
        />
      </div>
    );
  }
  return (
    <div className="px-4">
      <p className={LABEL}>Store</p>
      <p className="truncate text-sm font-medium">{own.data?.name ?? "—"}</p>
    </div>
  );
}
