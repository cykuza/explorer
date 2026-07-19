import type { Metadata } from "next";

import { DocsView } from "@/components/DocsView";

export const metadata: Metadata = {
  title: "API",
};

export default function DocsPage() {
  return (
    <div>
      <h1 className="mb-4 font-accent text-4xl tracking-tight text-text-bright">
        API
      </h1>
      <DocsView />
    </div>
  );
}
