import type { Metadata } from "next";

import { EntityShell } from "@/components/EntityShell";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Transaction",
};

export default function NetworkTxPage() {
  return <EntityShell kind="tx" />;
}
