import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/lib/api/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  /** Alternativa a JWT: cabecera X-API-Key (opera como super_admin). */
  apiKey: string | null;
  user: User | null;
  /** Tienda en contexto. Para super_admin la elige el usuario; el resto usa la suya. */
  activeStoreId: string | null;

  setSession: (s: { accessToken: string; refreshToken: string }) => void;
  setAccessToken: (token: string) => void;
  setApiKey: (key: string) => void;
  setUser: (user: User) => void;
  setActiveStore: (id: string | null) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      apiKey: null,
      user: null,
      activeStoreId: null,

      setSession: ({ accessToken, refreshToken }) =>
        set({ accessToken, refreshToken, apiKey: null }),
      setAccessToken: (accessToken) => set({ accessToken }),
      setApiKey: (apiKey) => set({ apiKey, accessToken: null, refreshToken: null }),
      setUser: (user) =>
        set((s) => ({
          user,
          activeStoreId: user.role === "super_admin" ? s.activeStoreId : user.store_id,
        })),
      setActiveStore: (activeStoreId) => set({ activeStoreId }),
      clear: () =>
        set({ accessToken: null, refreshToken: null, apiKey: null, user: null, activeStoreId: null }),
    }),
    {
      name: "shelfvision.auth",
      skipHydration: true,
    },
  ),
);

export const isAuthenticated = (s: AuthState) => Boolean(s.accessToken || s.apiKey);
