import type { Metadata } from "next";

import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = {
  title: "MWEB",
};

export default function MwebPage() {
  return <ComingSoon title="MWEB" />;
}
