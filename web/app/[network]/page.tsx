import type { Metadata } from "next";

import { DashboardView } from "@/components/DashboardView";

export { generateStaticParams } from "@/lib/networkStaticParams";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default function NetworkHomePage() {
  return (
    <div>
      <h1 className="mb-4 font-accent text-4xl tracking-tight text-text-bright">
        Dashboard
      </h1>
      <DashboardView />
    </div>
  );
}
