"use client";

import { Hint } from "@/components/Hint";

type TxKindBadgeProps = {
  isHogex?: boolean | null;
  hasMweb?: boolean | null;
  className?: string;
};

const HOGEX_HINT =
  "Hogwarts Extension (HogEx): the L1 transaction that commits this block’s MWEB state (pegs and kernels).";
const MWEB_HINT =
  "Transaction participates in MWEB (for example a peg-in).";

/**
 * Professional chip for MWEB-related txs.
 * HogEx wins over the generic MWEB label — never both.
 */
export function TxKindBadge({
  isHogex = false,
  hasMweb = false,
  className = "",
}: TxKindBadgeProps) {
  const label = isHogex ? "HogEx" : hasMweb ? "MWEB" : null;
  if (!label) {
    return null;
  }
  const hint = isHogex ? HOGEX_HINT : MWEB_HINT;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-sm border border-surface-3 px-1.5 py-0.5 text-xs text-metal ${className}`}
      data-testid={isHogex ? "tx-badge-hogex" : "tx-badge-mweb"}
      aria-label={`${label}. ${hint}`}
    >
      {label}
      <Hint content={hint} label={`About ${label}`} />
    </span>
  );
}
