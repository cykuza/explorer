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
      className={`grid h-auto min-h-10 grid-cols-[4.5rem_3.25rem_2.5rem_minmax(0,1fr)] items-center gap-2 border-b border-surface-3/50 px-2 py-1.5 sm:h-10 sm:grid-cols-[5.5rem_4rem_4rem_5.5rem_minmax(0,1fr)] sm:gap-3 sm:py-0 ${className}`}
      aria-hidden
    >
      <Skeleton className="h-4 w-14" />
      <Skeleton className="h-4 w-10" />
      <Skeleton className="h-4 w-8" />
      <Skeleton className="hidden h-4 w-12 sm:block" />
      <Skeleton className="ml-auto h-4 w-20 sm:w-24" />
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
