import type { Metadata } from "next";

import { BlockView } from "@/components/BlockView";

export const metadata: Metadata = {
  title: "Block",
};

export default function BlockPage() {
  return <BlockView />;
}
