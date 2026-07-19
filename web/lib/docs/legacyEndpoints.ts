export type LegacyEndpoint = {
  path: string;
  summary: string;
  response: string;
};

/** Static docs for legacy `/api/*` adapters (from `legacy.py`). */
export const LEGACY_ENDPOINTS: LegacyEndpoint[] = [
  {
    path: "/api/addressbalance/{addr}",
    summary: "Address balance",
    response: '{"error":"ok","message":"<8dp>"} or invalid-address envelope',
  },
  {
    path: "/api/receivedbyaddress/{addr}",
    summary: "Total received by address",
    response: '{"error":"ok","message":"<8dp>"} or invalid-address envelope',
  },
  {
    path: "/api/sentbyaddress/{addr}",
    summary: "Total sent by address",
    response: '{"error":"ok","message":"<8dp>"} or invalid-address envelope',
  },
  {
    path: "/api/validateaddress/{addr}",
    summary: "Validate address via RPC",
    response: '{"error":"ok","message":"valid"} or invalid envelope',
  },
  {
    path: "/api/rawtx/{txid}",
    summary: "Raw transaction (RPC getrawtransaction verbosity 1)",
    response: "full RPC JSON object, or invalid-tx envelope",
  },
  {
    path: "/api/block/getbestblockhash",
    summary: "Tip block hash",
    response: 'bare JSON string "<hash>", or 404-style envelope',
  },
  {
    path: "/api/block/getblockcount",
    summary: "Tip height",
    response: '{"error":"ok","message":"<height>"}',
  },
  {
    path: "/api/block/{hash}",
    summary: "Block via RPC (getblock verbosity 2)",
    response: "full RPC JSON object, or invalid envelope",
  },
  {
    path: "/api/getsummary",
    summary: "Circulating supply (coinbase sum − fees)",
    response: '{"error":"ok","message":"<8dp supply>"}',
  },
  {
    path: "/api/totaltransactions",
    summary: "Indexed transaction count",
    response: '{"error":"ok","message":"<count>"}',
  },
  {
    path: "/api/confirmations/{height}",
    summary: "Confirmations for a height (tip − height + 1)",
    response: '{"error":"ok","message":"<n>"}',
  },
  {
    path: "/api/lastdifficulty",
    summary: "Tip block difficulty",
    response: '{"error":"ok","message":"<8dp>"}',
  },
];
