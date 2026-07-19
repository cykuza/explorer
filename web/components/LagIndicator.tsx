"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { fetchHealth, type NetworkHealth } from "@/lib/api/client";
import { activeNetworkFromPathname } from "@/lib/networks";

const POLL_MS = 30_000;

type LagState =
  | { kind: "loading" }
  | { kind: "ok"; health: NetworkHealth }
  | { kind: "lag"; health: NetworkHealth }
  | { kind: "unknown"; reason: string };

export function LagIndicator() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  const [state, setState] = useState<LagState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const health = await fetchHealth();
        if (cancelled) {
          return;
        }
        const entry = health.networks[network];
        if (!entry) {
          setState({ kind: "unknown", reason: `no health for ${network}` });
          return;
        }
        if (entry.lag === 0) {
          setState({ kind: "ok", health: entry });
        } else {
          setState({ kind: "lag", health: entry });
        }
      } catch {
        if (!cancelled) {
          setState({ kind: "unknown", reason: "health unreachable" });
        }
      }
    }

    void poll();
    const id = window.setInterval(() => void poll(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [network]);

  const ok = state.kind === "ok";
  const label =
    state.kind === "ok"
      ? `Node in sync (lag 0)`
      : state.kind === "lag"
        ? `Indexer lag ${state.health.lag} (db ${state.health.db_height}, node ${state.health.node_height})`
        : state.kind === "unknown"
          ? state.reason
          : "Checking node…";

  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs text-text-dim"
      title={label}
      aria-label={label}
    >
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          ok ? "bg-text-bright" : "bg-text-dim"
        }`}
        aria-hidden="true"
      />
      <span className="hidden sm:inline">{ok ? "sync" : "lag"}</span>
    </span>
  );
}
