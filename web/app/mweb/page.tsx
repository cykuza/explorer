import type { Metadata } from "next";

import { MwebView } from "@/components/MwebView";

export const metadata: Metadata = {
  title: "MWEB",
};

export default function MwebPage() {
  return <MwebView />;
}
