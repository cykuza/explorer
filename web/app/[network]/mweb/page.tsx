import type { Metadata } from "next";

import { MwebView } from "@/components/MwebView";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "MWEB",
};

export default function NetworkMwebPage() {
  return <MwebView />;
}
