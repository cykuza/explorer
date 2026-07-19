"use client";

import { useCallback, useState } from "react";

type HashLinkProps = {
  value: string;
  href?: string;
  head?: number;
  tail?: number;
  className?: string;
};

function truncateMiddle(value: string, head: number, tail: number): string {
  if (value.length <= head + tail + 1) {
    return value;
  }
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

export function HashLink({
  value,
  href,
  head = 8,
  tail = 8,
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
    <span className={`inline-flex items-center gap-1.5 font-mono text-sm ${className}`}>
      {href ? (
        <a
          href={href}
          className="text-text-mute underline-offset-2 hover:text-text-bright hover:underline"
          title={value}
        >
          {display}
        </a>
      ) : (
        <span className="text-text-mute" title={value}>
          {display}
        </span>
      )}
      <button
        type="button"
        onClick={onCopy}
        className="text-xs text-text-dim hover:text-text-mute"
        aria-label={copied ? "Copied" : "Copy to clipboard"}
        title={copied ? "Copied" : "Copy"}
      >
        {copied ? "copied" : "copy"}
      </button>
    </span>
  );
}
