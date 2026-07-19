/** Property names that are monetary amounts encoded as 8-decimal strings. */
const MONETARY_STRING_FIELDS = new Set([
  "balance",
  "received",
  "sent",
  "fee",
  "fees",
  "total_fee",
  "total_out",
  "value",
  "delta",
  "mweb_amount",
  "pegin",
  "pegout",
  "kernel_fees",
  "pegin_24h",
  "pegout_24h",
  "difficulty",
  "amount",
]);

export function isMonetaryStringField(name: string, typeLabel: string): boolean {
  const leaf = name.includes(".") ? name.slice(name.lastIndexOf(".") + 1) : name;
  const base = leaf.endsWith("[]") ? leaf.slice(0, -2) : leaf;
  if (!MONETARY_STRING_FIELDS.has(base)) {
    return false;
  }
  return typeLabel === "string" || typeLabel.startsWith("string");
}

export function annotateType(name: string, typeLabel: string): string {
  if (isMonetaryStringField(name, typeLabel)) {
    return "string (8 dp)";
  }
  return typeLabel;
}
