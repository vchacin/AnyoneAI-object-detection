"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { authService } from "@/services/auth.service";
import { useAuth } from "@/stores/auth-store";
import { useHydrated } from "./use-hydrated";

export const selectAuthed = (s: { accessToken: string | null; apiKey: string | null }) =>
  Boolean(s.accessToken || s.apiKey);

/** Login por credenciales o por API key; deja el perfil cargado en el store. */
export function useLogin() {
  const router = useRouter();
  return useMutation({
    mutationFn: async (input: { mode: "password"; email: string; password: string } | { mode: "key"; key: string }) => {
      const { setSession, setApiKey, setUser, clear } = useAuth.getState();
      if (input.mode === "password") {
        const t = await authService.login(input.email, input.password);
        setSession({ accessToken: t.access_token, refreshToken: t.refresh_token });
      } else {
        setApiKey(input.key);
      }
      try {
        setUser(await authService.me());
      } catch (e) {
        clear();
        throw e;
      }
    },
    onSuccess: () => router.replace("/"),
  });
}

export function useLogout() {
  const router = useRouter();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { refreshToken } = useAuth.getState();
      try {
        if (refreshToken) await authService.logout(refreshToken);
      } catch {
        /* si falla igual cerramos la sesion local */
      }
    },
    meta: { silent: true },
    onSettled: () => {
      useAuth.getState().clear();
      qc.clear();
      router.replace("/login");
    },
  });
}

/** Guarda de rutas privadas: redirige a /login y revalida el perfil al cargar. */
export function useRequireSession() {
  const router = useRouter();
  const ready = useHydrated();
  const authed = useAuth(selectAuthed);
  const user = useAuth((s) => s.user);

  useEffect(() => {
    if (ready && !authed) router.replace("/login");
  }, [ready, authed, router]);

  useEffect(() => {
    if (!ready || !authed) return;
    authService
      .me()
      .then((u) => useAuth.getState().setUser(u))
      .catch(() => useAuth.getState().clear());
  }, [ready, authed]);

  return { loading: !ready || !authed || !user };
}

/** On /login: redirect to the home page if a session already exists. */
export function useRedirectIfAuthed() {
  const router = useRouter();
  const ready = useHydrated();
  const authed = useAuth(selectAuthed);
  useEffect(() => {
    if (ready && authed) router.replace("/");
  }, [ready, authed, router]);
  return ready;
}
