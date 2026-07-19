type AmountCYProps = {
  /** Amount in CY (not sats). Accepts number or numeric string. */
  value: number | string;
  className?: string;
  showUnit?: boolean;
  /** Short form for dense lists (e.g. 508.95M). Full precision in title. */
  compact?: boolean;
};

function parseCy(value: number | string): number {
  return typeof value === "number" ? value : Number(value);
}

function formatCyFull(value: number | string): string {
  const n = parseCy(value);
  if (!Number.isFinite(n)) {
    return "0.00000000";
  }
  return n.toFixed(8);
}

function formatCyCompact(value: number | string): string {
  const n = parseCy(value);
  if (!Number.isFinite(n)) {
    return "0";
  }
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toFixed(2)}M`;
  }
  if (abs >= 10_000) {
    return `${sign}${(abs / 1_000).toFixed(1)}k`;
  }
  if (abs >= 100) {
    return `${sign}${abs.toFixed(0)}`;
  }
  if (abs >= 1) {
    return `${sign}${abs.toFixed(2)}`;
  }
  if (abs === 0) {
    return "0";
  }
  return n.toPrecision(3);
}

export function AmountCY({
  value,
  className = "",
  showUnit = true,
  compact = false,
}: AmountCYProps) {
  const display = compact ? formatCyCompact(value) : formatCyFull(value);
  const title = compact ? `${formatCyFull(value)} CY` : undefined;
  return (
    <span className={`font-mono tabular-nums ${className}`} title={title}>
      {display}
      {showUnit ? (
        <span className="ml-1 text-text-dim">CY</span>
      ) : null}
    </span>
  );
}
