"use client";

import { ScanSearch } from "lucide-react";
import Link from "next/link";
import { GlobalView } from "@/components/dashboard/global-view";
import { StoreView } from "@/components/dashboard/store-view";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { useStoreContext } from "@/hooks/use-store-context";

export default function OverviewPage() {
  const { storeId, isSuper, user } = useStoreContext();

  return (
    <>
      <PageHeader
        title="Resumen"
        description={storeId ? "Estado de reposición y actividad reciente de la tienda." : `Hola ${user?.email}. Vista global de la plataforma.`}
        actions={
          <Link href="/analyze">
            <Button size="sm">
              <ScanSearch /> Analizar imagen
            </Button>
          </Link>
        }
      />
      {storeId ? (
        <StoreView key={storeId} storeId={storeId} />
      ) : isSuper ? (
        <GlobalView />
      ) : (
        <EmptyState title="Sin tienda asignada" description="Pide a un administrador que asocie tu usuario a una tienda." />
      )}
    </>
  );
}
