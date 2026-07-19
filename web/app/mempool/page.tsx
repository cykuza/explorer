import type { Metadata } from "next";

import { MempoolView } from "@/components/MempoolView";

export const metadata: Metadata = {
  title: "Mempool",
};

export default function MempoolPage() {
  return <MempoolView />;
}
