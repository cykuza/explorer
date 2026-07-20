/** Canonical public origin for absolute metadata URLs (OG, canonical, JSON-LD). */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://cyberyen.work"
).replace(/\/$/, "");

export const SITE_NAME = "Cyberyen Explorer";

export const SITE_DESCRIPTION =
  "Browse Cyberyen blocks, transactions, addresses, mempool, and MWEB activity.";
