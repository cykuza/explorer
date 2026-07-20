"use client";

import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

type HintProps = {
  content: string;
  className?: string;
  /** Accessible name for the trigger (default "About"). */
  label?: string;
};

type Anchor = { top: number; left: number };

/**
 * Compact info control: "i" trigger + design-token popover.
 * Safe beside stretch-links (stopPropagation on click; no nested <a>).
 */
export function Hint({ content, className = "", label = "About" }: HintProps) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tipId = useId();
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [anchor, setAnchor] = useState<Anchor | null>(null);

  const measure = useCallback(() => {
    const el = triggerRef.current;
    if (!el) {
      return;
    }
    const r = el.getBoundingClientRect();
    setAnchor({ top: r.bottom + 6, left: r.left + r.width / 2 });
  }, []);

  const show = useCallback(() => {
    measure();
    setOpen(true);
  }, [measure]);

  const hide = useCallback(() => {
    setOpen(false);
    setPinned(false);
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      return;
    }
    measure();
  }, [open, measure]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onScrollOrResize = () => measure();
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [open, measure]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        hide();
        triggerRef.current?.focus();
      }
    };
    const onPointerDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t)) {
        return;
      }
      const tip = document.getElementById(tipId);
      if (tip?.contains(t)) {
        return;
      }
      hide();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open, hide, tipId]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        data-testid="hint-trigger"
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? tipId : undefined}
        className={`inline-flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border border-surface-3 text-[10px] leading-none text-text-dim transition-colors hover:border-text-dim hover:text-text-mute focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-metal ${className}`}
        onMouseEnter={show}
        onMouseLeave={() => {
          if (!pinned) {
            setOpen(false);
          }
        }}
        onFocus={show}
        onBlur={() => {
          if (!pinned) {
            setOpen(false);
          }
        }}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (pinned) {
            hide();
            return;
          }
          measure();
          setPinned(true);
          setOpen(true);
        }}
      >
        i
      </button>
      {open && anchor
        ? createPortal(
            <span
              id={tipId}
              role="tooltip"
              data-testid="hint-tooltip"
              className="pointer-events-none fixed z-50 max-w-[16rem] -translate-x-1/2 rounded-sm border border-surface-3 bg-surface-2 px-2.5 py-1.5 text-left text-xs leading-snug text-text shadow-[0_8px_24px_rgba(0,0,0,0.45)]"
              style={{ top: anchor.top, left: anchor.left }}
            >
              {content}
            </span>,
            document.body,
          )
        : null}
    </>
  );
}
