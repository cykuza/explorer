import type { Metadata } from "next";

import { ChartsView } from "@/components/ChartsView";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Charts",
};

export default function NetworkChartsPage() {
  return <ChartsView />;
}
