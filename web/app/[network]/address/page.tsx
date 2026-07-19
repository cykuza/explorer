import type { Metadata } from "next";

import { EntityShell } from "@/components/EntityShell";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Address",
};

export default function NetworkAddressPage() {
  return <EntityShell kind="address" />;
}
