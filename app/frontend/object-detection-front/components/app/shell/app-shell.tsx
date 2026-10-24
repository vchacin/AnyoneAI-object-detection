"use client";

import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { BrandName } from "@/components/app/brand";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { NavLinks } from "./nav-links";
import { StoreSwitcher } from "./store-switcher";
import { UserMenu } from "./user-menu";

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col bg-sidebar">
      <div className="px-4 pt-5 pb-4">
        <BrandName />
      </div>
      <StoreSwitcher />
      <NavLinks onNavigate={onNavigate} />
      <div className="border-t p-2">
        <UserMenu />
      </div>
    </div>
  );
}

function MobileNav() {
  const pathname = usePathname();
  const [state, setState] = useState({ open: false, path: pathname });
  // Cierra el menu al navegar sin usar un efecto.
  const open = state.open && state.path === pathname;

  return (
    <>
      <header className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b bg-background/80 px-3 backdrop-blur lg:hidden">
        <Button variant="ghost" size="icon" onClick={() => setState({ open: true, path: pathname })} aria-label="Abrir menú">
          <Menu />
        </Button>
        <BrandName className="text-sm" />
      </header>
      <Sheet open={open} onOpenChange={(o) => setState({ open: o, path: pathname })}>
        <SheetContent side="left" className="w-64 p-0 sm:max-w-64" showCloseButton={false}>
          <SheetTitle className="sr-only">Navegación</SheetTitle>
          <SidebarBody />
        </SheetContent>
      </Sheet>
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-svh lg:pl-60">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 border-r lg:block">
        <SidebarBody />
      </aside>
      <MobileNav />
      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-8 sm:py-8">{children}</main>
    </div>
  );
}
