"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { BlockRow, BlockRowHeader } from "@/components/BlockRow";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorCard } from "@/components/ErrorCard";
import { SkeletonRow } from "@/components/Skeleton";
import { fetchBlocks, type BlockSummary } from "@/lib/api/client";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { activeNetworkFromPathname } from "@/lib/networks";

const PAGE_LIMIT = 25;

export function BlocksView() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  const live = useLiveEvents(network);

  const [blocks, setBlocks] = useState<BlockSummary[]>([]);
  const [before, setBefore] = useState<number | null>(null);
  const [cursorStack, setCursorStack] = useState<(number | null)[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [tipBaseline, setTipBaseline] = useState<number | null>(null);

  const load = useCallback(
    async (cursor: number | null, opts?: { resetStack?: boolean }) => {
      await Promise.resolve();
      setLoading(true);
      setError(null);
      try {
        const list = await fetchBlocks(network, {
          before: cursor ?? undefined,
          limit: PAGE_LIMIT,
        });
        setBlocks(list);
        setBefore(cursor);
        if (opts?.resetStack) {
          setCursorStack([]);
        }
        if (cursor === null && list[0]) {
          setTipBaseline(list[0].height);
        }
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    },
    [network],
  );

  useEffect(() => {
    const id = window.setTimeout(() => {
      void load(null, { resetStack: true });
    }, 0);
    return () => window.clearTimeout(id);
  }, [load]);

  const atTip = before === null;
  const liveTip = live.tip?.height ?? tipBaseline;
  const newestVisible = blocks[0]?.height ?? null;
  let newCount = 0;
  if (!atTip && liveTip != null && newestVisible != null) {
    newCount = Math.max(0, liveTip - newestVisible);
  } else if (atTip && liveTip != null && tipBaseline != null) {
    newCount = Math.max(0, liveTip - tipBaseline);
  }

  const showNewPill = newCount > 0;

  function goOlder() {
    const oldest = blocks[blocks.length - 1];
    if (!oldest) {
      return;
    }
    setCursorStack((s) => [...s, before]);
    void load(oldest.height);
  }

  function goNewer() {
    if (cursorStack.length === 0) {
      void load(null);
      if (liveTip != null) {
        setTipBaseline(liveTip);
      }
      return;
    }
    const prev = cursorStack[cursorStack.length - 1] ?? null;
    setCursorStack((s) => s.slice(0, -1));
    void load(prev);
  }

  function jumpToTip() {
    if (liveTip != null) {
      setTipBaseline(liveTip);
    }
    void load(null, { resetStack: true });
  }

  const canOlder = blocks.length >= PAGE_LIMIT;
  const canNewer = !atTip || cursorStack.length > 0;

  return (
    <div className="space-y-4" data-testid="blocks-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-accent text-2xl text-text-bright">Blocks</h1>
        <div className="flex items-center gap-2">
          {showNewPill ? (
            <button
              type="button"
              onClick={jumpToTip}
              className="rounded-sm border border-surface-3 bg-surface-2 px-3 py-1 text-xs text-metal hover:bg-surface-3"
              data-testid="new-blocks-pill"
            >
              {newCount} new block{newCount === 1 ? "" : "s"}
            </button>
          ) : null}
          <Button onClick={goNewer} disabled={!canNewer || loading}>
            Newer
          </Button>
          <Button onClick={goOlder} disabled={!canOlder || loading}>
            Older
          </Button>
        </div>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="p-2">
          <BlockRowHeader />
        </div>
        {loading && blocks.length === 0 ? (
          <div className="px-2 pb-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        ) : null}
        {error && blocks.length === 0 ? (
          <div className="p-4">
            <ErrorCard error={error} />
          </div>
        ) : null}
        {!loading && !error && blocks.length === 0 ? (
          <div className="p-4">
            <EmptyState title="No blocks" />
          </div>
        ) : null}
        <div className="px-2 pb-2">
          {blocks.map((b) => (
            <BlockRow key={b.hash} block={b} network={network} />
          ))}
        </div>
      </Card>
    </div>
  );
}
