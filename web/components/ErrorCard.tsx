import { Card } from "@/components/Card";
import { ApiError } from "@/lib/api/client";

type ErrorCardProps = {
  error: unknown;
  className?: string;
};

function normalize(error: unknown): { title: string; detail: string; status?: number } {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return {
        title: "Not found",
        detail: error.detail || "The requested resource does not exist.",
        status: 404,
      };
    }
    return {
      title: error.title || `Error ${error.status}`,
      detail: error.detail || error.message,
      status: error.status,
    };
  }
  if (error instanceof Error) {
    return { title: "Error", detail: error.message };
  }
  return { title: "Error", detail: "Something went wrong." };
}

export function ErrorCard({ error, className = "" }: ErrorCardProps) {
  const { title, detail, status } = normalize(error);
  return (
    <Card className={className} role="alert">
      <p className="font-accent text-lg text-text-bright">
        {title}
        {status !== undefined ? (
          <span className="ml-2 text-sm text-text-dim">{status}</span>
        ) : null}
      </p>
      <p className="mt-1 text-sm text-text-mute">{detail}</p>
    </Card>
  );
}
