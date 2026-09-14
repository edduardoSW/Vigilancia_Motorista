"use client";

import { useRef } from "react";
import { useEscapeAndFocus, usePresence } from "@/components/ui/use-presence";
import { cn } from "@/lib/utils";

// Diálogo central que cresce de 0,98 para 1. Esc ou clicar fora fecha.
export function Dialog({
  open,
  onClose,
  title,
  summary,
  footer,
  children,
  width = 480,
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  summary?: React.ReactNode;
  footer?: React.ReactNode;
  children?: React.ReactNode;
  width?: number;
}) {
  const caixa = useRef<HTMLDivElement>(null);
  const { montado, saindo } = usePresence(open, 140);
  useEscapeAndFocus(open, onClose, caixa);
  if (!montado) return null;

  return (
    <div className="no-print fixed inset-0 z-50 grid place-items-center p-6">
      <div aria-hidden="true" onClick={onClose} className={cn("absolute inset-0 bg-tinta/35", saindo ? "anim-fade-out" : "anim-fade")} />
      <div
        ref={caixa}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        tabIndex={-1}
        style={{ width: `min(${width}px, 100%)` }}
        className={cn(
          "relative max-h-[calc(100vh-48px)] overflow-y-auto rounded-[14px] border border-fio bg-white shadow-[0_24px_60px_-30px_rgb(23_59_48/0.45)] outline-none",
          saindo ? "anim-dialog-out" : "anim-dialog",
        )}
      >
        <div className="px-6 pb-2 pt-5">
          <h2 className="font-titulo text-[20px] font-semibold leading-tight">{title}</h2>
          {summary && <p className="mt-1 text-[14px] text-grafite">{summary}</p>}
        </div>
        {children && <div className="px-6 py-3">{children}</div>}
        {footer && <div className="flex items-center justify-end gap-2 px-6 pb-5 pt-3">{footer}</div>}
      </div>
    </div>
  );
}
