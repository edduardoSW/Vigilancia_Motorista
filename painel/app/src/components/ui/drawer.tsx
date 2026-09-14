"use client";

import { useRef } from "react";
import { Glyph } from "@/components/ui/glyph";
import { useEscapeAndFocus, usePresence } from "@/components/ui/use-presence";
import { cn } from "@/lib/utils";

// Painel lateral que desliza da direita: ver e editar sem trocar de tela. Esc fecha.
export function Drawer({
  open,
  onClose,
  title,
  summary,
  footer,
  children,
  width = 460,
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  summary?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  width?: number;
}) {
  const painel = useRef<HTMLElement>(null);
  const { montado, saindo } = usePresence(open, 160);
  useEscapeAndFocus(open, onClose, painel);
  if (!montado) return null;

  return (
    <div className="no-print fixed inset-0 z-40">
      <div aria-hidden="true" onClick={onClose} className={cn("absolute inset-0 bg-tinta/10", saindo ? "anim-fade-out" : "anim-fade")} />
      <aside
        ref={painel}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        tabIndex={-1}
        style={{ width: `min(${width}px, 100vw)` }}
        className={cn(
          "absolute inset-y-0 right-0 flex flex-col border-l border-fio bg-white shadow-[-18px_0_40px_-28px_rgb(23_59_48/0.35)] outline-none",
          saindo ? "anim-drawer-out" : "anim-drawer",
        )}
      >
        <header className="flex items-start gap-3 border-b border-fio px-6 pb-4 pt-5">
          <div className="min-w-0 flex-1">
            <h2 className="font-titulo text-[20px] font-semibold leading-tight">{title}</h2>
            {summary && <p className="mt-1 text-[13.5px] text-grafite">{summary}</p>}
          </div>
          <button
            type="button"
            data-close
            onClick={onClose}
            aria-label="Fechar"
            className="-mr-2 grid size-9 place-items-center rounded-[8px] text-grafite transition-colors hover:bg-lateral hover:text-tinta"
          >
            <Glyph name="close" size={18} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && <footer className="flex items-center justify-end gap-2 border-t border-fio px-6 py-4">{footer}</footer>}
      </aside>
    </div>
  );
}
