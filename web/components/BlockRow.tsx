"use client";

import { AmountCY } from "@/components/AmountCY";
import { HashLink } from "@/components/HashLink";
import { RelativeAge } from "@/components/RelativeAge";
import { entityHref } from "@/lib/networks";
import type { components } from "@/lib/api/schema";

export type BlockSummary = components["schemas"]["BlockSummary"];

/**
 * list — /blocks: Height | Age | Txs | Size | Out (+ hash)
 * feed — dashboard: Block | Hash | Time | Tx | Size
 */
export type BlockRowVariant = "list" | "feed";

const GRID: Record<BlockRowVariant, string> = {
  list: "grid grid-cols-[4.5rem_3.25rem_2.5rem_minmax(0,1fr)] items-center gap-2 px-2 sm:grid-cols-[5.5rem_4rem_4rem_5.5rem_minmax(0,1fr)] sm:gap-3",
  feed: "grid grid-cols-[4.5rem_minmax(0,1fr)_3.25rem_2.5rem] items-center gap-2 px-2 sm:grid-cols-[5.5rem_minmax(0,1fr)_4rem_3rem_5rem] sm:gap-3",
};

type BlockRowProps = {
  block: BlockSummary;
  network: string;
  highlight?: boolean;
  className?: string;
  variant?: BlockRowVariant;
};

export function BlockRow({
  block,
  network,
  highlight = false,
  className = "",
  variant = "list",
}: BlockRowProps) {
  const heightHref = entityHref(network, "block", String(block.height));
  const hashHref = entityHref(network, "block", block.hash);
  const sizeLabel = block.size != null ? `${block.size}` : "—";

  return (
    <div
      className={`${GRID[variant]} h-auto min-h-10 border-b border-surface-3/40 py-1.5 text-xs transition-colors duration-700 sm:h-10 sm:py-0 sm:text-sm ${
        highlight ? "bg-surface-2" : ""
      } ${className}`}
      data-testid="block-row"
      data-height={block.height}
    >
      <a
        href={heightHref}
        className="font-mono tabular-nums text-text-bright underline-offset-2 hover:underline"
      >
        {block.height}
      </a>
      {variant === "list" ? (
        <>
          <RelativeAge time={block.time} />
          <span className="font-mono tabular-nums text-text-mute">
            {block.tx_count}
          </span>
          <span className="hidden font-mono tabular-nums text-text-mute sm:block">
            {sizeLabel}
          </span>
          <div className="flex min-w-0 items-center justify-end gap-2">
            <AmountCY
              value={block.total_out}
              compact
              className="min-w-0 truncate text-xs text-text-mute sm:text-sm"
            />
            <HashLink
              value={block.hash}
              href={hashHref}
              className="hidden sm:inline-flex"
            />
          </div>
        </>
      ) : (
        <>
          <HashLink
            value={block.hash}
            href={hashHref}
            className="min-w-0"
          />
          <RelativeAge time={block.time} />
          <span className="font-mono tabular-nums text-text-mute">
            {block.tx_count}
          </span>
          <span className="hidden font-mono tabular-nums text-text-mute sm:block">
            {sizeLabel}
          </span>
        </>
      )}
    </div>
  );
}

export function BlockRowHeader({
  className = "",
  variant = "list",
}: {
  className?: string;
  variant?: BlockRowVariant;
}) {
  return (
    <div
      className={`${GRID[variant]} h-8 border-b border-surface-3 text-xs text-text-dim ${className}`}
    >
      {variant === "list" ? (
        <>
          <span>Height</span>
          <span>Age</span>
          <span>Txs</span>
          <span className="hidden sm:block">Size</span>
          <span className="text-right">Out</span>
        </>
      ) : (
        <>
          <span>Block</span>
          <span>Hash</span>
          <span>Time</span>
          <span>Tx</span>
          <span className="hidden sm:block">Size</span>
        </>
      )}
    </div>
  );
}
