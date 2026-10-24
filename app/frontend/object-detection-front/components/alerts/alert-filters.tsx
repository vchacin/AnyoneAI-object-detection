"use client";

import { Choice } from "@/components/common/choice";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export const ALERT_STATUSES = [
  { value: "open", label: "Abiertas" },
  { value: "acknowledged", label: "En atención" },
  { value: "closed", label: "Cerradas" },
  { value: "all", label: "Todas" },
];

interface Props {
  status: string;
  severity: string;
  onStatus: (v: string) => void;
  onSeverity: (v: string) => void;
}

export function AlertFilters({ status, severity, onStatus, onSeverity }: Props) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <Tabs value={status} onValueChange={(v) => onStatus(v as string)}>
        <TabsList>
          {ALERT_STATUSES.map((s) => (
            <TabsTrigger key={s.value} value={s.value}>{s.label}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="w-40">
        <Choice
          size="sm"
          value={severity}
          onChange={onSeverity}
          emptyLabel="Toda severidad"
          options={[
            { value: "high", label: "Alta" },
            { value: "medium", label: "Media" },
            { value: "low", label: "Baja" },
          ]}
        />
      </div>
    </div>
  );
}
