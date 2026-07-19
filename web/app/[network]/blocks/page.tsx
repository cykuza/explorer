import type { Metadata } from "next";

import { BlocksView } from "@/components/BlocksView";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Blocks",
};

export default function NetworkBlocksPage() {
  return <BlocksView />;
}
