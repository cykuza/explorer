import type { HTMLAttributes, ReactNode } from "react";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  tone?: "1" | "2";
};

export function Card({
  children,
  tone = "1",
  className = "",
  ...rest
}: CardProps) {
  const bg = tone === "1" ? "bg-surface-1" : "bg-surface-2";
  return (
    <div
      className={`rounded-sm border border-surface-3 ${bg} p-4 ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
