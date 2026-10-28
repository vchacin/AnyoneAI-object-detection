import { request } from "@/lib/api/client";
import type { TokenPair, User } from "@/lib/api/types";

export const authService = {
  login: (email: string, password: string) =>
    request<TokenPair>("/auth/login", { method: "POST", form: { email, password }, anonymous: true }),
  me: () => request<User>("/auth/me"),
  logout: (refresh_token: string) =>
    request<{ ok: boolean }>("/auth/logout", { method: "POST", form: { refresh_token } }),
};
