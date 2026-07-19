import { Card } from "@/components/Card";

type EmptyStateProps = {
  title: string;
  detail?: string;
  className?: string;
};

export function EmptyState({ title, detail, className = "" }: EmptyStateProps) {
  return (
    <Card className={className}>
      <p className="font-accent text-lg text-text-mute">{title}</p>
      {detail ? <p className="mt-1 text-sm text-text-dim">{detail}</p> : null}
    </Card>
  );
}
