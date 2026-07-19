import { Card } from "@/components/Card";

type ComingSoonProps = {
  title: string;
  detail?: string;
};

export function ComingSoon({ title, detail }: ComingSoonProps) {
  return (
    <Card>
      <h1 className="font-accent text-2xl text-text-bright">{title}</h1>
      <p className="mt-2 text-sm text-text-mute">
        {detail ?? "Coming soon."}
      </p>
    </Card>
  );
}
