"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { AmountCY } from "@/components/AmountCY";
import { Card } from "@/components/Card";
import { ChartSvg, type ChartSeriesPoint } from "@/components/ChartSvg";
import { EmptyState } from "@/components/EmptyState";
import { ErrorCard } from "@/components/ErrorCard";
import { HashLink } from "@/components/HashLink";
import { Hint } from "@/components/Hint";
import { Skeleton } from "@/components/Skeleton";
import {
  fetchCharts,
  fetchMwebSummary,
  fetchTip,
  type MwebSummary,
} from "@/lib/api/client";
import {
  activeNetworkFromPathname,
  entityHref,
} from "@/lib/networks";

export function MwebView() {
  const pathname = usePathname() || "/";
  const network = activeNetworkFromPathname(pathname);
  return <MwebViewInner key={network} network={network} />;
}

function MwebViewInner({ network }: { network: string }) {
  const [summary, setSummary] = useState<MwebSummary | null>(null);
  const [series, setSeries] = useState<ChartSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [showAddressHint, setShowAddressHint] = useState(false);

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const [sum, tip] = await Promise.all([
        fetchMwebSummary(network),
        fetchTip(network),
      ]);
      setSummary(sum);
      const from = 0;
      const to = Math.max(tip.height, 0);
      const pts = await fetchCharts(network, {
        metric: "mweb_amount",
        from,
        to,
      });
      setSeries(
        pts.map((p) => ({
          height: p.height,
          time: p.time,
          value: Number(p.value),
        })),
      );
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [network]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(id);
  }, [load]);

  useEffect(() => {
    function syncHash() {
      setShowAddressHint(window.location.hash === "#address");
    }
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  if (loading && !summary) {
    return (
      <div className="space-y-4" data-testid="mweb-loading">
        <Skeleton className="h-8 w-32" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <Skeleton className="h-12 w-full" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error && !summary) {
    return <ErrorCard error={error} />;
  }

  if (!summary) {
    return <EmptyState title="MWEB unavailable" />;
  }

  const latest = summary.latest;

  return (
    <div className="space-y-6" data-testid="mweb-page">
      <h1 className="font-accent text-2xl text-text-bright">MWEB</h1>

      {showAddressHint ? (
        <Card data-testid="mweb-address-hint" className="border-metal/40">
          <h2 className="font-accent text-lg text-text-bright">
            MWEB address lookup
          </h2>
          <p className="mt-2 text-sm text-text-mute">
            Addresses starting with <span className="font-mono">cymweb1</span>{" "}
            or <span className="font-mono">tmweb</span> are confidential MWEB
            destinations. They are not indexed on-chain, so the explorer cannot
            resolve balances or history for them.
          </p>
        </Card>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <div className="flex items-center gap-1.5">
            <p className="text-xs text-text-dim">MWEB amount</p>
            <Hint content="Total coins currently held inside the MWEB protocol." />
          </div>
          <div className="mt-1" data-testid="mweb-amount">
            <AmountCY
              value={summary.mweb_amount}
              className="text-lg text-text-bright"
            />
          </div>
        </Card>
        <Card>
          <p className="text-xs text-text-dim">Activation height</p>
          <a
            href={entityHref(
              network,
              "block",
              String(summary.activation_height),
            )}
            className="mt-1 inline-block font-mono text-lg tabular-nums text-text-bright underline-offset-2 hover:underline"
          >
            {summary.activation_height}
          </a>
        </Card>
        <Card>
          <p className="text-xs text-text-dim">Peg-in (24h)</p>
          <div className="mt-1">
            <AmountCY
              value={summary.pegin_24h}
              className="text-lg text-text-bright"
            />
          </div>
        </Card>
        <Card>
          <p className="text-xs text-text-dim">Peg-out (24h)</p>
          <div className="mt-1">
            <AmountCY
              value={summary.pegout_24h}
              className="text-lg text-text-bright"
            />
          </div>
        </Card>
      </div>

      {latest ? (
        <Card data-testid="mweb-latest">
          <h2 className="mb-3 font-accent text-lg text-text-bright">
            Latest MWEB block
          </h2>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-text-dim">Height</dt>
              <dd>
                <a
                  href={entityHref(network, "block", String(latest.height))}
                  className="font-mono tabular-nums text-text-mute underline-offset-2 hover:underline"
                >
                  {latest.height}
                </a>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-text-dim">Kernels / TXOs</dt>
              <dd className="font-mono tabular-nums">
                {latest.num_kernels} / {latest.num_txos}
              </dd>
            </div>
            <div>
              <dt className="flex items-center gap-1.5 text-xs text-text-dim">
                <span>Amount</span>
                <Hint content="Total coins currently held inside the MWEB protocol." />
              </dt>
              <dd>
                <AmountCY value={latest.mweb_amount} />
              </dd>
            </div>
            {latest.hogex_txid ? (
              <div>
                <dt className="flex items-center gap-1.5 text-xs text-text-dim">
                  <span>HogEx</span>
                  <Hint content="Hogwarts Extension transaction that commits this block’s MWEB state to the transparent chain." />
                </dt>
                <dd>
                  <HashLink
                    value={latest.hogex_txid}
                    href={entityHref(network, "tx", latest.hogex_txid)}
                  />
                </dd>
              </div>
            ) : null}
          </dl>
        </Card>
      ) : (
        <EmptyState
          title="No MWEB blocks yet"
          detail="Waiting for activation and peg activity."
        />
      )}

      <Card>
        <h2 className="mb-3 font-accent text-lg text-text-bright">
          About MWEB confidentiality
        </h2>
        <div className="space-y-3 text-sm text-text-mute">
          <p>
            Mimblewimble Extension Blocks (MWEB) keep transaction amounts and
            addresses inside the extension block confidential. Observing the
            public chain does not reveal who paid whom or how much moved between
            MWEB wallets.
          </p>
          <p>
            Peg-ins and peg-outs bridge value between the transparent chain and
            MWEB, and those bridge amounts are visible. The totals shown on this
            page summarize that observable boundary — not the private graph of
            activity inside MWEB.
          </p>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-accent text-lg text-text-bright">
          MWEB amount over height
        </h2>
        {series.length === 0 ? (
          <EmptyState
            title="No chart data"
            detail="No mweb_amount series in range."
            className="border-0 bg-transparent p-2"
          />
        ) : (
          <ChartSvg
            points={series}
            formatValue={(v) => v.toFixed(4)}
          />
        )}
      </Card>
    </div>
  );
}
