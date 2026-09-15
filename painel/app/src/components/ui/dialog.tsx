"use client";

import { useRef } from "react";
import { Glyph } from "@/components/ui/glyph";
import { Camada } from "@/components/ui/layer";
import { useEscapeAndFocus, usePresence } from "@/components/ui/use-presence";
import { cn } from "@/lib/utils";

// Janela no centro da tela (spec 019, MOD-01): o resto da janela fica desfocado e escurecido; cresce de 0,98 para 1.
// Cabeçalho com título e Fechar, corpo que rola por dentro e rodapé sempre visível. Esc ou clique fora fecham.
// Todo cadastrar, ver e editar usa esta janela; o painel lateral deixou de existir.
export function Dialog({
  open,
  onClose,
  title,
  summary,
  footer,
  children,
  width = 520,
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
    <Camada>
      <div className="no-print fixed inset-0 z-50 grid place-items-center p-6">
        <div aria-hidden="true" onClick={onClose} className={cn("veu absolute inset-0", saindo ? "anim-fade-out" : "anim-fade")} />
        <div
          ref={caixa}
          role="dialog"
          aria-modal="true"
          aria-label={typeof title === "string" ? title : undefined}
          tabIndex={-1}
          style={{ width: `min(${width}px, 100%)` }}
          className={cn(
            "janela relative flex max-h-[calc(var(--altura-janela)-48px)] flex-col overflow-hidden rounded-[14px] border border-fio bg-elevada shadow-[0_24px_60px_-30px_rgb(0_0_0/0.45)] outline-none",
            saindo ? "anim-dialog-out" : "anim-dialog",
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
              className="-mr-2 grid size-9 shrink-0 place-items-center rounded-[8px] text-grafite transition-colors hover:bg-lateral hover:text-tinta"
            >
              <Glyph name="close" size={18} />
            </button>
          </header>
          {children && <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>}
          {footer && <footer className="flex items-center justify-end gap-2 border-t border-fio px-6 py-4">{footer}</footer>}
        </div>
      </div>
    </Camada>
  );
}
