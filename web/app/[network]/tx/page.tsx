import type { Metadata } from "next";

import { TxView } from "@/components/TxView";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Transaction",
};

export default function NetworkTxPage() {
  return <TxView />;
}
