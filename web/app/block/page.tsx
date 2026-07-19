import type { Metadata } from "next";

import { EntityShell } from "@/components/EntityShell";

export const metadata: Metadata = {
  title: "Block",
};

export default function BlockPage() {
  return <EntityShell kind="block" />;
}
