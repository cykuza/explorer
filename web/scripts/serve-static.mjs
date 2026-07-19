#!/usr/bin/env node
/**
 * Serve Next static export (`out/`) with API + pretty-entity rewrites for Lighthouse.
 * No extra deps — Node http only. Usage: node scripts/serve-static.mjs [port]
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "out");
const PORT = Number(process.argv[2] || 4173);
const API = process.env.API_UPSTREAM || "http://127.0.0.1:8080";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".ico": "image/x-icon",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
};

function mapEntityPath(urlPath) {
  const entity = urlPath.match(
    /^\/(?:(mainnet|testnet|regtest)\/)?(block|tx|address)\/[^/]+\/?$/,
  );
  if (!entity) {
    return null;
  }
  const network = entity[1];
  const kind = entity[2];
  if (network) {
    return `/${network}/${kind}.html`;
  }
  return `/${kind}.html`;
}

function resolveFile(urlPath) {
  const mapped = mapEntityPath(urlPath);
  const candidate = mapped || urlPath;
  const clean = candidate.split("?")[0] || "/";
  if (clean === "/") {
    return path.join(OUT, "index.html");
  }
  const asFile = path.join(OUT, clean.replace(/^\//, ""));
  if (fs.existsSync(asFile) && fs.statSync(asFile).isFile()) {
    return asFile;
  }
  const withHtml = `${asFile}.html`;
  if (fs.existsSync(withHtml)) {
    return withHtml;
  }
  const index = path.join(asFile, "index.html");
  if (fs.existsSync(index)) {
    return index;
  }
  return null;
}

async function proxy(req, res, targetBase) {
  const url = new URL(req.url || "/", `http://${req.headers.host}`);
  const upstream = `${targetBase}${url.pathname}${url.search}`;
  const headers = { ...req.headers, host: new URL(targetBase).host };
  delete headers["content-length"];
  const init = {
    method: req.method,
    headers,
    duplex: "half",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = req;
  }
  const upstreamRes = await fetch(upstream, init);
  res.writeHead(upstreamRes.status, Object.fromEntries(upstreamRes.headers));
  if (upstreamRes.body) {
    const reader = upstreamRes.body.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      res.write(value);
    }
  }
  res.end();
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${req.headers.host}`);
    if (url.pathname.startsWith("/api/") || url.pathname === "/healthz") {
      await proxy(req, res, API);
      return;
    }
    const file = resolveFile(url.pathname);
    if (!file) {
      res.writeHead(404, { "content-type": "text/plain" });
      res.end("Not found");
      return;
    }
    const ext = path.extname(file);
    res.writeHead(200, { "content-type": MIME[ext] || "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  } catch (err) {
    res.writeHead(502, { "content-type": "text/plain" });
    res.end(String(err));
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`static+proxy http://127.0.0.1:${PORT} (out=${OUT} api=${API})`);
});
