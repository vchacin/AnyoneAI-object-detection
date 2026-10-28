"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useOpenAlertCount } from "@/hooks/queries/use-alerts";
import { useStoreContext } from "@/hooks/use-store-context";
import { cn } from "@/lib/utils";
import { NAV } from "./nav-config";

export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user, storeId } = useStoreContext();
  const { data: alertCount } = useOpenAlertCount(storeId);

  return (
    <nav className="flex-1 overflow-y-auto px-3 py-2">
      {NAV.map((group, i) => {
        const items = group.items.filter((it) => !it.roles || (user && it.roles.includes(user.role)));
        if (!items.length) return null;
        return (
          <div key={i} className={cn(i > 0 && "mt-5")}>
            {group.title && (
              <p className="mb-1 px-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                {group.title}
              </p>
            )}
            <ul className="grid gap-0.5">
              {items.map((it) => {
                const active = it.href === "/" ? pathname === "/" : pathname.startsWith(it.href);
                return (
                  <li key={it.href}>
                    <Link
                      href={it.href}
                      onClick={onNavigate}
                      className={cn(
                        "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                        active
                          ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                          : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                      )}
                    >
                      <it.icon className={cn("size-4", active && "text-primary")} />
                      {it.label}
                      {it.badge === "alerts" && alertCount ? (
                        <span className="tnum ml-auto rounded-full bg-gap px-1.5 text-[11px] font-semibold text-background">
                          {alertCount}
                        </span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
