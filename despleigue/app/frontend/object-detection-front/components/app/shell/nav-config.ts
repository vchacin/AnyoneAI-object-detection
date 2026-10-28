import { Activity, Bell, Camera, Gauge, History, Presentation, Rows3, ScanSearch, Settings2, Store, Users } from "lucide-react";
import type { Rolee } from "@/lib/api/types";

export interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: Rolee[];
  badge?: "alerts";
}

export interface NavGroup {
  title?: string;
  items: NavItem[];
}

export const NAV: NavGroup[] = [
  {
    items: [
      { href: "/", label: "Overview", icon: Gauge },
      { href: "/demo", label: "Demo pitch", icon: Presentation },
      { href: "/analyze", label: "Analyze image", icon: ScanSearch },
      { href: "/inspections", label: "Inspections", icon: History },
      { href: "/alerts", label: "Alerts", icon: Bell, badge: "alerts" },
    ],
  },
  {
    title: "Store",
    items: [
      { href: "/cameras", label: "Cameras", icon: Camera },
      { href: "/shelves", label: "Shelves", icon: Rows3 },
      { href: "/team", label: "Team", icon: Users },
      { href: "/settings", label: "Settings", icon: Settings2 },
    ],
  },
  {
    title: "Platform",
    items: [
      { href: "/stores", label: "Stores", icon: Store, roles: ["super_admin"] },
      { href: "/system", label: "System and models", icon: Activity },
    ],
  },
];
