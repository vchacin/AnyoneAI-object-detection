"use client";

import { ChevronsUpDown, Loader2, LogOut, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { ROLE_LABELS } from "@/components/common/badges";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useLogout } from "@/hooks/use-session";
import { useAuth } from "@/stores/auth-store";

export function UserMenu() {
  const user = useAuth((s) => s.user);
  const { resolvedTheme, setTheme } = useTheme();
  const logout = useLogout();
  if (!user) return null;

  const dark = resolvedTheme === "dark";

  return (
    <div className="flex items-center gap-1">
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <button className="flex min-w-0 flex-1 items-center gap-2.5 rounded-md px-2 py-2 text-left outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-ring" />
          }
        >
          <span className="grid size-7 shrink-0 place-items-center rounded-full bg-primary/15 text-xs font-semibold text-primary uppercase">
            {user.email[0]}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm leading-tight font-medium">{user.email}</span>
            <span className="block text-xs text-muted-foreground">{ROLE_LABELS[user.role] ?? user.role}</span>
          </span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" />
        </DropdownMenuTrigger>
        <DropdownMenuContent side="top" align="start" className="w-56">
          <DropdownMenuGroup>
            <DropdownMenuLabel className="truncate">{user.email}</DropdownMenuLabel>
          </DropdownMenuGroup>
          <DropdownMenuItem onClick={() => setTheme(dark ? "light" : "dark")}>
            {dark ? <Sun /> : <Moon />}
            Cambiar a tema {dark ? "claro" : "oscuro"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onClick={() => logout.mutate()}>
            <LogOut />
            Cerrar sesión
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Tooltip>
        <TooltipTrigger
          render={
            <Button variant="ghost" size="icon" aria-label="Cerrar sesión" disabled={logout.isPending} onClick={() => logout.mutate()} />
          }
        >
          {logout.isPending ? <Loader2 className="animate-spin" /> : <LogOut />}
        </TooltipTrigger>
        <TooltipContent side="top">Cerrar sesión</TooltipContent>
      </Tooltip>
    </div>
  );
}
