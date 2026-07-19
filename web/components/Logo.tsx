import Link from "next/link";

const LOGO_PATH =
  "M385 127v25h25v51h51v-51h-25v-50h-51v25m203 0v25h-25v51h51v-51h25v-50h-51v25M410 254v17h-33v34h-34v34h-34v270h34v34h34v34h33v34h204v-34h33v-34h34v-34h34v-67h-68v33h-33v34h-34v34H444v-34h-34v-34h-33V372h33v-33h34v-34h136v34h34v33h33v34h68v-67h-34v-34h-34v-34h-33v-34H410v17m0 503.5V770h76v51h-76v25h75.976l.262 38.25.262 38.25h51l.262-38.25.262-38.25H614v-25h-76v-51h76v-25H410v12.5";

type LogoProps = {
  href?: string;
  className?: string;
};

export function Logo({ href = "/", className = "" }: LogoProps) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2 text-text-bright ${className}`}
      aria-label="Cyberyen Explorer home"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 1024 1024"
        width={36}
        height={36}
        aria-hidden="true"
        className="shrink-0"
      >
        <path fill="#6D6D6D" d={LOGO_PATH} />
      </svg>
      <span className="font-accent text-xl tracking-tight">Explorer</span>
    </Link>
  );
}
