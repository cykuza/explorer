"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AmountCY } from "@/components/AmountCY";
import { AmountDelta } from "@/components/AmountDelta";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorCard } from "@/components/ErrorCard";
import { HashLink } from "@/components/HashLink";
import { RelativeAge } from "@/components/RelativeAge";
import { Skeleton } from "@/components/Skeleton";
import {
  fetchAddress,
  fetchAddressTxs,
  type AddressStatsResponse,
  type AddressTxPage,
} from "@/lib/api/client";
import { useEntityId } from "@/hooks/usePrettyPathname";
import {
  activeNetworkFromPathname,
  entityHref,
} from "@/lib/networks";

const PER_PAGE = 25;

export function AddressView() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  const addr = useEntityId("address");

  if (!addr) {
    return (
      <EmptyState
        title="Address"
        detail="Open an address via /address/{addr}."
      />
    );
  }

  return (
    <AddressViewInner key={`${network}:${addr}`} network={network} addr={addr} />
  );
}

function AddressViewInner({
  network,
  addr,
}: {
  network: string;
  addr: string;
}) {
  const [stats, setStats] = useState<AddressStatsResponse | null>(null);
  const [txs, setTxs] = useState<AddressTxPage | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const [s, t] = await Promise.all([
        fetchAddress(network, addr),
        fetchAddressTxs(network, addr, { page, per_page: PER_PAGE }),
      ]);
      setStats(s);
      setTxs(t);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [addr, network, page]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(id);
  }, [load]);

  if (loading && !stats) {
    return (
      <div className="space-y-4" data-testid="address-loading">
        <Skeleton className="h-8 w-64" />
        <Card>
          <Skeleton className="mb-2 h-4 w-full" />
          <Skeleton className="h-4 w-1/2" />
        </Card>
      </div>
    );
  }

  if (error && !stats) {
    return <ErrorCard error={error} />;
  }

  if (!stats) {
    return <EmptyState title="Address not found" />;
  }

  const totalPages = txs ? Math.max(1, Math.ceil(txs.total / txs.per_page)) : 1;

  return (
    <div className="space-y-4" data-testid="address-page">
      <h1 className="font-accent text-2xl text-text-bright">Address</h1>
      <Card data-testid="address-header">
        <div className="mb-3">
          <HashLink value={stats.address} head={12} tail={12} />
        </div>
        <dl className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Balance">
            <span data-testid="address-balance">
              <AmountCY value={stats.balance} className="text-text-bright" />
            </span>
          </Field>
          <Field label="Received">
            <AmountCY value={stats.received} />
          </Field>
          <Field label="Sent">
            <AmountCY value={stats.sent} />
          </Field>
          <Field label="Tx count">
            <span className="font-mono tabular-nums">{stats.tx_count}</span>
          </Field>
          <Field label="First seen">
            <a
              href={entityHref(network, "block", String(stats.first_seen_height))}
              className="font-mono text-text-mute underline-offset-2 hover:underline"
            >
              {stats.first_seen_height}
            </a>
          </Field>
          <Field label="Last seen">
            <a
              href={entityHref(network, "block", String(stats.last_seen_height))}
              className="font-mono text-text-mute underline-offset-2 hover:underline"
            >
              {stats.last_seen_height}
            </a>
          </Field>
        </dl>
      </Card>

      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-accent text-lg text-text-bright">History</h2>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
            >
              Newer
            </Button>
            <span className="font-mono text-xs text-text-dim">
              {page} / {totalPages}
            </span>
            <Button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= totalPages || loading}
            >
              Older
            </Button>
          </div>
        </div>
        {!txs || txs.txs.length === 0 ? (
          <EmptyState title="No transactions" className="border-0 p-2" />
        ) : (
          <ul>
            <li className="grid h-8 grid-cols-[minmax(0,1fr)_5rem_4rem_minmax(7rem,auto)] items-center gap-3 border-b border-surface-3 px-1 text-xs text-text-dim">
              <span>Txid</span>
              <span>Height</span>
              <span>Age</span>
              <span className="text-right">Delta</span>
            </li>
            {txs.txs.map((row) => (
              <li
                key={`${row.txid}-${row.block_height}`}
                className="grid h-10 grid-cols-[minmax(0,1fr)_5rem_4rem_minmax(7rem,auto)] items-center gap-3 border-b border-surface-3/40 px-1 text-sm"
                data-testid="address-tx-row"
              >
                <HashLink
                  value={row.txid}
                  href={entityHref(network, "tx", row.txid)}
                />
                <a
                  href={entityHref(network, "block", String(row.block_height))}
                  className="font-mono tabular-nums text-text-mute underline-offset-2 hover:underline"
                >
                  {row.block_height}
                </a>
                <RelativeAge time={row.time} />
                <div className="text-right">
                  <AmountDelta value={row.delta} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs text-text-dim">{label}</dt>
      <dd className="mt-0.5 text-text">{children}</dd>
    </div>
  );
}
