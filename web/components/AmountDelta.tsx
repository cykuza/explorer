import { AmountCY } from "@/components/AmountCY";

type AmountDeltaProps = {
  value: number | string;
  className?: string;
  showUnit?: boolean;
};

export function AmountDelta({
  value,
  className = "",
  showUnit = true,
}: AmountDeltaProps) {
  const n = typeof value === "number" ? value : Number(value);
  const positive = Number.isFinite(n) && n >= 0;
  const abs = Number.isFinite(n) ? Math.abs(n) : 0;
  const tone = positive ? "text-metal" : "text-text-dim";

  return (
    <span className={`inline-flex items-baseline gap-0.5 ${tone} ${className}`}>
      <span className="font-mono">{positive ? "+" : "−"}</span>
      <AmountCY value={abs} showUnit={showUnit} className={tone} />
    </span>
  );
}
