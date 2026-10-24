"use client";

import { useMemo, useState } from "react";
import { dayEnd, dayStart } from "@/lib/format";

export const INSPECTIONS_PAGE_SIZE = 25;

/** Filtros de la lista de inspecciones; cambiar cualquiera vuelve a la pagina 1. */
export function useInspectionFilters(storeId: string | null) {
  const [cameraId, setCameraId] = useState("");
  const [shelfId, setShelfId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(0);

  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(0);
  };

  const filters = useMemo(
    () => ({ store_id: storeId, camera_id: cameraId, shelf_id: shelfId, date_from: dayStart(from), date_to: dayEnd(to) }),
    [storeId, cameraId, shelfId, from, to],
  );

  return {
    filters,
    page,
    setPage,
    values: { cameraId, shelfId, from, to },
    setCameraId: reset(setCameraId),
    setShelfId: reset(setShelfId),
    setFrom: reset(setFrom),
    setTo: reset(setTo),
  };
}
