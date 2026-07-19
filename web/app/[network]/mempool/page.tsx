import type { Metadata } from "next";

import { MempoolView } from "@/components/MempoolView";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Mempool",
};

export default function NetworkMempoolPage() {
  return <MempoolView />;
}
