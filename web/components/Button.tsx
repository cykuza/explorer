import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
};

export function Button({
  children,
  className = "",
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center border border-surface-3 px-3 py-1.5 text-sm text-text-bright transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      style={{
        backgroundImage: "linear-gradient(27deg, #3d3d3d, #252525)",
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
