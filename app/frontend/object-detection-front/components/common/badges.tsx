import { cn } from "@/lib/utils";
import type { AlertSeverity, AlertStatus } from "@/lib/api/types";

function Pill({ tone, children, className }: { tone: string; children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium whitespace-nowrap", className)}>
      <span className={cn("size-1.5 rounded-full", tone)} />
      {children}
    </span>
  );
}

const STATUS: Record<AlertStatus, { label: string; tone: string }> = {
  open: { label: "Abierta", tone: "bg-gap" },
  acknowledged: { label: "En atención", tone: "bg-info" },
  closed: { label: "Cerrada", tone: "bg-muted-foreground/50" },
};
const SEVERITY: Record<AlertSeverity, { label: string; cls: string }> = {
  low: { label: "Baja", cls: "text-muted-foreground" },
  medium: { label: "Media", cls: "text-gap-foreground" },
  high: { label: "Alta", cls: "text-destructive" },
};

export function AlertStatusPill({ status }: { status: AlertStatus }) {
  const s = STATUS[status] ?? { label: status, tone: "bg-muted-foreground" };
  return <Pill tone={s.tone}>{s.label}</Pill>;
}

export function SeverityTag({ severity }: { severity: AlertSeverity }) {
  const s = SEVERITY[severity] ?? { label: severity, cls: "" };
  return <span className={cn("text-xs font-semibold tracking-wide uppercase", s.cls)}>{s.label}</span>;
}

export function ActivePill({ active, labels = ["Activo", "Inactivo"] }: { active: boolean; labels?: [string, string] }) {
  return <Pill tone={active ? "bg-ok" : "bg-muted-foreground/50"}>{active ? labels[0] : labels[1]}</Pill>;
}

export function StatusPill({ status }: { status: string }) {
  return <ActivePill active={status === "active"} />;
}

export const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super admin",
  store_admin: "Admin de tienda",
  employee: "Empleado",
  viewer: "Solo lectura",
};
