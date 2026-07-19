import type { Metadata } from "next";

import { EntityShell } from "@/components/EntityShell";

export const metadata: Metadata = {
  title: "Address",
};

export default function AddressPage() {
  return <EntityShell kind="address" />;
}
