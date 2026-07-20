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
      <span className="inline-flex h-9 items-center rounded-sm border border-surface-3 px-3 text-sm leading-none text-text-dim">
        {current}
      </span>
    );
  }

  return (
    <div className="relative flex h-9 items-center">
      <label htmlFor="network-switcher" className="sr-only">
        Network
      </label>
      <select
        id="network-switcher"
        value={current}
        onChange={(e) => switchTo(e.target.value)}
        className="h-9 appearance-none border border-surface-3 bg-surface-1 py-0 pl-3 pr-8 text-sm leading-none text-text focus:outline-none"
      >
        {NETWORKS.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
      <span
        className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-text-dim"
        aria-hidden="true"
      >
        <svg width="10" height="6" viewBox="0 0 10 6" aria-hidden="true">
          <path
            d="M1 1l4 4 4-4"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
          />
        </svg>
      </span>
    </div>
  );
}
