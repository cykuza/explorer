/**
 * Thin typed fetch wrapper for the explorer API.
 * OpenAPI types live in `./schema` (generated — do not edit by hand).
 */

import type { components } from "./schema";

export type TipResponse = components["schemas"]["TipResponse"];
export type BlockSummary = components["schemas"]["BlockSummary"];
export type BlockDetail = components["schemas"]["BlockDetail"];
export type BlockTxPage = components["schemas"]["BlockTxPage"];
export type TxDetail = components["schemas"]["TxDetail"];
export type AddressStatsResponse = components["schemas"]["AddressStatsResponse"];
export type AddressTxPage = components["schemas"]["AddressTxPage"];
export type MempoolInfo = components["schemas"]["MempoolInfo"];
export type MempoolTxids = components["schemas"]["MempoolTxids"];
export type MwebSummary = components["schemas"]["MwebSummary"];

export type ProblemDetails = {
  type: string;
  title: string;
  status: number;
  detail: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly title: string;
  readonly detail: string;
  readonly type: string;

  constructor(problem: ProblemDetails) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.status = problem.status;
    this.title = problem.title;
    this.detail = problem.detail;
    this.type = problem.type;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseProblem(status: number, body: unknown): ProblemDetails {
  if (isRecord(body)) {
    return {
      type: typeof body.type === "string" ? body.type : "about:blank",
      title:
        typeof body.title === "string" ? body.title : `HTTP ${status}`,
      status: typeof body.status === "number" ? body.status : status,
      detail:
        typeof body.detail === "string"
          ? body.detail
          : `Request failed with status ${status}`,
    };
  }
  return {
    type: "about:blank",
    title: `HTTP ${status}`,
    status,
    detail: `Request failed with status ${status}`,
  };
}

/**
 * Same-origin relative fetch. Throws {@link ApiError} on non-2xx responses.
 * For endpoints that legitimately return problem bodies with useful data on
 * error status (e.g. healthz 503), use {@link fetchApiAllowStatus}.
 */
export async function fetchApi<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const { data, ok } = await fetchApiAllowStatus<T>(path, init);
  if (!ok) {
    throw data;
  }
  return data;
}

type AllowOk<T> = { ok: true; data: T; status: number };
type AllowErr = { ok: false; data: ApiError; status: number };

/**
 * Like {@link fetchApi} but returns either success data or an ApiError
 * without throwing, and still parses JSON bodies on error statuses.
 */
export async function fetchApiAllowStatus<T>(
  path: string,
  init?: RequestInit,
  options?: { acceptStatuses?: number[] },
): Promise<AllowOk<T> | AllowErr> {
  if (!path.startsWith("/")) {
    throw new Error(`fetchApi path must be relative (got: ${path})`);
  }

  const res = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json, application/problem+json",
      ...init?.headers,
    },
  });

  const accept = options?.acceptStatuses ?? [];
  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      body = text;
    }
  }

  if (res.ok || accept.includes(res.status)) {
    return { ok: true, data: body as T, status: res.status };
  }

  const problem = parseProblem(res.status, body);
  return {
    ok: false,
    data: new ApiError(problem),
    status: res.status,
  };
}

export type SearchHit = {
  type: "block" | "tx" | "address";
  id: string;
};

export type NetworkHealth = {
  db_height: number;
  node_height: number;
  lag: number;
};

export type HealthResponse = {
  networks: Record<string, NetworkHealth>;
};

export async function searchEntity(
  network: string,
  q: string,
): Promise<SearchHit> {
  const encoded = encodeURIComponent(q);
  return fetchApi<SearchHit>(`/api/v1/${network}/search/${encoded}`);
}

/** Poll health; accepts 503 so lagging bodies are still usable. */
export async function fetchHealth(): Promise<HealthResponse> {
  const result = await fetchApiAllowStatus<HealthResponse>("/healthz", undefined, {
    acceptStatuses: [503],
  });
  if (!result.ok) {
    throw result.data;
  }
  return result.data;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue;
    }
    sp.set(key, String(value));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export async function fetchTip(network: string): Promise<TipResponse> {
  return fetchApi<TipResponse>(`/api/v1/${network}/tip`);
}

export async function fetchBlocks(
  network: string,
  opts?: { before?: number | null; limit?: number },
): Promise<BlockSummary[]> {
  return fetchApi<BlockSummary[]>(
    `/api/v1/${network}/blocks${qs({ before: opts?.before, limit: opts?.limit })}`,
  );
}

export async function fetchBlock(
  network: string,
  blockId: string,
): Promise<BlockDetail> {
  return fetchApi<BlockDetail>(
    `/api/v1/${network}/block/${encodeURIComponent(blockId)}`,
  );
}

export async function fetchBlockTxs(
  network: string,
  blockId: string,
  opts?: { page?: number; per_page?: number },
): Promise<BlockTxPage> {
  return fetchApi<BlockTxPage>(
    `/api/v1/${network}/block/${encodeURIComponent(blockId)}/txs${qs({
      page: opts?.page,
      per_page: opts?.per_page,
    })}`,
  );
}

export async function fetchTx(network: string, txid: string): Promise<TxDetail> {
  return fetchApi<TxDetail>(
    `/api/v1/${network}/tx/${encodeURIComponent(txid)}`,
  );
}

export async function fetchAddress(
  network: string,
  addr: string,
): Promise<AddressStatsResponse> {
  return fetchApi<AddressStatsResponse>(
    `/api/v1/${network}/address/${encodeURIComponent(addr)}`,
  );
}

export async function fetchAddressTxs(
  network: string,
  addr: string,
  opts?: { page?: number; per_page?: number },
): Promise<AddressTxPage> {
  return fetchApi<AddressTxPage>(
    `/api/v1/${network}/address/${encodeURIComponent(addr)}/txs${qs({
      page: opts?.page,
      per_page: opts?.per_page,
    })}`,
  );
}

export async function fetchMempool(network: string): Promise<MempoolInfo> {
  return fetchApi<MempoolInfo>(`/api/v1/${network}/mempool`);
}

export async function fetchMempoolTxs(
  network: string,
  opts?: { limit?: number },
): Promise<MempoolTxids> {
  return fetchApi<MempoolTxids>(
    `/api/v1/${network}/mempool/txs${qs({ limit: opts?.limit })}`,
  );
}

export async function fetchMwebSummary(network: string): Promise<MwebSummary> {
  return fetchApi<MwebSummary>(`/api/v1/${network}/mweb/summary`);
}
