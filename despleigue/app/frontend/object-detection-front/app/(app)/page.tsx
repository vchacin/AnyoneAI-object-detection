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
        title="Overview"
        description={storeId ? "Store replenishment status and recent activity." : `Hello ${user?.email}. Platform overview.`}
        actions={
          <Link href="/analyze">
            <Button size="sm">
              <ScanSearch /> Analyze image
            </Button>
          </Link>
        }
      />
      {storeId ? (
        <StoreView key={storeId} storeId={storeId} />
      ) : isSuper ? (
        <GlobalView />
      ) : (
        <EmptyState title="No store assigned" description="Ask an administrator to assign your user to a store." />
      )}
    </>
  );
}
