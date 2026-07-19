import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = {
  title: "Mempool",
};

export default function MempoolPage() {
  return <ComingSoon title="Mempool" />;
}
