"use client";

import { HashLink } from "@/components/HashLink";
import { TxKindBadge } from "@/components/TxKindBadge";
import { entityHref } from "@/lib/networks";

type TxIdRowProps = {
  txid: string;
  network: string;
  isHogex?: boolean;
  hasMweb?: boolean;
  className?: string;
  /** Optional test id on the row element. */
  testId?: string;
};

/** Dense txid + kind row used on dashboard feed and mempool list. */
export function TxIdRow({
  txid,
  network,
  isHogex = false,
  hasMweb = false,
  className = "",
  testId,
}: TxIdRowProps) {
  return (
    <li
      className={`flex h-8 items-center justify-between gap-2 ${className}`}
      data-testid={testId}
    >
      <HashLink value={txid} href={entityHref(network, "tx", txid)} />
      <TxKindBadge isHogex={isHogex} hasMweb={hasMweb} />
    </li>
  );
}
