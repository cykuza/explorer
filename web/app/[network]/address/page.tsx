import type { Metadata } from "next";

import { AddressView } from "@/components/AddressView";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Address",
};

export default function NetworkAddressPage() {
  return <AddressView />;
}
