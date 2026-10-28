"use client";

import { Store } from "lucide-react";
import { EmptyState } from "@/components/common/states";
import { useStoreContext } from "@/hooks/use-store-context";

/** Renders children only when a store is in context. */
export function RequireStore({ children }: { children: (storeId: string) => React.ReactNode }) {
  const { storeId, isSuper } = useStoreContext();
  if (!storeId) {
    return (
      <EmptyState
        icon={Store}
        title="Select a store"
        description={
          isSuper
            ? "Choose a store from the sidebar selector to view this section."
            : "Your user is not assigned to a store."
        }
      />
    );
  }
  return <>{children(storeId)}</>;
}
