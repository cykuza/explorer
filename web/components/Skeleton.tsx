type SkeletonProps = {
  className?: string;
};

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-sm bg-surface-3/60 ${className}`}
      aria-hidden
    />
  );
}

export function SkeletonRow({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`grid h-10 grid-cols-[5rem_4rem_4rem_5rem_1fr] items-center gap-3 border-b border-surface-3/50 px-2 ${className}`}
      aria-hidden
    >
      <Skeleton className="h-4 w-14" />
      <Skeleton className="h-4 w-10" />
      <Skeleton className="h-4 w-10" />
      <Skeleton className="h-4 w-12" />
      <Skeleton className="h-4 w-24" />
    </div>
  );
}

export function SkeletonStat({ className = "" }: SkeletonProps) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden>
      <Skeleton className="h-3 w-16" />
      <Skeleton className="h-6 w-24" />
    </div>
  );
}
