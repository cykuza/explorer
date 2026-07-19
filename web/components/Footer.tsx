import Link from "next/link";

import pkg from "../package.json";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-surface-3">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-4 text-xs text-text-dim sm:flex-row sm:items-center sm:justify-between">
        <span>Cyberyen Explorer v{pkg.version}</span>
        <nav className="flex flex-wrap gap-4" aria-label="Footer">
          <a
            href="https://github.com/cykuza/explorer"
            className="hover:text-text-mute"
            rel="noopener noreferrer"
            target="_blank"
          >
            GitHub
          </a>
          <Link href="/docs" className="hover:text-text-mute">
            API docs
          </Link>
        </nav>
      </div>
    </footer>
  );
}
