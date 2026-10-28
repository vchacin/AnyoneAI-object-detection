import { MutationCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "@/lib/api/client";

declare module "@tanstack/react-query" {
  interface Register {
    mutationMeta: {
      /** Mensaje de exito que se muestra como toast. */
      success?: string;
      /** Si es true, el error no se muestra automaticamente (lo maneja el llamador). */
      silent?: boolean;
    };
  }
}

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
      },
    },
    mutationCache: new MutationCache({
      onSuccess: (_data, _vars, _ctx, mutation) => {
        const message = mutation.meta?.success;
        if (message) toast.success(message);
      },
      onError: (error, _vars, _ctx, mutation) => {
        if (!mutation.meta?.silent) toast.error(error instanceof Error ? error.message : "Unexpected error");
      },
    }),
  });
}
