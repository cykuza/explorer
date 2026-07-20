"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { usePathname, useRouter } from "next/navigation";

import {
  NETWORKS,
  activeNetworkFromPathname,
  networkHref,
  parsePathname,
} from "@/lib/networks";

const CONTROL =
  "h-9 border border-surface-3 bg-surface-1 font-mono text-sm leading-none text-text";

export function NetworkSwitcher() {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const current = activeNetworkFromPathname(pathname);
  const parsed = parsePathname(pathname);

  const listId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const currentIndex = Math.max(0, NETWORKS.indexOf(current));
  const [activeIndex, setActiveIndex] = useState(currentIndex);

  function switchTo(next: string) {
    setOpen(false);
    if (next === current) {
      return;
    }
    const sectionPath =
      parsed.section === null
        ? "/"
        : parsed.id
          ? `/${parsed.section}/${parsed.id}`
          : `/${parsed.section}`;
    router.push(networkHref(next, sectionPath));
  }

  function openMenu() {
    setActiveIndex(currentIndex);
    setOpen(true);
  }

  useEffect(() => {
    if (!open) {
      return;
    }
    listRef.current?.focus();

    function onPointerDown(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: globalThis.KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (NETWORKS.length <= 1) {
    return (
      <span
        className={`inline-flex items-center px-3 ${CONTROL} text-text-dim`}
      >
        {current}
      </span>
    );
  }

  function onTriggerKeyDown(e: KeyboardEvent<HTMLButtonElement>) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) {
        openMenu();
        return;
      }
      setActiveIndex((i) => {
        if (e.key === "ArrowDown") {
          return Math.min(NETWORKS.length - 1, i + 1);
        }
        return Math.max(0, i - 1);
      });
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (open) {
        const next = NETWORKS[activeIndex];
        if (next) {
          switchTo(next);
        }
      } else {
        openMenu();
      }
    }
  }

  function onListKeyDown(e: KeyboardEvent<HTMLUListElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(NETWORKS.length - 1, i + 1));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
      return;
    }
    if (e.key === "Home") {
      e.preventDefault();
      setActiveIndex(0);
      return;
    }
    if (e.key === "End") {
      e.preventDefault();
      setActiveIndex(NETWORKS.length - 1);
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      const next = NETWORKS[activeIndex];
      if (next) {
        switchTo(next);
      }
    }
  }

  const activeId = `${listId}-opt-${activeIndex}`;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        id={`${listId}-trigger`}
        className={`inline-flex w-full min-w-[7.5rem] items-center justify-between gap-2 px-3 ${CONTROL} focus:border-text-dim focus:outline-none`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label="Network"
        onClick={() => {
          if (open) {
            setOpen(false);
          } else {
            openMenu();
          }
        }}
        onKeyDown={onTriggerKeyDown}
      >
        <span>{current}</span>
        <svg
          width="10"
          height="6"
          viewBox="0 0 10 6"
          aria-hidden="true"
          className={`shrink-0 text-text-dim transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path
            d="M1 1l4 4 4-4"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
          />
        </svg>
      </button>

      {open ? (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          aria-labelledby={`${listId}-trigger`}
          aria-activedescendant={activeId}
          tabIndex={-1}
          className="absolute top-full right-0 left-0 z-50 -mt-px border border-surface-3 bg-surface-1 focus:outline-none"
          onKeyDown={onListKeyDown}
        >
          {NETWORKS.map((n, i) => {
            const selected = n === current;
            const active = i === activeIndex;
            return (
              <li
                key={n}
                id={`${listId}-opt-${i}`}
                role="option"
                aria-selected={selected}
                className={`flex cursor-pointer items-center justify-between px-3 py-2 font-mono text-sm leading-none ${
                  active ? "bg-surface-2" : ""
                } ${selected ? "text-text-bright" : "text-text"}`}
                onMouseEnter={() => setActiveIndex(i)}
                onClick={() => switchTo(n)}
              >
                <span>{n}</span>
                {selected ? (
                  <span className="text-text-dim" aria-hidden="true">
                    ✓
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
