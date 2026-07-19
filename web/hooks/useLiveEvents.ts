"use client";

import { useEffect, useRef, useState } from "react";

export type TipEvent = {
  height: number;
  hash: string;
  time: number;
};

export type MempoolEvent = {
  count: number;
  vsize: number;
};

export type LiveEvents = {
  tip: TipEvent | null;
  mempool: MempoolEvent | null;
  connected: boolean;
};

const MIN_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30_000;

function parseJson<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

/**
 * Native EventSource on `/api/v1/{network}/events`.
 * Reconnects with capped exponential backoff (1s → 30s); closes cleanly on unmount.
 */
export function useLiveEvents(
  network: string,
  options?: { enabled?: boolean },
): LiveEvents {
  const enabled = options?.enabled ?? true;
  const [tip, setTip] = useState<TipEvent | null>(null);
  const [mempool, setMempool] = useState<MempoolEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const backoffRef = useRef(MIN_BACKOFF_MS);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    let cancelled = false;

    function clearTimer() {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }

    function closeEs() {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    }

    function scheduleReconnect() {
      if (cancelled) {
        return;
      }
      clearTimer();
      const delay = backoffRef.current;
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
      timerRef.current = setTimeout(connect, delay);
    }

    function connect() {
      if (cancelled) {
        return;
      }
      closeEs();
      const es = new EventSource(`/api/v1/${encodeURIComponent(network)}/events`);
      esRef.current = es;

      es.addEventListener("open", () => {
        if (cancelled) {
          return;
        }
        setConnected(true);
        backoffRef.current = MIN_BACKOFF_MS;
      });

      es.addEventListener("tip", (ev) => {
        if (cancelled || !(ev instanceof MessageEvent)) {
          return;
        }
        const data = parseJson<TipEvent>(String(ev.data));
        if (
          data &&
          typeof data.height === "number" &&
          typeof data.hash === "string" &&
          typeof data.time === "number"
        ) {
          setTip(data);
        }
      });

      es.addEventListener("mempool", (ev) => {
        if (cancelled || !(ev instanceof MessageEvent)) {
          return;
        }
        const data = parseJson<MempoolEvent>(String(ev.data));
        if (
          data &&
          typeof data.count === "number" &&
          typeof data.vsize === "number"
        ) {
          setMempool(data);
        }
      });

      es.onerror = () => {
        if (cancelled) {
          return;
        }
        setConnected(false);
        closeEs();
        scheduleReconnect();
      };
    }

    backoffRef.current = MIN_BACKOFF_MS;
    connect();

    return () => {
      cancelled = true;
      setConnected(false);
      clearTimer();
      closeEs();
    };
  }, [network, enabled]);

  return { tip, mempool, connected };
}
