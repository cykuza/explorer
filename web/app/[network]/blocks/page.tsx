import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Blocks",
};

export default function NetworkBlocksPage() {
  return <ComingSoon title="Blocks" />;
}
