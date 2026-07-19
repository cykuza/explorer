import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = {
  title: "Blocks",
};

export default function BlocksPage() {
  return <ComingSoon title="Blocks" />;
}
