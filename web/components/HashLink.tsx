"use client";

import { useCallback, useState } from "react";

import {
  HASH_DISPLAY_HEAD,
  HASH_DISPLAY_TAIL,
  truncateMiddle,
} from "@/lib/truncateMiddle";

type HashLinkProps = {
  value: string;
  href?: string;
  /** Leading chars kept when truncating (default 4 — mobile-safe one line). */
  head?: number;
  /** Trailing chars kept when truncating (default 4). */
  tail?: number;
  className?: string;
};

export function HashLink({
  value,
  href,
  head = HASH_DISPLAY_HEAD,
  tail = HASH_DISPLAY_TAIL,
  className = "",
}: HashLinkProps) {
  const [copied, setCopied] = useState(false);
  const display = truncateMiddle(value, head, tail);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }, [value]);

  return (
    <span
      className={`inline-flex max-w-full shrink-0 items-center gap-1.5 whitespace-nowrap font-mono text-sm ${className}`}
    >
      {href ? (
        <a
          href={href}
          className="whitespace-nowrap text-text-mute underline-offset-2 hover:text-text-bright hover:underline"
          title={value}
        >
          {display}
        </a>
      ) : (
        <span className="whitespace-nowrap text-text-mute" title={value}>
          {display}
        </span>
      )}
      <button
        type="button"
        onClick={onCopy}
        className="shrink-0 text-xs text-text-dim hover:text-text-mute"
        aria-label={copied ? "Copied" : "Copy to clipboard"}
        title={copied ? "Copied" : "Copy"}
      >
        {copied ? "copied" : "copy"}
      </button>
    </span>
  );
}
