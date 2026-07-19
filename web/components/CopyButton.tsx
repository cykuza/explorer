"use client";

import { useCallback, useState } from "react";

type CopyButtonProps = {
  text: string;
  className?: string;
};

function ClipboardIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 16 16"
      width={14}
      height={14}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={className}
    >
      <rect x="5.5" y="1.75" width="8" height="10.5" rx="1.25" />
      <path d="M3.25 4.25H2.75A1.5 1.5 0 0 0 1.25 5.75v7.5A1.5 1.5 0 0 0 2.75 14.75h7.5a1.5 1.5 0 0 0 1.5-1.5v-.5" />
    </svg>
  );
}

function CheckIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 16 16"
      width={14}
      height={14}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={className}
    >
      <path d="M3.5 8.5 6.5 11.5 12.5 4.5" />
    </svg>
  );
}

/** Compact clipboard control; label lives in aria/title only. */
export function CopyButton({ text, className = "" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }, [text]);

  return (
    <button
      type="button"
      onClick={onCopy}
      className={`inline-flex shrink-0 items-center justify-center rounded-sm p-0.5 text-text-dim transition-colors hover:bg-surface-3/50 hover:text-text-mute ${
        copied ? "text-metal" : ""
      } ${className}`}
      aria-label={copied ? "Copied" : "Copy to clipboard"}
      title={copied ? "Copied" : "Copy"}
    >
      {copied ? <CheckIcon /> : <ClipboardIcon />}
    </button>
  );
}
