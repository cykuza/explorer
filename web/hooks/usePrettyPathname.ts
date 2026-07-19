"use client";

import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

import { parsePathname, type EntityKind } from "@/lib/networks";

/**
 * Prefer the browser URL (pretty `/block/:id` after nginx/dev rewrite).
 * `usePathname()` keeps this store in sync on client navigations.
 */
export function usePrettyPathname(): string {
  const nextPath = usePathname() ?? "/";
  return useSyncExternalStore(
    () => () => {},
    () => window.location.pathname,
    () => nextPath,
  );
}

export function useEntityId(kind: EntityKind): string | null {
  const path = usePrettyPathname();
  const parsed = parsePathname(path);
  if (parsed.section !== kind) {
    return null;
  }
  return parsed.id;
}
