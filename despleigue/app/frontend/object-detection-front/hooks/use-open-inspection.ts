"use client";

import { useEffect, useState } from "react";
import { useInspection } from "@/hooks/queries/use-inspections";

/** Inspection open in the side panel; supports the ?open=<id> link. */
export function useOpenInspection() {
  const [openId, setOpenId] = useState<string | null>(null);
  const query = useInspection(openId);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("open");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (id) setOpenId(id);
  }, []);

  return {
    inspection: openId ? (query.data ?? null) : null,
    open: setOpenId,
    close: () => {
      setOpenId(null);
      if (window.location.search) window.history.replaceState(null, "", window.location.pathname);
    },
  };
}
