import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = {
  title: "Charts",
};

export default function ChartsPage() {
  return <ComingSoon title="Charts" />;
}
