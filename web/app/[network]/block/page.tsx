import type { Metadata } from "next";

import { EntityShell } from "@/components/EntityShell";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Block",
};

export default function NetworkBlockPage() {
  return <EntityShell kind="block" />;
}
