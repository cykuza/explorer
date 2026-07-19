import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Mempool",
};

export default function NetworkMempoolPage() {
  return <ComingSoon title="Mempool" />;
}
