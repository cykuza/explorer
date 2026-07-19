"use client";

import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

import { ComingSoon } from "@/components/ComingSoon";
import { HashLink } from "@/components/HashLink";
import { parsePathname, type EntityKind } from "@/lib/networks";

const TITLES: Record<EntityKind, string> = {
  block: "Block",
  tx: "Transaction",
  address: "Address",
};

type EntityShellProps = {
  kind: EntityKind;
};

function usePrettyPathname(): string {
  const nextPath = usePathname() ?? "/";
  // Prefer the browser URL (pretty /block/:id after nginx/dev rewrite).
  // usePathname() keeps this store in sync on client navigations.
  return useSyncExternalStore(
    () => () => {},
    () => window.location.pathname,
    () => nextPath,
  );
}

export function EntityShell({ kind }: EntityShellProps) {
  const path = usePrettyPathname();
  const id = parsePathname(path).id;

  return (
    <div className="space-y-3">
      <ComingSoon
        title={TITLES[kind]}
        detail="Entity details arrive in a later phase."
      />
      {id ? (
        <p className="text-sm text-text-mute">
          <span className="mr-2 text-text-dim">id</span>
          <HashLink value={id} />
        </p>
      ) : null}
    </div>
  );
}
