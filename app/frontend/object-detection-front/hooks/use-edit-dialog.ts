"use client";

import { useState } from "react";

/**
 * Estado de un dialogo de alta/edicion: que elemento se edita ("new" = alta)
 * y el borrador del formulario. `toDraft(null)` devuelve el borrador vacio.
 */
export function useEditDialog<Item, Draft>(toDraft: (item: Item | null) => Draft) {
  const [target, setTarget] = useState<Item | "new" | null>(null);
  const [draft, setDraft] = useState<Draft>(() => toDraft(null));

  return {
    target,
    item: target === "new" ? null : target,
    isOpen: target !== null,
    isNew: target === "new",
    draft,
    patch: (partial: Partial<Draft>) => setDraft((d) => ({ ...d, ...partial })),
    open: (t: Item | "new", overrides?: Partial<Draft>) => {
      setDraft({ ...toDraft(t === "new" ? null : t), ...overrides });
      setTarget(t);
    },
    close: () => setTarget(null),
  };
}
