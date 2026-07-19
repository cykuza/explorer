"use client";

import { useCallback, useEffect, useState } from "react";

import { Card } from "@/components/Card";
import { ErrorCard } from "@/components/ErrorCard";
import { LEGACY_ENDPOINTS } from "@/lib/docs/legacyEndpoints";
import {
  isOpenAPIDocument,
  parseOpenApiDocument,
  type DocsEndpoint,
  type DocsTagGroup,
} from "@/lib/docs/parseOpenApi";

function PathDisplay({ path }: { path: string }) {
  const parts = path.split(/(\{[^}]+\})/g);
  return (
    <span className="font-mono text-sm text-text">
      {parts.map((part, i) =>
        part.startsWith("{") && part.endsWith("}") ? (
          <span key={i} className="text-text-dim">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }, [text]);

  return (
    <button
      type="button"
      onClick={onCopy}
      className="text-xs text-text-dim hover:text-text-mute"
      aria-label={copied ? "Copied" : "Copy to clipboard"}
    >
      {copied ? "copied" : "copy"}
    </button>
  );
}

function EndpointCard({ endpoint }: { endpoint: DocsEndpoint }) {
  return (
    <Card data-testid="docs-endpoint" id={`op-${endpoint.id}`} className="scroll-mt-6">
      <details>
        <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
          <div className="flex flex-wrap items-baseline gap-3">
            <span className="inline-block bg-surface-3 px-2 py-0.5 font-mono text-xs uppercase text-text-bright">
              {endpoint.method}
            </span>
            <PathDisplay path={endpoint.path} />
            {endpoint.summary ? (
              <span className="text-sm text-text-mute">{endpoint.summary}</span>
            ) : null}
          </div>
        </summary>

        <div className="mt-4 space-y-4 border-t border-surface-3 pt-4">
          {endpoint.parameters.length > 0 ? (
            <div>
              <h4 className="mb-2 font-accent text-sm text-text-bright">
                Parameters
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-text-dim">
                      <th className="py-1 pr-3 font-normal">Name</th>
                      <th className="py-1 pr-3 font-normal">In</th>
                      <th className="py-1 pr-3 font-normal">Type</th>
                      <th className="py-1 pr-3 font-normal">Required</th>
                      <th className="py-1 font-normal">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {endpoint.parameters.map((p) => (
                      <tr
                        key={`${p.in}:${p.name}`}
                        className="border-t border-surface-3"
                      >
                        <td className="py-1.5 pr-3 font-mono text-text">
                          {p.name}
                        </td>
                        <td className="py-1.5 pr-3 text-text-mute">{p.in}</td>
                        <td className="py-1.5 pr-3 font-mono text-text-mute">
                          {p.type}
                        </td>
                        <td className="py-1.5 pr-3 text-text-mute">
                          {p.required ? "yes" : "no"}
                        </td>
                        <td className="py-1.5 text-text-dim">{p.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          <div>
            <h4 className="mb-2 font-accent text-sm text-text-bright">
              Response
              {endpoint.responseTitle !== "(untyped)" ? (
                <span className="ml-2 font-mono text-xs font-normal text-text-dim">
                  {endpoint.responseTitle}
                </span>
              ) : null}
            </h4>
            {endpoint.responseFields.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-text-dim">
                      <th className="py-1 pr-3 font-normal">Field</th>
                      <th className="py-1 pr-3 font-normal">Type</th>
                      <th className="py-1 font-normal">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {endpoint.responseFields.map((f) => (
                      <tr
                        key={`${f.depth}:${f.name}`}
                        className="border-t border-surface-3"
                      >
                        <td
                          className="py-1.5 pr-3 font-mono text-text"
                          style={{ paddingLeft: `${f.depth * 12}px` }}
                        >
                          {f.name}
                        </td>
                        <td className="py-1.5 pr-3 font-mono text-text-mute">
                          {f.type}
                        </td>
                        <td className="py-1.5 text-text-dim">{f.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-text-dim">
                No JSON schema for the success response.
              </p>
            )}
            <p className="mt-2 text-xs text-text-dim">
              Errors use{" "}
              <span className="font-mono text-text-mute">
                application/problem+json
              </span>{" "}
              (RFC 7807):{" "}
              <span className="font-mono">{`{ type, title, status, detail }`}</span>.
            </p>
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between gap-2">
              <h4 className="font-accent text-sm text-text-bright">Example</h4>
              <CopyButton text={endpoint.curl} />
            </div>
            <pre className="overflow-x-auto rounded-sm border border-surface-3 bg-bg p-3 font-mono text-xs text-text-mute">
              {endpoint.curl}
            </pre>
          </div>
        </div>
      </details>
    </Card>
  );
}

export function DocsView() {
  const [groups, setGroups] = useState<DocsTagGroup[] | null>(null);
  const [origin, setOrigin] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const base = window.location.origin;
      try {
        const res = await fetch("/api/v1/openapi.json");
        if (!res.ok) {
          throw new Error(`Failed to load OpenAPI schema (${res.status})`);
        }
        const json: unknown = await res.json();
        if (!isOpenAPIDocument(json)) {
          throw new Error("Invalid OpenAPI document");
        }
        if (cancelled) {
          return;
        }
        setOrigin(base);
        setGroups(parseOpenApiDocument(json, base));
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setOrigin(window.location.origin);
          setError(err);
          setGroups(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div data-testid="docs-page" className="lg:grid lg:grid-cols-[13rem_1fr] lg:gap-8">
      <nav
        aria-label="API docs"
        className="mb-6 max-h-[70vh] overflow-y-auto text-xs lg:sticky lg:top-4 lg:mb-0 lg:max-h-[calc(100vh-2rem)]"
      >
        <p className="mb-2 font-accent text-sm text-text-bright">On this page</p>
        <ul className="space-y-1 text-text-dim">
          <li>
            <a href="#intro" className="hover:text-text-mute">
              Introduction
            </a>
          </li>
          {groups?.map((g) => (
            <li key={g.tag} className="pt-2">
              <a
                href={`#tag-${g.tag}`}
                className="font-accent text-text-mute hover:text-text"
              >
                {g.tag}
              </a>
              <ul className="mt-1 space-y-0.5 border-l border-surface-3 pl-2">
                {g.endpoints.map((ep) => (
                  <li key={ep.id}>
                    <a
                      href={`#op-${ep.id}`}
                      className="block truncate hover:text-text-mute"
                      title={ep.path}
                    >
                      <span className="uppercase text-text-dim">
                        {ep.method}
                      </span>{" "}
                      {ep.path.replace(/^\/api\/v1/, "")}
                    </a>
                  </li>
                ))}
              </ul>
            </li>
          ))}
          <li className="pt-2">
            <a href="#legacy" className="hover:text-text-mute">
              Legacy
            </a>
          </li>
        </ul>
      </nav>

      <div className="min-w-0 space-y-8">
        <section id="intro" className="scroll-mt-6 space-y-4">
          <Card>
            <h2 className="font-accent text-xl text-text-bright">Introduction</h2>
            <p className="mt-2 text-sm text-text-mute">
              REST API for Cyberyen Explorer. Schema is loaded from{" "}
              <span className="font-mono text-text">/api/v1/openapi.json</span>.
              Prefer the branded docs here;{" "}
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
              <a
                href="/api/v1/docs"
                className="text-text underline-offset-2 hover:text-text-bright hover:underline"
              >
                interactive (Swagger)
              </a>{" "}
              is also available.
            </p>

            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="text-text-dim">Base URL</dt>
                <dd className="font-mono text-text">
                  {origin || "…"}
                  <span className="text-text-dim">/api/v1</span>
                </dd>
              </div>
              <div>
                <dt className="text-text-dim">Network path parameter</dt>
                <dd className="text-text-mute">
                  Most routes are under{" "}
                  <span className="font-mono text-text">
                    /api/v1/{"{network}"}/...
                  </span>
                  . Allowed values:{" "}
                  <span className="font-mono text-text">mainnet</span>,{" "}
                  <span className="font-mono text-text">testnet</span>
                  {" "}(and{" "}
                  <span className="font-mono text-text">regtest</span> when
                  configured). Unknown networks return 404 problem+json.
                </dd>
              </div>
              <div>
                <dt className="text-text-dim">Amounts</dt>
                <dd className="text-text-mute">
                  Monetary fields are JSON strings with exactly 8 decimal places
                  (never floats), e.g.{" "}
                  <span className="font-mono text-text">
                    &quot;1.50000000&quot;
                  </span>
                  .
                </dd>
              </div>
              <div>
                <dt className="text-text-dim">Errors</dt>
                <dd className="text-text-mute">
                  Failures use RFC 7807{" "}
                  <span className="font-mono text-text">
                    application/problem+json
                  </span>
                  :
                  <pre className="mt-2 overflow-x-auto rounded-sm border border-surface-3 bg-bg p-3 font-mono text-xs text-text-mute">{`{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "…"
}`}</pre>
                </dd>
              </div>
              <div>
                <dt className="text-text-dim">Server-sent events</dt>
                <dd className="text-text-mute">
                  Live tip and mempool updates over SSE (not fully typed in
                  OpenAPI). Events:{" "}
                  <span className="font-mono text-text">tip</span> (
                  <span className="font-mono">
                    {`{height,hash,time}`}
                  </span>
                  ),{" "}
                  <span className="font-mono text-text">mempool</span> (
                  <span className="font-mono">
                    {`{count,vsize}`}
                  </span>
                  ). Heartbeat comments every ~15s.
                  <pre className="mt-2 overflow-x-auto rounded-sm border border-surface-3 bg-bg p-3 font-mono text-xs text-text-mute">{`const es = new EventSource("/api/v1/mainnet/events");
es.addEventListener("tip", (e) => {
  console.log(JSON.parse(e.data));
});
es.addEventListener("mempool", (e) => {
  console.log(JSON.parse(e.data));
});`}</pre>
                </dd>
              </div>
            </dl>
          </Card>
        </section>

        {loading ? (
          <p className="text-sm text-text-dim">Loading OpenAPI schema…</p>
        ) : null}
        {error ? <ErrorCard error={error} /> : null}

        {groups?.map((g) => (
          <section
            key={g.tag}
            id={`tag-${g.tag}`}
            className="scroll-mt-6 space-y-3"
          >
            <h2 className="font-accent text-xl text-text-bright">{g.tag}</h2>
            {g.endpoints.map((ep) => (
              <EndpointCard key={ep.id} endpoint={ep} />
            ))}
          </section>
        ))}

        <section id="legacy" className="scroll-mt-6 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="font-accent text-xl text-text-bright">
              Legacy /api/*
            </h2>
            <span className="bg-surface-3 px-2 py-0.5 font-mono text-xs uppercase text-text-mute">
              deprecated
            </span>
          </div>
          <p className="text-sm text-text-mute">
            Cyberyen.work-compatible adapters on the default network. Prefer v1.
            Many logical errors still return HTTP 200 with an error envelope.
          </p>
          <div className="space-y-2">
            {LEGACY_ENDPOINTS.map((ep) => (
              <Card key={ep.path} tone="2">
                <div className="flex flex-wrap items-baseline gap-3">
                  <span className="inline-block bg-surface-3 px-2 py-0.5 font-mono text-xs uppercase text-text-bright">
                    GET
                  </span>
                  <PathDisplay path={ep.path} />
                  <span className="text-sm text-text-mute">{ep.summary}</span>
                </div>
                <p className="mt-2 font-mono text-xs text-text-dim">
                  {ep.response}
                </p>
              </Card>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
