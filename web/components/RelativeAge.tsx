"use client";

import { useEffect, useState } from "react";

import { formatAge } from "@/lib/formatAge";

type RelativeAgeProps = {
  /** Unix timestamp in seconds. */
  time: number;
  className?: string;
};

export function RelativeAge({ time, className = "" }: RelativeAgeProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <span className={`font-mono tabular-nums text-text-mute ${className}`} title={new Date(time * 1000).toISOString()}>
      {formatAge(time, now)}
    </span>
  );
}
