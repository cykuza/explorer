/**
 * Ensure regtest has mined+synced blocks before Playwright runs.
 * Expects compose (`--profile api`) already up and env matching `.env.example`.
 */

import { execFileSync } from "node:child_process";
import path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const BACKEND = path.join(ROOT, "backend");
const RPC_URL = process.env.EXPLORER_RPC_URL ?? "http://127.0.0.1:18439";
const RPC_USER = process.env.EXPLORER_RPC_USER ?? "dev";
const RPC_PASSWORD = process.env.EXPLORER_RPC_PASSWORD ?? "dev";
const API_BASE = process.env.PLAYWRIGHT_API_BASE ?? "http://127.0.0.1:8080";
const MIN_HEIGHT = 5;

function rpcCall(url: string, method: string, params: unknown[] = []): unknown {
  const body = JSON.stringify({
    jsonrpc: "1.0",
    id: "e2e",
    method,
    params,
  });
  const out = execFileSync(
    "curl",
    [
      "-sS",
      "-u",
      `${RPC_USER}:${RPC_PASSWORD}`,
      "-H",
      "Content-Type: application/json",
      "--data-binary",
      body,
      url,
    ],
    { encoding: "utf8", maxBuffer: 10 * 1024 * 1024 },
  );
  const parsed = JSON.parse(out) as { result?: unknown; error?: unknown };
  if (parsed.error) {
    throw new Error(`RPC ${method} failed: ${JSON.stringify(parsed.error)}`);
  }
  return parsed.result;
}

function ensureWallet(name: string): void {
  try {
    const wallets = rpcCall(RPC_URL, "listwallets") as string[];
    if (wallets.includes(name)) {
      return;
    }
  } catch {
    // continue
  }
  try {
    rpcCall(RPC_URL, "loadwallet", [name]);
    return;
  } catch {
    // create
  }
  try {
    rpcCall(RPC_URL, "createwallet", [name]);
  } catch (err) {
    const msg = String(err);
    if (!/already/i.test(msg)) {
      try {
        rpcCall(RPC_URL, "loadwallet", [name]);
      } catch {
        throw err;
      }
    }
  }
}

function mineBlocks(n: number): void {
  ensureWallet("testwallet");
  const walletUrl = `${RPC_URL.replace(/\/$/, "")}/wallet/testwallet`;
  const address = rpcCall(walletUrl, "getnewaddress") as string;
  let remaining = n;
  while (remaining > 0) {
    const batch = Math.min(25, remaining);
    rpcCall(walletUrl, "generatetoaddress", [batch, address]);
    remaining -= batch;
  }
}

async function waitForTip(minHeight: number, timeoutMs = 120_000): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/regtest/tip`);
      if (res.ok) {
        const tip = (await res.json()) as { height: number };
        if (tip.height >= minHeight) {
          return;
        }
      }
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`Timed out waiting for tip height >= ${minHeight}`);
}

export default async function globalSetup(): Promise<void> {
  if (process.env.PLAYWRIGHT_SKIP_FIXTURE === "1") {
    await waitForTip(1);
    return;
  }

  console.log("[e2e] migrating database…");
  execFileSync("uv", ["run", "alembic", "upgrade", "head"], {
    cwd: BACKEND,
    stdio: "inherit",
    env: process.env,
  });

  console.log(`[e2e] mining ${MIN_HEIGHT} blocks…`);
  mineBlocks(MIN_HEIGHT);

  console.log("[e2e] syncing index…");
  execFileSync("uv", ["run", "explorer", "sync", "--once"], {
    cwd: BACKEND,
    stdio: "inherit",
    env: process.env,
  });

  console.log("[e2e] waiting for API tip…");
  await waitForTip(MIN_HEIGHT);
  console.log("[e2e] fixture ready");
}
