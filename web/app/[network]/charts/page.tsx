import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Charts",
};

export default function NetworkChartsPage() {
  return <ComingSoon title="Charts" />;
}
