"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AmountCY } from "@/components/AmountCY";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorCard } from "@/components/ErrorCard";
import { HashLink } from "@/components/HashLink";
import { Hint } from "@/components/Hint";
import { RelativeAge } from "@/components/RelativeAge";
import { Skeleton } from "@/components/Skeleton";
import { TxKindBadge } from "@/components/TxKindBadge";
import {
  fetchBlock,
  fetchBlockTxs,
  type BlockDetail,
  type BlockTxPage,
} from "@/lib/api/client";
import { useEntityId } from "@/hooks/usePrettyPathname";
import {
  activeNetworkFromPathname,
  entityHref,
} from "@/lib/networks";

const PER_PAGE = 25;

export function BlockView() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  const blockId = useEntityId("block");

  if (!blockId) {
    return (
      <EmptyState
        title="Block"
        detail="Open a block via /block/{height|hash}."
      />
    );
  }

  return <BlockViewInner key={`${network}:${blockId}`} network={network} blockId={blockId} />;
}

function BlockViewInner({
  network,
  blockId,
}: {
  network: string;
  blockId: string;
}) {
  const [block, setBlock] = useState<BlockDetail | null>(null);
  const [txs, setTxs] = useState<BlockTxPage | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const [detail, txPage] = await Promise.all([
        fetchBlock(network, blockId),
        fetchBlockTxs(network, blockId, { page, per_page: PER_PAGE }),
      ]);
      setBlock(detail);
      setTxs(txPage);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [blockId, network, page]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(id);
  }, [load]);

  if (loading && !block) {
    return (
      <div className="space-y-4" data-testid="block-loading">
        <Skeleton className="h-8 w-48" />
        <Card>
          <Skeleton className="mb-2 h-4 w-full" />
          <Skeleton className="mb-2 h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </Card>
      </div>
    );
  }

  if (error && !block) {
    return <ErrorCard error={error} />;
  }

  if (!block) {
    return <EmptyState title="Block not found" />;
  }

  const totalPages = txs ? Math.max(1, Math.ceil(txs.total / txs.per_page)) : 1;

  return (
    <div className="space-y-4" data-testid="block-page">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-accent text-2xl text-text-bright">
          Block {block.height}
        </h1>
        <nav className="flex items-center gap-1" aria-label="Adjacent blocks">
          {block.prev_hash ? (
            <a
              href={entityHref(network, "block", block.prev_hash)}
              className="border border-surface-3 px-2 py-1 text-sm text-text-mute hover:text-text-bright"
              aria-label="Previous block"
            >
              ←
            </a>
          ) : (
            <span className="border border-surface-3/40 px-2 py-1 text-sm text-text-dim">
              ←
            </span>
          )}
          {block.next_hash ? (
            <a
              href={entityHref(network, "block", block.next_hash)}
              className="border border-surface-3 px-2 py-1 text-sm text-text-mute hover:text-text-bright"
              aria-label="Next block"
            >
              →
            </a>
          ) : (
            <span className="border border-surface-3/40 px-2 py-1 text-sm text-text-dim">
              →
            </span>
          )}
        </nav>
      </div>

      <Card data-testid="block-header">
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <Field label="Hash">
            <span data-testid="block-hash">
              <HashLink value={block.hash} />
            </span>
          </Field>
          <Field label="Time">
            <RelativeAge time={block.time} />
            <span className="ml-2 text-text-dim">
              {new Date(block.time * 1000).toISOString()}
            </span>
          </Field>
          <Field label="Size / weight">
            <span className="font-mono tabular-nums">
              {block.size ?? "—"} / {block.weight ?? "—"}
            </span>
          </Field>
          <Field label="Difficulty">
            <span className="font-mono tabular-nums">
              {block.difficulty ?? "—"}
            </span>
          </Field>
          <Field label="Tx count">
            <span className="font-mono tabular-nums">{block.tx_count}</span>
          </Field>
          <Field label="Total out">
            <AmountCY value={block.total_out} />
          </Field>
          <Field label="Fees">
            <AmountCY value={block.fees} />
          </Field>
        </dl>
      </Card>

      {block.mweb ? (
        <Card data-testid="block-mweb">
          <h2 className="mb-3 font-accent text-lg text-text-bright">MWEB</h2>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <Field
              label="MWEB amount"
              hint="Total coins currently held inside the MWEB protocol."
            >
              <AmountCY value={block.mweb.mweb_amount} />
            </Field>
            <Field label="Kernels / TXOs">
              <span className="font-mono tabular-nums">
                {block.mweb.num_kernels} / {block.mweb.num_txos}
              </span>
            </Field>
            <Field label="Pegin">
              <AmountCY value={block.mweb.pegin} />
            </Field>
            <Field label="Pegout">
              <AmountCY value={block.mweb.pegout} />
            </Field>
            <Field label="Kernel fees">
              <AmountCY value={block.mweb.kernel_fees} />
            </Field>
            {block.mweb.hogex_txid ? (
              <Field
                label="HogEx"
                hint="Hogwarts Extension transaction that commits this block’s MWEB state to the transparent chain."
              >
                <HashLink
                  value={block.mweb.hogex_txid}
                  href={entityHref(network, "tx", block.mweb.hogex_txid)}
                />
              </Field>
            ) : null}
          </dl>
        </Card>
      ) : null}

      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-accent text-lg text-text-bright">Transactions</h2>
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
          <ul className="divide-y divide-surface-3/40">
            {txs.txs.map((tx) => (
              <li
                key={tx.txid}
                className="grid h-10 grid-cols-[minmax(0,1fr)_4.5rem_minmax(14rem,max-content)] items-center gap-3 text-sm"
                data-testid="block-tx-row"
              >
                <HashLink
                  value={tx.txid}
                  href={entityHref(network, "tx", tx.txid)}
                />
                <span className="flex justify-end">
                  <TxKindBadge isHogex={tx.is_hogex} hasMweb={tx.has_mweb} />
                </span>
                <AmountCY
                  value={tx.total_out}
                  className="justify-self-end text-right text-text-mute"
                />
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
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <dt className="flex items-center gap-1.5 text-xs text-text-dim">
        <span>{label}</span>
        {hint ? <Hint content={hint} /> : null}
      </dt>
      <dd className="mt-0.5 text-text">{children}</dd>
    </div>
  );
}
