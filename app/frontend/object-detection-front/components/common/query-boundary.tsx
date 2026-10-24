"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { ErrorState, RowsSkeleton } from "@/components/common/states";

interface QueryBoundaryProps<T> {
  query: Pick<UseQueryResult<T>, "data" | "error" | "isPending" | "refetch">;
  children: (data: T) => React.ReactNode;
  skeleton?: React.ReactNode;
  /** Si devuelve true se muestra `empty` en lugar de `children`. */
  isEmpty?: (data: T) => boolean;
  empty?: React.ReactNode;
}

/** Resuelve los tres estados de una query: cargando, error y vacio. */
export function QueryBoundary<T>({ query, children, skeleton, isEmpty, empty }: QueryBoundaryProps<T>) {
  if (query.error && query.data === undefined) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  if (query.isPending || query.data === undefined) return <>{skeleton ?? <RowsSkeleton />}</>;
  if (isEmpty?.(query.data)) return <>{empty}</>;
  return <>{children(query.data)}</>;
}
