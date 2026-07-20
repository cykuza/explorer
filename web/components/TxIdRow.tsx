"use client";

import { HashLink } from "@/components/HashLink";
import { TxKindBadge } from "@/components/TxKindBadge";
import { entityHref } from "@/lib/networks";

/**
 * list — mempool: txid + kind badge
 * feed — dashboard: TxID column, block-row geometry, no badges
 */
export type TxIdRowVariant = "list" | "feed";

const FEED_ROW =
  "flex h-auto min-h-10 items-center border-b border-surface-3/40 px-2 py-1.5 text-xs sm:h-10 sm:py-0 sm:text-sm";

type TxIdRowProps = {
  txid: string;
  network: string;
  isHogex?: boolean;
  hasMweb?: boolean;
  className?: string;
  /** Optional test id on the row element. */
  testId?: string;
  variant?: TxIdRowVariant;
};

/** Dense txid row — feed (dashboard) or list (mempool). */
export function TxIdRow({
  txid,
  network,
  isHogex = false,
  hasMweb = false,
  className = "",
  testId,
  variant = "list",
}: TxIdRowProps) {
  if (variant === "feed") {
    return (
      <li className={`${FEED_ROW} ${className}`} data-testid={testId}>
        <HashLink
          value={txid}
          href={entityHref(network, "tx", txid)}
          ellipsis="end"
          className="min-w-0"
        />
      </li>
    );
  }

  return (
    <li
      className={`flex h-8 items-center justify-between gap-2 ${className}`}
      data-testid={testId}
    >
      <HashLink value={txid} href={entityHref(network, "tx", txid)} />
      <TxKindBadge isHogex={isHogex} hasMweb={hasMweb} />
    </li>
  );
}

export function TxIdRowHeader({ className = "" }: { className?: string }) {
  return (
    <div
      className={`grid h-8 grid-cols-1 items-center border-b border-surface-3 px-2 text-xs text-text-dim ${className}`}
    >
      <span>TxID</span>
    </div>
  );
}
