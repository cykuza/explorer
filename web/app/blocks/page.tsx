import type { Metadata } from "next";

import { BlocksView } from "@/components/BlocksView";

export const metadata: Metadata = {
  title: "Blocks",
};

export default function BlocksPage() {
  return <BlocksView />;
}
