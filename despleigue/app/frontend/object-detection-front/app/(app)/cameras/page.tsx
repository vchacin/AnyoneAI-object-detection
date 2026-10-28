"use client";

import { CamerasPanel } from "@/components/cameras/cameras-panel";
import { PageHeader } from "@/components/common/page-header";
import { RequireStore } from "@/components/common/require-store";

export default function CamerasPage() {
  return (
    <>
      <PageHeader title="Cameras" description="Devices that send shelf images. Each camera authenticates with its own token." />
      <RequireStore>{(storeId) => <CamerasPanel key={storeId} storeId={storeId} />}</RequireStore>
    </>
  );
}
