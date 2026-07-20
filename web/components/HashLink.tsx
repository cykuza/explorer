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
  /**
   * middle — fixed head+tail with … in the center (default).
   * end — full value with CSS end ellipsis (width-adaptive).
   */
  ellipsis?: "middle" | "end";
  className?: string;
};

export function HashLink({
  value,
  href,
  head = HASH_DISPLAY_HEAD,
  tail = HASH_DISPLAY_TAIL,
  ellipsis = "middle",
  className = "",
}: HashLinkProps) {
  const end = ellipsis === "end";
  const display = end ? value : truncateMiddle(value, head, tail);
  const textClass = end
    ? "min-w-0 truncate text-text-mute underline-offset-2 hover:text-text-bright hover:underline"
    : "whitespace-nowrap text-text-mute underline-offset-2 hover:text-text-bright hover:underline";
  const spanTextClass = end
    ? "min-w-0 truncate text-text-mute"
    : "whitespace-nowrap text-text-mute";

  return (
    <span
      className={`inline-flex max-w-full items-center gap-1 font-mono text-sm ${
        end ? "min-w-0" : "shrink-0 whitespace-nowrap"
      } ${className}`}
    >
      {href ? (
        <a href={href} className={textClass} title={value}>
          {display}
        </a>
      ) : (
        <span className={spanTextClass} title={value}>
          {display}
        </span>
      )}
      <CopyButton text={value} />
    </span>
  );
}
