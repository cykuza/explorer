import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default function NetworkHomePage() {
  return <ComingSoon title="Dashboard" />;
}
