import { Activity, Bell, Camera, Gauge, History, Rows3, ScanSearch, Settings2, Store, Users } from "lucide-react";
import type { Role } from "@/lib/api/types";

export interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: Role[];
  badge?: "alerts";
}

export interface NavGroup {
  title?: string;
  items: NavItem[];
}

export const NAV: NavGroup[] = [
  {
    items: [
      { href: "/", label: "Resumen", icon: Gauge },
      { href: "/analyze", label: "Analizar imagen", icon: ScanSearch },
      { href: "/inspections", label: "Inspecciones", icon: History },
      { href: "/alerts", label: "Alertas", icon: Bell, badge: "alerts" },
    ],
  },
  {
    title: "Tienda",
    items: [
      { href: "/cameras", label: "Cámaras", icon: Camera },
      { href: "/shelves", label: "Estantes", icon: Rows3 },
      { href: "/team", label: "Equipo", icon: Users },
      { href: "/settings", label: "Ajustes", icon: Settings2 },
    ],
  },
  {
    title: "Plataforma",
    items: [
      { href: "/stores", label: "Tiendas", icon: Store, roles: ["super_admin"] },
      { href: "/system", label: "Sistema y modelos", icon: Activity },
    ],
  },
];
