"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AmountCY } from "@/components/AmountCY";
import { BlockRow, BlockRowHeader } from "@/components/BlockRow";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorCard } from "@/components/ErrorCard";
import { RelativeAge } from "@/components/RelativeAge";
import { Skeleton, SkeletonRow, SkeletonStat } from "@/components/Skeleton";
import { TxIdRow } from "@/components/TxIdRow";
import {
  fetchBlock,
  fetchBlocks,
  fetchLatestTxs,
  fetchMempool,
  fetchMwebSummary,
  fetchTip,
  type BlockSummary,
  type LatestTxItem,
  type MempoolInfo,
  type MwebSummary,
  type TipResponse,
} from "@/lib/api/client";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import {
  activeNetworkFromPathname,
  entityHref,
  networkHref,
} from "@/lib/networks";

const LATEST_LIMIT = 10;
const LATEST_TX_LIMIT = 12;
const HIGHLIGHT_MS = 2500;

type DashState = {
  tip: TipResponse | null;
  difficulty: string | null;
  blocks: BlockSummary[];
  txs: LatestTxItem[];
  mempool: MempoolInfo | null;
  mweb: MwebSummary | null;
};

export function DashboardView() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  const [data, setData] = useState<DashState | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const live = useLiveEvents(network, { enabled: !loading && data != null });
  const [highlightHeights, setHighlightHeights] = useState<Set<number>>(
    () => new Set(),
  );
  const lastTipHeight = useRef<number | null>(null);

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const [tip, blocks, txs, mempool, mweb] = await Promise.all([
        fetchTip(network),
        fetchBlocks(network, { limit: LATEST_LIMIT }),
        fetchLatestTxs(network, { limit: LATEST_TX_LIMIT }),
        fetchMempool(network),
        fetchMwebSummary(network),
      ]);
      setData({
        tip,
        difficulty: null,
        blocks,
        txs,
        mempool,
        mweb,
      });
      lastTipHeight.current = tip.height;
      setLoading(false);
      try {
        const detail = await fetchBlock(network, String(tip.height));
        setData((cur) =>
          cur ? { ...cur, difficulty: detail.difficulty } : cur,
        );
      } catch {
        // difficulty is optional for first paint
      }
    } catch (err) {
      setError(err);
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
    const tip = live.tip;
    if (!tip || lastTipHeight.current === null) {
      return;
    }
    if (tip.height <= lastTipHeight.current) {
      return;
    }
    const prev = lastTipHeight.current;
    lastTipHeight.current = tip.height;

    void (async () => {
      try {
        const [newBlock, latestTxs] = await Promise.all([
          fetchBlock(network, String(tip.height)),
          fetchLatestTxs(network, { limit: LATEST_TX_LIMIT }),
        ]);
        const summary: BlockSummary = {
          height: newBlock.height,
          hash: newBlock.hash,
          time: newBlock.time,
          tx_count: newBlock.tx_count,
          size: newBlock.size,
          total_out: newBlock.total_out,
          fees: newBlock.fees,
          has_mweb: newBlock.mweb != null,
        };
        setData((cur) => {
          if (!cur) {
            return cur;
          }
          const withoutDup = cur.blocks.filter((b) => b.height !== summary.height);
          return {
            ...cur,
            tip: { height: tip.height, hash: tip.hash, time: tip.time },
            difficulty: newBlock.difficulty ?? cur.difficulty,
            blocks: [summary, ...withoutDup].slice(0, LATEST_LIMIT),
            txs: latestTxs,
          };
        });
        setHighlightHeights((s) => new Set(s).add(summary.height));
        window.setTimeout(() => {
          setHighlightHeights((s) => {
            const next = new Set(s);
            next.delete(summary.height);
            return next;
          });
        }, HIGHLIGHT_MS);

        if (tip.height - prev > 1) {
          const gap = await fetchBlocks(network, { limit: LATEST_LIMIT });
          setData((cur) => (cur ? { ...cur, blocks: gap } : cur));
        }
      } catch {
        // Ignore transient live refresh errors.
      }
    })();
  }, [live.tip, network]);

  useEffect(() => {
    const mp = live.mempool;
    if (!mp) {
      return;
    }
    setData((cur) =>
      cur
        ? {
            ...cur,
            mempool: {
              count: mp.count,
              vsize: mp.vsize,
              total_fee: cur.mempool?.total_fee ?? "0",
            },
          }
        : cur,
    );
  }, [live.mempool]);

  if (loading && !data) {
    return (
      <div className="space-y-6" data-testid="dashboard-loading">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Card key={i} className="min-h-[4.5rem]">
              <SkeletonStat />
            </Card>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card className="min-h-[28rem]">
            <h2 className="mb-3 h-7 font-accent text-xl text-text-bright">
              Latest Transactions
            </h2>
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="mb-2 h-8 w-full" />
            ))}
          </Card>
          <Card className="min-h-[28rem]">
            <h2 className="mb-3 h-7 font-accent text-xl text-text-bright">
              Latest blocks
            </h2>
            <BlockRowHeader variant="feed" />
            {Array.from({ length: LATEST_LIMIT }).map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </Card>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return <ErrorCard error={error} />;
  }

  if (!data?.tip) {
    return <EmptyState title="No tip yet" detail="Waiting for indexed blocks." />;
  }

  const tip = live.tip ?? data.tip;
  const mempool = live.mempool
    ? {
        count: live.mempool.count,
        vsize: live.mempool.vsize,
        total_fee: data.mempool?.total_fee ?? "0",
      }
    : data.mempool;

  return (
    <div className="space-y-6" data-testid="dashboard">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard
          label="Tip height"
          href={networkHref(network, "/blocks")}
          testId="stat-tip"
        >
          <span
            className="font-mono text-xl tabular-nums text-text-bright"
            data-testid="tip-height"
          >
            {tip.height}
          </span>
        </StatCard>
        <StatCard
          label="Last block"
          href={entityHref(network, "block", String(tip.height))}
          testId="stat-last-block"
        >
          <RelativeAge time={tip.time} className="text-xl text-text-bright" />
        </StatCard>
        <StatCard
          label="Difficulty"
          href={networkHref(network, "/charts")}
          testId="stat-difficulty"
        >
          <span className="font-mono text-sm tabular-nums text-text-bright sm:text-lg">
            {data.difficulty ?? "—"}
          </span>
        </StatCard>
        <StatCard
          label="Mempool"
          href={networkHref(network, "/mempool")}
          testId="stat-mempool"
        >
          <span className="font-mono text-sm tabular-nums text-text-bright sm:text-lg">
            {mempool?.count ?? 0}
            <span className="ml-1 text-xs text-text-dim sm:text-sm">
              / {mempool?.vsize ?? 0} vB
            </span>
          </span>
        </StatCard>
        <StatCard
          label="MWEB"
          href={networkHref(network, "/mweb")}
          testId="stat-mweb"
        >
          <AmountCY
            value={data.mweb?.mweb_amount ?? "0"}
            compact
            className="text-sm text-text-bright sm:text-base"
          />
        </StatCard>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="min-h-[28rem]">
          <h2 className="mb-2 h-7 font-accent text-xl text-text-bright">
            Latest Transactions
          </h2>
          {data.txs.length === 0 ? (
            <EmptyState
              title="No transactions"
              className="border-0 bg-transparent p-2"
            />
          ) : (
            <ul className="space-y-1" data-testid="latest-txs">
              {data.txs.map((tx) => (
                <TxIdRow
                  key={tx.txid}
                  txid={tx.txid}
                  network={network}
                  isHogex={tx.is_hogex}
                  hasMweb={tx.has_mweb}
                  testId="latest-tx-row"
                />
              ))}
            </ul>
          )}
        </Card>

        <Card className="min-h-[28rem]">
          <div className="mb-2 flex h-7 items-baseline justify-between">
            <h2 className="font-accent text-xl text-text-bright">
              Latest blocks
            </h2>
            <a
              href={networkHref(network, "/blocks")}
              className="text-xs text-text-dim hover:text-text-mute"
            >
              View all
            </a>
          </div>
          <BlockRowHeader variant="feed" />
          {data.blocks.length === 0 ? (
            <EmptyState
              title="No blocks"
              className="border-0 bg-transparent p-2"
            />
          ) : (
            data.blocks.map((b) => (
              <BlockRow
                key={b.hash}
                block={b}
                network={network}
                highlight={highlightHeights.has(b.height)}
                variant="feed"
              />
            ))
          )}
        </Card>
      </div>
    </div>
  );
}

function StatCard({
  label,
  children,
  testId,
  href,
}: {
  label: string;
  children: ReactNode;
  testId?: string;
  href: string;
}) {
  return (
    <Card
      href={href}
      data-testid={testId}
      className="min-h-[4.5rem] min-w-0 overflow-hidden"
      aria-label={`${label}: open`}
    >
      <p className="text-xs uppercase tracking-wide text-text-dim">{label}</p>
      <div className="mt-1 min-h-8 min-w-0 break-all">{children}</div>
    </Card>
  );
}
