"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface ChoiceOption {
  value: string;
  label: string;
}

const NONE = "__none__";

interface ChoiceProps {
  value: string;
  onChange: (value: string) => void;
  options: ChoiceOption[];
  /** Si se define, agrega una opcion "vacia" (value "") con esta etiqueta. */
  emptyLabel?: string;
  placeholder?: string;
  size?: "sm" | "default";
  className?: string;
  disabled?: boolean;
  id?: string;
}

/** Select simple basado en lista de opciones; el valor vacio se mapea a "". */
export function Choice({ value, onChange, options, emptyLabel, placeholder, size, className, disabled, id }: ChoiceProps) {
  const items = emptyLabel !== undefined ? [{ value: NONE, label: emptyLabel }, ...options] : options;
  return (
    <Select
      value={value === "" && emptyLabel !== undefined ? NONE : value || null}
      onValueChange={(v) => onChange(v === NONE || v === null ? "" : (v as string))}
      items={items}
      disabled={disabled}
    >
      <SelectTrigger id={id} size={size} className={cn("w-full", className)}>
        <SelectValue>
          {(v: string | null) => items.find((o) => o.value === v)?.label ?? (
            <span className="text-muted-foreground">{placeholder ?? "Seleccionar…"}</span>
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent alignItemWithTrigger={false}>
        {items.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
