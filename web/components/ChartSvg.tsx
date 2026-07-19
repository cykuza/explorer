"use client";

import {
  useCallback,
  useId,
  useMemo,
  useState,
  type MouseEvent,
} from "react";

export type ChartSeriesPoint = {
  height: number;
  time: number;
  value: number;
};

type ChartSvgProps = {
  points: ChartSeriesPoint[];
  className?: string;
  formatValue?: (value: number) => string;
};

const PAD = { top: 12, right: 12, bottom: 28, left: 56 };
const WIDTH = 720;
const HEIGHT = 280;

function formatTick(n: number): string {
  if (!Number.isFinite(n)) {
    return "—";
  }
  const abs = Math.abs(n);
  if (abs >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(2)}M`;
  }
  if (abs >= 10_000) {
    return `${(n / 1_000).toFixed(1)}k`;
  }
  if (abs >= 100) {
    return n.toFixed(0);
  }
  if (abs >= 1) {
    return n.toFixed(2);
  }
  return n.toPrecision(3);
}

export function ChartSvg({
  points,
  className = "",
  formatValue = formatTick,
}: ChartSvgProps) {
  const gradId = useId().replace(/:/g, "");
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const layout = useMemo(() => {
    if (points.length === 0) {
      return null;
    }
    const xs = points.map((p) => p.height);
    const ys = points.map((p) => p.value);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const spanX = Math.max(maxX - minX, 1);
    const spanY = Math.max(maxY - minY, Number.EPSILON);
    const innerW = WIDTH - PAD.left - PAD.right;
    const innerH = HEIGHT - PAD.top - PAD.bottom;

    const coords = points.map((p) => {
      const x = PAD.left + ((p.height - minX) / spanX) * innerW;
      const y = PAD.top + (1 - (p.value - minY) / spanY) * innerH;
      return { x, y, ...p };
    });

    const line = coords
      .map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(2)},${c.y.toFixed(2)}`)
      .join(" ");
    const first = coords[0]!;
    const last = coords[coords.length - 1]!;
    const area = `${line} L${last.x.toFixed(2)},${(PAD.top + innerH).toFixed(2)} L${first.x.toFixed(2)},${(PAD.top + innerH).toFixed(2)} Z`;

    const yTicks = [minY, minY + spanY / 2, maxY];
    const xTicks = [minX, Math.round(minX + spanX / 2), maxX];

    return { coords, line, area, yTicks, xTicks, minX, maxX, minY, maxY, spanY, innerW, innerH };
  }, [points]);

  const onMove = useCallback(
    (e: MouseEvent<SVGSVGElement>) => {
      if (!layout || layout.coords.length === 0) {
        return;
      }
      const rect = e.currentTarget.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * WIDTH;
      let best = 0;
      let bestDist = Infinity;
      for (let i = 0; i < layout.coords.length; i++) {
        const d = Math.abs(layout.coords[i]!.x - x);
        if (d < bestDist) {
          bestDist = d;
          best = i;
        }
      }
      setHoverIdx(best);
    },
    [layout],
  );

  if (!layout) {
    return (
      <div
        className={`flex h-64 items-center justify-center text-sm text-text-dim ${className}`}
        data-testid="chart-empty"
      >
        No data for this range
      </div>
    );
  }

  const hover = hoverIdx != null ? layout.coords[hoverIdx] : null;

  return (
    <div className={`relative ${className}`}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-auto w-full"
        role="img"
        aria-label="Chart"
        onMouseMove={onMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#b8bec6" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#b8bec6" stopOpacity="0" />
          </linearGradient>
        </defs>

        {layout.yTicks.map((v, i) => {
          const y =
            PAD.top +
            (1 - (v - layout.minY) / Math.max(layout.spanY, Number.EPSILON)) *
              layout.innerH;
          return (
            <g key={`y-${i}`}>
              <line
                x1={PAD.left}
                x2={WIDTH - PAD.right}
                y1={y}
                y2={y}
                stroke="#3c3c3c"
                strokeWidth={1}
              />
              <text
                x={PAD.left - 8}
                y={y + 3}
                textAnchor="end"
                fill="#6d6d6d"
                fontSize={10}
                fontFamily="ui-monospace, monospace"
              >
                {formatValue(v)}
              </text>
            </g>
          );
        })}

        {layout.xTicks.map((h, i) => {
          const x =
            PAD.left +
            ((h - layout.minX) / Math.max(layout.maxX - layout.minX, 1)) *
              layout.innerW;
          return (
            <text
              key={`x-${i}`}
              x={x}
              y={HEIGHT - 8}
              textAnchor="middle"
              fill="#6d6d6d"
              fontSize={10}
              fontFamily="ui-monospace, monospace"
            >
              {h}
            </text>
          );
        })}

        <path d={layout.area} fill={`url(#${gradId})`} />
        <path
          d={layout.line}
          fill="none"
          stroke="#b1b1b1"
          strokeWidth={1.5}
          data-testid="chart-path"
        />

        {hover ? (
          <>
            <line
              x1={hover.x}
              x2={hover.x}
              y1={PAD.top}
              y2={PAD.top + layout.innerH}
              stroke="#6d6d6d"
              strokeDasharray="3 3"
            />
            <circle cx={hover.x} cy={hover.y} r={3.5} fill="#fff" />
          </>
        ) : null}
      </svg>

      {hover ? (
        <div
          className="pointer-events-none absolute top-2 right-2 border border-surface-3 bg-surface-2 px-2 py-1 font-mono text-xs text-text"
          data-testid="chart-tooltip"
        >
          <div>h {hover.height}</div>
          <div>{new Date(hover.time * 1000).toISOString().slice(0, 19)}Z</div>
          <div>{formatValue(hover.value)}</div>
        </div>
      ) : null}
    </div>
  );
}
