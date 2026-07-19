import type { Metadata } from "next";

import { BlockView } from "@/components/BlockView";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Block",
};

export default function NetworkBlockPage() {
  return <BlockView />;
}
