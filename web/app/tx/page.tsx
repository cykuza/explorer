import type { Metadata } from "next";

import { EntityShell } from "@/components/EntityShell";

export const metadata: Metadata = {
  title: "Transaction",
};

export default function TxPage() {
  return <EntityShell kind="tx" />;
}
