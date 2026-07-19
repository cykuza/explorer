export { generateStaticParams } from "@/lib/networkStaticParams";

export default function NetworkLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
