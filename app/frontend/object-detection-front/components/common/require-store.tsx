"use client";

import { Store } from "lucide-react";
import { EmptyState } from "@/components/common/states";
import { useStoreContext } from "@/hooks/use-store-context";

/** Renderiza hijos solo cuando hay una tienda en contexto. */
export function RequireStore({ children }: { children: (storeId: string) => React.ReactNode }) {
  const { storeId, isSuper } = useStoreContext();
  if (!storeId) {
    return (
      <EmptyState
        icon={Store}
        title="Selecciona una tienda"
        description={
          isSuper
            ? "Elige una tienda en el selector de la barra lateral para ver esta sección."
            : "Tu usuario no está asociado a ninguna tienda."
        }
      />
    );
  }
  return <>{children(storeId)}</>;
}
