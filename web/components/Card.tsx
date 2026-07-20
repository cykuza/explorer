import type { HTMLAttributes, ReactNode } from "react";

type CardBaseProps = {
  children: ReactNode;
  tone?: "1" | "2";
  className?: string;
};

type CardDivProps = CardBaseProps &
  Omit<HTMLAttributes<HTMLDivElement>, "children" | "className"> & {
    href?: undefined;
  };

type CardAnchorProps = CardBaseProps &
  Omit<HTMLAttributes<HTMLAnchorElement>, "children" | "className"> & {
    href: string;
  };

export type CardProps = CardDivProps | CardAnchorProps;

export function Card({
  children,
  tone = "1",
  className = "",
  href,
  ...rest
}: CardProps) {
  const bg = tone === "1" ? "bg-surface-1" : "bg-surface-2";
  const classes = `rounded-sm border border-surface-3 ${bg} p-4 ${className}`;
  if (href) {
    return (
      <a
        href={href}
        className={`block transition-colors hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-metal ${classes}`}
        {...(rest as Omit<
          HTMLAttributes<HTMLAnchorElement>,
          "children" | "className" | "href"
        >)}
      >
        {children}
      </a>
    );
  }
  return (
    <div
      className={classes}
      {...(rest as Omit<HTMLAttributes<HTMLDivElement>, "children" | "className">)}
    >
      {children}
    </div>
  );
}
