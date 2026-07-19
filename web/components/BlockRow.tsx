"use client";

import { AmountCY } from "@/components/AmountCY";
import { HashLink } from "@/components/HashLink";
import { RelativeAge } from "@/components/RelativeAge";
import { entityHref } from "@/lib/networks";
import type { components } from "@/lib/api/schema";

export type BlockSummary = components["schemas"]["BlockSummary"];

/** Mobile: Height | Age | Txs | Out. sm+: + Size; Hash via HashLink. */
const BLOCK_ROW_GRID =
  "grid grid-cols-[4.5rem_3.25rem_2.5rem_minmax(0,1fr)] items-center gap-2 px-2 sm:grid-cols-[5.5rem_4rem_4rem_5.5rem_minmax(0,1fr)] sm:gap-3";

type BlockRowProps = {
  block: BlockSummary;
  network: string;
  highlight?: boolean;
  className?: string;
};

export function BlockRow({
  block,
  network,
  highlight = false,
  className = "",
}: BlockRowProps) {
  const href = entityHref(network, "block", String(block.height));
  return (
    <div
      className={`${BLOCK_ROW_GRID} h-auto min-h-10 border-b border-surface-3/40 py-1.5 text-xs transition-colors duration-700 sm:h-10 sm:py-0 sm:text-sm ${
        highlight ? "bg-surface-2" : ""
      } ${className}`}
      data-testid="block-row"
      data-height={block.height}
    >
      <a
        href={href}
        className="font-mono tabular-nums text-text-bright underline-offset-2 hover:underline"
      >
        {block.height}
      </a>
      <RelativeAge time={block.time} />
      <span className="font-mono tabular-nums text-text-mute">{block.tx_count}</span>
      <span className="hidden font-mono tabular-nums text-text-mute sm:block">
        {block.size != null ? `${block.size}` : "—"}
      </span>
      <div className="flex min-w-0 items-center justify-end gap-2">
        <AmountCY
          value={block.total_out}
          compact
          className="min-w-0 truncate text-xs text-text-mute sm:text-sm"
        />
        <HashLink
          value={block.hash}
          href={entityHref(network, "block", block.hash)}
          className="hidden sm:inline-flex"
        />
      </div>
    </div>
  );
}

export function BlockRowHeader({ className = "" }: { className?: string }) {
  return (
    <div
      className={`${BLOCK_ROW_GRID} h-8 border-b border-surface-3 text-xs text-text-dim ${className}`}
    >
      <span>Height</span>
      <span>Age</span>
      <span>Txs</span>
      <span className="hidden sm:block">Size</span>
      <span className="text-right">Out</span>
    </div>
  );
}
