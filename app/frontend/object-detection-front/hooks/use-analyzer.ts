"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import type { ViewerBox } from "@/components/app/detection-viewer";
import { useStoreContext } from "@/hooks/use-store-context";
import { usePredict } from "@/hooks/queries/use-system";
import { usePrefs } from "@/stores/prefs-store";

/** Estado y acciones de la pantalla de analisis de imagen. */
export function useAnalyzer() {
  const prefs = usePrefs();
  const predict = usePredict();
  const { storeId } = useStoreContext();

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);
  const [cameraId, setCameraId] = useState("");
  const [shelfId, setShelfId] = useState("");

  const { reset: resetResult } = predict;

  const swapPreview = useCallback((next: string | null) => {
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old);
      return next;
    });
  }, []);

  const pick = useCallback(
    (f: File | undefined) => {
      if (!f) return;
      if (!/^image\/(jpeg|png)$/.test(f.type)) {
        toast.error("Solo se aceptan imágenes JPG o PNG");
        return;
      }
      const url = URL.createObjectURL(f);
      const probe = new Image();
      probe.onload = () => setDims({ w: probe.naturalWidth, h: probe.naturalHeight });
      probe.src = url;
      setFile(f);
      swapPreview(url);
      resetResult();
    },
    [swapPreview, resetResult],
  );

  const clear = useCallback(() => {
    setFile(null);
    setDims(null);
    swapPreview(null);
    resetResult();
  }, [swapPreview, resetResult]);

  // Pegar imagen desde el portapapeles.
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => pick(e.clipboardData?.files[0]);
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [pick]);

  const analyze = () => {
    if (!file) return;
    predict.mutate({
      file,
      model: prefs.model,
      persist: prefs.persist,
      conf: prefs.conf,
      camera_id: cameraId,
      shelf_id: shelfId,
      store_id: storeId,
    });
  };

  /** Al elegir una camara con estante vinculado, preselecciona ese estante. */
  const selectCamera = (id: string, shelfOfCamera?: string | null) => {
    setCameraId(id);
    if (shelfOfCamera) setShelfId(shelfOfCamera);
  };

  const result = predict.data ?? null;
  const boxes = useMemo<ViewerBox[]>(
    () =>
      (result?.detections ?? []).map((d) => ({
        box: d.box,
        kind: d.class === "missing" ? "missing" : "object",
        confidence: d.confidence,
      })),
    [result],
  );

  return {
    file,
    preview,
    size: result ? { w: result.width, h: result.height } : (dims ?? { w: 1600, h: 900 }),
    result,
    boxes,
    isAnalyzing: predict.isPending,
    cameraId,
    shelfId,
    setShelfId,
    selectCamera,
    pick,
    clear,
    analyze,
  };
}
