"use client";

import { CopyButton } from "@/components/CopyButton";
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
  const display = truncateMiddle(value, head, tail);

  return (
    <span
      className={`inline-flex max-w-full shrink-0 items-center gap-1 whitespace-nowrap font-mono text-sm ${className}`}
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
      <CopyButton text={value} />
    </span>
  );
}
