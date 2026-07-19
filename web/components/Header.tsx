import { LagIndicator } from "@/components/LagIndicator";
import { Logo } from "@/components/Logo";
import { NetworkSwitcher } from "@/components/NetworkSwitcher";
import { SearchBar } from "@/components/SearchBar";

export function Header() {
  return (
    <header className="border-b border-surface-3 bg-bg">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:gap-4">
        <Logo />
        <SearchBar />
        <div className="flex shrink-0 items-center justify-between gap-3 sm:justify-end">
          <NetworkSwitcher />
          <LagIndicator />
        </div>
      </div>
    </header>
  );
}
