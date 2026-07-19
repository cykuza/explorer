"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorCard } from "@/components/ErrorCard";
import { HashLink } from "@/components/HashLink";
import { Skeleton } from "@/components/Skeleton";
import {
  fetchMempool,
  fetchMempoolTxs,
  type MempoolInfo,
} from "@/lib/api/client";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import {
  activeNetworkFromPathname,
  entityHref,
} from "@/lib/networks";

const TX_LIMIT = 200;

export function MempoolView() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  return <MempoolViewInner key={network} network={network} />;
}

function MempoolViewInner({ network }: { network: string }) {
  const live = useLiveEvents(network);
  const [info, setInfo] = useState<MempoolInfo | null>(null);
  const [txids, setTxids] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const [mp, txs] = await Promise.all([
        fetchMempool(network),
        fetchMempoolTxs(network, { limit: TX_LIMIT }),
      ]);
      setInfo(mp);
      setTxids(txs.txids);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [network]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(id);
  }, [load]);

  useEffect(() => {
    const mp = live.mempool;
    if (!mp) {
      return;
    }
    void (async () => {
      await Promise.resolve();
      setInfo((cur) => ({
        count: mp.count,
        vsize: mp.vsize,
        total_fee: cur?.total_fee ?? "0",
      }));
      try {
        const r = await fetchMempoolTxs(network, { limit: TX_LIMIT });
        setTxids(r.txids);
      } catch {
        // ignore transient refresh errors
      }
    })();
  }, [live.mempool, network]);

  if (loading && !info) {
    return (
      <div className="space-y-4" data-testid="mempool-loading">
        <Skeleton className="h-8 w-40" />
        <Card>
          <Skeleton className="h-10 w-48" />
        </Card>
        <Card>
          <Skeleton className="h-40 w-full" />
        </Card>
      </div>
    );
  }

  if (error && !info) {
    return <ErrorCard error={error} />;
  }

  const count = live.mempool?.count ?? info?.count ?? 0;
  const vsize = live.mempool?.vsize ?? info?.vsize ?? 0;

  return (
    <div className="space-y-4" data-testid="mempool-page">
      <h1 className="font-accent text-2xl text-text-bright">Mempool</h1>

      <Card>
        <dl className="grid gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-text-dim">Transactions</dt>
            <dd
              className="mt-0.5 font-mono text-xl tabular-nums text-text-bright"
              data-testid="mempool-count"
            >
              {count}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-dim">Virtual size</dt>
            <dd
              className="mt-0.5 font-mono text-xl tabular-nums text-text-bright"
              data-testid="mempool-vsize"
            >
              {vsize}{" "}
              <span className="text-sm text-text-dim">vB</span>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-dim">Total fee</dt>
            <dd className="mt-0.5 font-mono text-xl tabular-nums text-text-bright">
              {info?.total_fee ?? "—"}
            </dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="mb-3 font-accent text-lg text-text-bright">
          Transactions
        </h2>
        {txids.length === 0 ? (
          <div data-testid="mempool-empty">
            <EmptyState
              title="mempool is empty"
              className="border-0 bg-transparent p-2"
            />
          </div>
        ) : (
          <ul className="space-y-1" data-testid="mempool-list">
            {txids.map((txid) => (
              <li key={txid} className="flex h-8 items-center">
                <HashLink
                  value={txid}
                  href={entityHref(network, "tx", txid)}
                />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
