"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/stores/auth-store";
import { usePrefs } from "@/stores/prefs-store";

/**
 * Los stores usan skipHydration para que el HTML del servidor y el primer
 * render del cliente coincidan. Aqui se leen de localStorage una sola vez.
 */
export function useHydrated(): boolean {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    void Promise.all([useAuth.persist.rehydrate(), usePrefs.persist.rehydrate()]).then(() => setReady(true));
  }, []);
  return ready;
}
