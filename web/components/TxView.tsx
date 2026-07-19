"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AmountCY } from "@/components/AmountCY";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorCard } from "@/components/ErrorCard";
import { HashLink } from "@/components/HashLink";
import { Skeleton } from "@/components/Skeleton";
import { TxKindBadge } from "@/components/TxKindBadge";
import { fetchTx, type TxDetail } from "@/lib/api/client";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { useEntityId } from "@/hooks/usePrettyPathname";
import {
  activeNetworkFromPathname,
  entityHref,
} from "@/lib/networks";
import { truncateMiddle } from "@/lib/truncateMiddle";

type ScriptPubKey = {
  address?: string;
  addresses?: string[];
  type?: string;
};

function spkAddress(spk: unknown): string | null {
  if (!spk || typeof spk !== "object") {
    return null;
  }
  const o = spk as ScriptPubKey;
  if (typeof o.address === "string") {
    return o.address;
  }
  if (Array.isArray(o.addresses) && typeof o.addresses[0] === "string") {
    return o.addresses[0];
  }
  return null;
}

function spkType(spk: unknown): string | null {
  if (!spk || typeof spk !== "object") {
    return null;
  }
  const t = (spk as ScriptPubKey).type;
  return typeof t === "string" ? t : null;
}

function SpentChip({
  spentByTxid,
  network,
}: {
  spentByTxid: string | null | undefined;
  network: string;
}) {
  if (spentByTxid === undefined) {
    return null;
  }
  if (spentByTxid == null) {
    return (
      <span
        className="rounded-sm border border-metal/50 px-1.5 py-0.5 text-xs text-text-bright"
        data-testid="tx-vout-unspent"
      >
        unspent
      </span>
    );
  }
  const short = truncateMiddle(spentByTxid);
  return (
    <a
      href={entityHref(network, "tx", spentByTxid)}
      className="whitespace-nowrap rounded-sm border border-surface-3 px-1.5 py-0.5 font-mono text-xs text-text-dim hover:border-text-dim hover:text-text-mute"
      data-testid="tx-vout-spent"
      title={spentByTxid}
    >
      spent · {short}
    </a>
  );
}

export function TxView() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  const txid = useEntityId("tx");

  if (!txid) {
    return (
      <EmptyState title="Transaction" detail="Open a tx via /tx/{txid}." />
    );
  }

  return <TxViewInner key={`${network}:${txid}`} network={network} txid={txid} />;
}

function TxViewInner({ network, txid }: { network: string; txid: string }) {
  const live = useLiveEvents(network);
  const [tx, setTx] = useState<TxDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [rawOpen, setRawOpen] = useState(false);

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      setTx(await fetchTx(network, txid));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [txid, network]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(id);
  }, [load]);

  if (loading && !tx) {
    return (
      <div className="space-y-4" data-testid="tx-loading">
        <Skeleton className="h-8 w-56" />
        <Card>
          <Skeleton className="mb-2 h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </Card>
      </div>
    );
  }

  if (error && !tx) {
    return <ErrorCard error={error} />;
  }

  if (!tx) {
    return <EmptyState title="Transaction not found" />;
  }

  const tipHeight = live.tip?.height;
  const confirmations =
    tx.block_height != null && tipHeight != null
      ? Math.max(0, tipHeight - tx.block_height + 1)
      : tx.block_height != null
        ? tx.confirmations
        : 0;

  return (
    <div className="space-y-4" data-testid="tx-page">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-accent text-2xl text-text-bright">Transaction</h1>
        <TxKindBadge isHogex={tx.is_hogex} hasMweb={tx.has_mweb} />
      </div>

      <Card data-testid="tx-header">
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <Field label="Txid">
            <HashLink value={tx.txid} />
          </Field>
          <Field label="Confirmations">
            <span className="font-mono tabular-nums" data-testid="tx-confirmations">
              {confirmations}
            </span>
          </Field>
          <Field label="Fee">
            {tx.fee != null ? <AmountCY value={tx.fee} /> : "—"}
          </Field>
          <Field label="Size / vsize">
            <span className="font-mono tabular-nums">
              {tx.size ?? "—"} / {tx.vsize ?? "—"}
            </span>
          </Field>
          {tx.block_height != null ? (
            <Field label="Block">
              <a
                href={entityHref(network, "block", String(tx.block_height))}
                className="font-mono text-text-mute underline-offset-2 hover:underline"
              >
                {tx.block_height}
              </a>
            </Field>
          ) : (
            <Field label="Block">
              <span className="text-text-dim">mempool</span>
            </Field>
          )}
        </dl>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2" data-testid="tx-vin-vout">
        <Card>
          <h2 className="mb-3 font-accent text-lg text-text-bright">
            Inputs ({tx.vin.length})
          </h2>
          <ul className="space-y-2">
            {tx.vin.map((vin, i) => {
              const coinbase = Boolean(vin.coinbase);
              const addr = vin.prevout?.address ?? null;
              const value = vin.prevout?.value ?? null;
              return (
                <li
                  key={i}
                  className="min-h-12 border-b border-surface-3/40 pb-2 text-sm"
                  data-testid="tx-vin"
                >
                  {coinbase ? (
                    <span className="text-text-mute">Coinbase</span>
                  ) : (
                    <div className="space-y-0.5">
                      {addr ? (
                        <HashLink
                          value={addr}
                          href={entityHref(network, "address", addr)}
                        />
                      ) : (
                        <span className="text-text-dim">unknown</span>
                      )}
                      {value != null ? (
                        <div>
                          <AmountCY value={value} className="text-text-mute" />
                        </div>
                      ) : null}
                      {vin.txid ? (
                        <HashLink
                          value={vin.txid}
                          href={entityHref(network, "tx", vin.txid)}
                          className="text-xs"
                        />
                      ) : null}
                    </div>
                  )}
                  {vin.ismweb ? (
                    <span className="mt-1 inline-block rounded-sm border border-surface-3 px-1.5 py-0.5 text-xs text-metal">
                      MWEB
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </Card>

        <Card>
          <h2 className="mb-3 font-accent text-lg text-text-bright">
            Outputs ({tx.vout.length})
          </h2>
          <ul className="space-y-2">
            {tx.vout.map((vout) => {
              const addr = spkAddress(vout.scriptPubKey);
              const typ = spkType(vout.scriptPubKey);
              return (
                <li
                  key={vout.n}
                  className="min-h-12 border-b border-surface-3/40 pb-2 text-sm"
                  data-testid="tx-vout"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    {addr ? (
                      <HashLink
                        value={addr}
                        href={entityHref(network, "address", addr)}
                      />
                    ) : (
                      <span className="text-text-dim">no address</span>
                    )}
                    {vout.value != null ? (
                      <AmountCY value={vout.value} className="text-text-mute" />
                    ) : null}
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-text-dim">
                    <span>#{vout.n}</span>
                    {typ ? <span>{typ}</span> : null}
                    <SpentChip
                      spentByTxid={vout.spent_by_txid}
                      network={network}
                    />
                    {vout.ismweb ? (
                      <span className="rounded-sm border border-surface-3 px-1.5 py-0.5 text-metal">
                        MWEB
                      </span>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>

      <Card>
        <button
          type="button"
          onClick={() => setRawOpen((o) => !o)}
          className="font-accent text-lg text-text-bright"
          aria-expanded={rawOpen}
        >
          Raw JSON {rawOpen ? "▾" : "▸"}
        </button>
        {rawOpen ? (
          <pre
            className="mt-3 max-h-96 overflow-auto font-mono text-xs text-text-mute"
            data-testid="tx-raw-json"
          >
            {JSON.stringify(tx, null, 2)}
          </pre>
        ) : null}
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
