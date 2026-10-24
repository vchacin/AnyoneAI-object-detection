"use client";

import { CamerasPanel } from "@/components/cameras/cameras-panel";
import { PageHeader } from "@/components/common/page-header";
import { RequireStore } from "@/components/common/require-store";

export default function CamerasPage() {
  return (
    <>
      <PageHeader title="Cámaras" description="Dispositivos que envían imágenes de estantes. Cada cámara se autentica con su propio token." />
      <RequireStore>{(storeId) => <CamerasPanel key={storeId} storeId={storeId} />}</RequireStore>
    </>
  );
}
