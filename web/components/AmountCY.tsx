type AmountCYProps = {
  /** Amount in CY (not sats). Accepts number or numeric string. */
  value: number | string;
  className?: string;
  showUnit?: boolean;
};

function formatCy(value: number | string): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) {
    return "0.00000000";
  }
  return n.toFixed(8);
}

export function AmountCY({
  value,
  className = "",
  showUnit = true,
}: AmountCYProps) {
  return (
    <span className={`font-mono tabular-nums ${className}`}>
      {formatCy(value)}
      {showUnit ? (
        <span className="ml-1 text-text-dim">CY</span>
      ) : null}
    </span>
  );
}
