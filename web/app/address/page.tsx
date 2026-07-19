import type { Metadata } from "next";

import { AddressView } from "@/components/AddressView";

export const metadata: Metadata = {
  title: "Address",
};

export default function AddressPage() {
  return <AddressView />;
}
