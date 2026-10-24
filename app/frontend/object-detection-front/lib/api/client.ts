import { useAuth } from "@/stores/auth-store";

/** Next reescribe /backend/* -> {API_URL}/api/v1/* (ver next.config.ts). */
export const API_BASE = "/backend";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code: string = "HTTP_ERROR",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

export function qs(params?: Query): string {
  if (!params) return "";
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

function authHeaders(): Record<string, string> {
  const { accessToken, apiKey } = useAuth.getState();
  if (accessToken) return { Authorization: `Bearer ${accessToken}` };
  if (apiKey) return { "X-API-Key": apiKey };
  return {};
}

let refreshing: Promise<boolean> | null = null;

/** Renueva el access token. Una sola peticion en vuelo aunque fallen varias a la vez. */
function refreshAccessToken(): Promise<boolean> {
  refreshing ??= (async () => {
    const { refreshToken, setAccessToken, clear } = useAuth.getState();
    if (!refreshToken) return false;
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ refresh_token: refreshToken }),
      });
      if (!res.ok) throw new Error("refresh failed");
      const data = (await res.json()) as { access_token: string };
      setAccessToken(data.access_token);
      return true;
    } catch {
      clear();
      return false;
    } finally {
      setTimeout(() => (refreshing = null), 0);
    }
  })();
  return refreshing;
}

async function toError(res: Response): Promise<ApiError> {
  let message = `Error ${res.status}`;
  let code = "HTTP_ERROR";
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") message = body.detail;
    else if (Array.isArray(body?.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join(", ");
    if (typeof body?.code === "string") code = body.code;
  } catch {
    /* cuerpo no JSON */
  }
  return new ApiError(message, res.status, code);
}

interface RequestOptions {
  method?: string;
  query?: Query;
  json?: unknown;
  form?: Record<string, string>;
  body?: FormData;
  headers?: Record<string, string>;
  /** No adjunta credenciales ni intenta refrescar (login/refresh). */
  anonymous?: boolean;
}

async function rawRequest(path: string, opts: RequestOptions = {}, retried = false): Promise<Response> {
  const headers: Record<string, string> = { ...(opts.anonymous ? {} : authHeaders()), ...opts.headers };
  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  } else if (opts.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(opts.form);
  } else if (opts.body) {
    body = opts.body;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}${qs(opts.query)}`, { method: opts.method ?? "GET", headers, body });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor", 0, "NETWORK_ERROR");
  }

  if (res.status === 401 && !opts.anonymous && !retried && useAuth.getState().refreshToken) {
    if (await refreshAccessToken()) return rawRequest(path, opts, true);
  }
  if (!res.ok) throw await toError(res);
  return res;
}

export async function request<T>(path: string, opts?: RequestOptions): Promise<T> {
  const res = await rawRequest(path, opts);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function requestBlob(path: string, opts?: RequestOptions): Promise<Blob> {
  return (await rawRequest(path, opts)).blob();
}

export async function download(path: string, filename: string, query?: Query) {
  const blob = await requestBlob(path, { query });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
