import { NETWORKS } from "@/lib/networks";

/** Static params for `app/[network]/…` (all configured networks). */
export function generateStaticParams() {
  return NETWORKS.map((network) => ({ network }));
}
