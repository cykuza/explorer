"use client";

import { type FormEvent, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { ApiError, searchEntity } from "@/lib/api/client";
import {
  activeNetworkFromPathname,
  entityHref,
  networkHref,
} from "@/lib/networks";

const MWEB_ADDR_PREFIX = /^(cymweb1|tmweb)/i;

export function SearchBar() {
  const router = useRouter();
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      const hit = await searchEntity(network, q);
      router.push(entityHref(network, hit.type, hit.id));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        if (MWEB_ADDR_PREFIX.test(q)) {
          router.push(`${networkHref(network, "/mweb")}#address`);
          return;
        }
        setError("not found");
      } else if (err instanceof ApiError) {
        setError(err.detail || err.title);
      } else {
        setError("search failed");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="min-w-0 flex-1">
      <form
        onSubmit={onSubmit}
        className="flex h-9 items-stretch border border-surface-3 bg-surface-1"
        role="search"
      >
        <label htmlFor="explorer-search" className="sr-only">
          Search block, transaction, or address
        </label>
        <input
          id="explorer-search"
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (error) {
              setError(null);
            }
          }}
          placeholder="Block / tx / address"
          autoComplete="off"
          spellCheck={false}
          className="min-w-0 flex-1 border-0 bg-transparent px-3 font-mono text-sm leading-none text-text placeholder:text-text-mute focus:outline-none"
        />
        <button
          type="submit"
          disabled={pending || !query.trim()}
          className="inline-flex h-full shrink-0 items-center justify-center border-l border-surface-3 px-3 text-sm leading-none text-text-bright transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            backgroundImage: "linear-gradient(27deg, #3d3d3d, #252525)",
          }}
        >
          Search
        </button>
      </form>
      {error ? (
        <p className="mt-1 text-xs text-text-dim" role="status">
          {error}
        </p>
      ) : null}
    </div>
  );
}
