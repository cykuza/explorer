import { DashboardView } from "@/components/DashboardView";

export default function HomePage() {
  return (
    <div>
      <h1 className="mb-4 font-accent text-4xl tracking-tight text-text-bright">
        Dashboard
      </h1>
      <DashboardView />
    </div>
  );
}
