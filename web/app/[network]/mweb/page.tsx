import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "MWEB",
};

export default function NetworkMwebPage() {
  return <ComingSoon title="MWEB" />;
}
