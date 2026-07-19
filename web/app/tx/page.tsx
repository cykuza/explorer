import type { Metadata } from "next";

import { TxView } from "@/components/TxView";

export const metadata: Metadata = {
  title: "Transaction",
};

export default function TxPage() {
  return <TxView />;
}
