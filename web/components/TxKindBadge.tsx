type TxKindBadgeProps = {
  isHogex?: boolean | null;
  hasMweb?: boolean | null;
  className?: string;
};

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
  return (
    <span
      className={`rounded-sm border border-surface-3 px-1.5 py-0.5 text-xs text-metal ${className}`}
      data-testid={isHogex ? "tx-badge-hogex" : "tx-badge-mweb"}
    >
      {label}
    </span>
  );
}
