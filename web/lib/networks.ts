export const SECTIONS = [
  "blocks",
  "block",
  "tx",
  "address",
  "mweb",
  "mempool",
  "charts",
] as const;

export type Section = (typeof SECTIONS)[number];

export type EntityKind = "block" | "tx" | "address";

export type ParsedPath = {
  network: string;
  section: Section | null;
  id: string | null;
  isDefaultNetwork: boolean;
};

const KNOWN_NETWORKS = new Set(["mainnet", "testnet", "regtest"]);

function parseNetworksEnv(): string[] {
  const raw = process.env.NEXT_PUBLIC_NETWORKS ?? "regtest";
  const list = raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter((s) => KNOWN_NETWORKS.has(s));
  return list.length > 0 ? list : ["regtest"];
}

export const NETWORKS: readonly string[] = parseNetworksEnv();
export const DEFAULT_NETWORK: string = NETWORKS[0]!;

export function nonDefaultNetworks(): string[] {
  return NETWORKS.filter((n) => n !== DEFAULT_NETWORK);
}

export function isKnownNetwork(value: string): boolean {
  return NETWORKS.includes(value.toLowerCase());
}

/** Build a network-aware href. `path` is like `/blocks` or `/block/123`. */
export function networkHref(network: string, path: string = "/"): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (network === DEFAULT_NETWORK) {
    return normalized === "" ? "/" : normalized;
  }
  if (normalized === "/") {
    return `/${network}`;
  }
  return `/${network}${normalized}`;
}

export function entityHref(
  network: string,
  kind: EntityKind,
  id: string,
): string {
  return networkHref(network, `/${kind}/${encodeURIComponent(id)}`);
}

export function parsePathname(pathname: string): ParsedPath {
  const parts = pathname.split("/").filter(Boolean);

  let network = DEFAULT_NETWORK;
  let rest = parts;
  let isDefaultNetwork = true;

  if (parts.length > 0 && isKnownNetwork(parts[0]!)) {
    network = parts[0]!;
    rest = parts.slice(1);
    isDefaultNetwork = false;
  }

  const sectionRaw = rest[0] ?? null;
  const section =
    sectionRaw && (SECTIONS as readonly string[]).includes(sectionRaw)
      ? (sectionRaw as Section)
      : null;

  let id: string | null = null;
  if (section === "block" || section === "tx" || section === "address") {
    id = rest.length >= 2 ? decodeURIComponent(rest.slice(1).join("/")) : null;
  }

  return { network, section, id, isDefaultNetwork };
}

export function activeNetworkFromPathname(pathname: string): string {
  return parsePathname(pathname).network;
}
