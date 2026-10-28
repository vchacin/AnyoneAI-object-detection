"use client";

import { Loader2 } from "lucide-react";
import { AppShell } from "@/components/app/shell/app-shell";
import { useRequireSession } from "@/hooks/use-session";

/** Protege las rutas privadas y monta el shell de navegacion. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { loading } = useRequireSession();

  if (loading) {
    return (
      <div className="grid min-h-svh place-items-center">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  return <AppShell>{children}</AppShell>;
}
