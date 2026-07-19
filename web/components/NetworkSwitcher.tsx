"use client";

import { usePathname, useRouter } from "next/navigation";

import {
  NETWORKS,
  activeNetworkFromPathname,
  networkHref,
  parsePathname,
} from "@/lib/networks";

export function NetworkSwitcher() {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const current = activeNetworkFromPathname(pathname);
  const parsed = parsePathname(pathname);

  function switchTo(next: string) {
    if (next === current) {
      return;
    }
    const sectionPath =
      parsed.section === null
        ? "/"
        : parsed.id
          ? `/${parsed.section}/${parsed.id}`
          : `/${parsed.section}`;
    router.push(networkHref(next, sectionPath));
  }

  if (NETWORKS.length <= 1) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-text-dim">
        <span className="rounded-sm border border-surface-3 px-1.5 py-0.5 text-xs text-text-dim">
          {current}
        </span>
      </span>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="network-switcher" className="sr-only">
        Network
      </label>
      <select
        id="network-switcher"
        value={current}
        onChange={(e) => switchTo(e.target.value)}
        className="border border-surface-3 bg-surface-1 px-2 py-1.5 text-xs text-text focus:outline-none"
      >
        {NETWORKS.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </div>
  );
}
