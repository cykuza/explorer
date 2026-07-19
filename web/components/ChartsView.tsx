"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ChartSvg, type ChartSeriesPoint } from "@/components/ChartSvg";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorCard } from "@/components/ErrorCard";
import { Skeleton } from "@/components/Skeleton";
import {
  fetchCharts,
  fetchTip,
  type ChartMetric,
  type ChartPoint,
} from "@/lib/api/client";
import { activeNetworkFromPathname, networkHref } from "@/lib/networks";

const METRICS: { id: ChartMetric; label: string }[] = [
  { id: "difficulty", label: "Difficulty" },
  { id: "tx_count", label: "Tx count" },
  { id: "fees", label: "Fees" },
  { id: "mweb_amount", label: "MWEB amount" },
];

const RANGES = [
  { id: "all", label: "All" },
  { id: "10k", label: "Last 10k" },
  { id: "1k", label: "Last 1k" },
] as const;

type RangeId = (typeof RANGES)[number]["id"];

function parseMetric(raw: string | null): ChartMetric {
  if (
    raw === "difficulty" ||
    raw === "tx_count" ||
    raw === "fees" ||
    raw === "mweb_amount"
  ) {
    return raw;
  }
  return "difficulty";
}

function parseRange(raw: string | null): RangeId {
  if (raw === "all" || raw === "10k" || raw === "1k") {
    return raw;
  }
  return "all";
}

function rangeBounds(tip: number, range: RangeId): { from: number; to: number } {
  const to = Math.max(tip, 0);
  if (range === "1k") {
    return { from: Math.max(0, to - 999), to };
  }
  if (range === "10k") {
    return { from: Math.max(0, to - 9999), to };
  }
  return { from: 0, to };
}

function toSeries(points: ChartPoint[]): ChartSeriesPoint[] {
  return points.map((p) => ({
    height: p.height,
    time: p.time,
    value: Number(p.value),
  }));
}

export function ChartsView() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4" data-testid="charts-loading">
          <Skeleton className="h-8 w-40" />
          <Card>
            <Skeleton className="h-64 w-full" />
          </Card>
        </div>
      }
    >
      <ChartsViewInner />
    </Suspense>
  );
}

function ChartsViewInner() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  const router = useRouter();
  const searchParams = useSearchParams();
  const metric = parseMetric(searchParams.get("metric"));
  const range = parseRange(searchParams.get("range"));

  const [points, setPoints] = useState<ChartSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const setQuery = useCallback(
    (next: { metric?: ChartMetric; range?: RangeId }) => {
      const m = next.metric ?? metric;
      const r = next.range ?? range;
      const base = networkHref(network, "/charts");
      router.replace(`${base}?metric=${m}&range=${r}`, { scroll: false });
    },
    [metric, range, network, router],
  );

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const tip = await fetchTip(network);
      const { from, to } = rangeBounds(tip.height, range);
      const raw = await fetchCharts(network, { metric, from, to });
      setPoints(toSeries(raw));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [network, metric, range]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(id);
  }, [load]);

  const formatValue = useMemo(() => {
    if (metric === "tx_count") {
      return (v: number) => String(Math.round(v));
    }
    if (metric === "fees" || metric === "mweb_amount") {
      return (v: number) => v.toFixed(4);
    }
    return (v: number) => {
      if (Math.abs(v) >= 1000) {
        return v.toExponential(2);
      }
      return v.toPrecision(4);
    };
  }, [metric]);

  if (loading && points.length === 0 && !error) {
    return (
      <div className="space-y-4" data-testid="charts-loading">
        <Skeleton className="h-8 w-40" />
        <Card>
          <Skeleton className="h-64 w-full" />
        </Card>
      </div>
    );
  }

  if (error && points.length === 0) {
    return <ErrorCard error={error} />;
  }

  return (
    <div className="space-y-4" data-testid="charts-page">
      <h1 className="font-accent text-2xl text-text-bright">Charts</h1>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Metric">
          {METRICS.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setQuery({ metric: m.id })}
              className={`border px-2 py-1 text-sm ${
                metric === m.id
                  ? "border-metal text-text-bright"
                  : "border-surface-3 text-text-mute hover:text-text"
              }`}
              aria-pressed={metric === m.id}
            >
              {m.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Range">
          {RANGES.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => setQuery({ range: r.id })}
              className={`border px-2 py-1 text-sm ${
                range === r.id
                  ? "border-metal text-text-bright"
                  : "border-surface-3 text-text-mute hover:text-text"
              }`}
              aria-pressed={range === r.id}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <Card>
        {points.length === 0 ? (
          <EmptyState title="No chart data" detail="Try another metric or range." />
        ) : (
          <ChartSvg points={points} formatValue={formatValue} />
        )}
      </Card>
    </div>
  );
}
