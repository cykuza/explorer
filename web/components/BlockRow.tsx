"use client";

import { AmountCY } from "@/components/AmountCY";
import { HashLink } from "@/components/HashLink";
import { RelativeAge } from "@/components/RelativeAge";
import { entityHref } from "@/lib/networks";
import type { components } from "@/lib/api/schema";

export type BlockSummary = components["schemas"]["BlockSummary"];

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
      className={`grid h-10 grid-cols-[5.5rem_4rem_4rem_5.5rem_minmax(0,1fr)] items-center gap-3 border-b border-surface-3/40 px-2 text-sm transition-colors duration-700 ${
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
      <span className="font-mono tabular-nums text-text-mute">
        {block.size != null ? `${block.size}` : "—"}
      </span>
      <div className="flex min-w-0 items-center justify-end gap-2">
        <AmountCY value={block.fees} className="text-text-mute" />
        <HashLink
          value={block.hash}
          href={entityHref(network, "block", block.hash)}
          head={6}
          tail={6}
          className="hidden sm:inline-flex"
        />
      </div>
    </div>
  );
}

export function BlockRowHeader({ className = "" }: { className?: string }) {
  return (
    <div
      className={`grid h-8 grid-cols-[5.5rem_4rem_4rem_5.5rem_minmax(0,1fr)] items-center gap-3 border-b border-surface-3 px-2 text-xs text-text-dim ${className}`}
    >
      <span>Height</span>
      <span>Age</span>
      <span>Txs</span>
      <span>Size</span>
      <span className="text-right">Fees</span>
    </div>
  );
}
