"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

// Abas de texto com contagem e sublinhado de 2 px que desliza até a aba escolhida (no lugar dos filtros em pílula).
export function Tabs({ items, value, onChange, label }: { items: TabItem[]; value: string; onChange: (id: string) => void; label?: string }) {
  const lista = useRef<HTMLDivElement>(null);
  const [barra, setBarra] = useState<{ left: number; width: number } | null>(null);

  useLayoutEffect(() => {
    const medir = () => {
      const ativo = lista.current?.querySelector<HTMLElement>(`[data-tab="${CSS.escape(value)}"]`);
      if (ativo) setBarra({ left: ativo.offsetLeft, width: ativo.offsetWidth });
    };
    medir();
    const observador = new ResizeObserver(medir);
    if (lista.current) observador.observe(lista.current);
    return () => observador.disconnect();
  }, [value, items]);

  function teclado(event: React.KeyboardEvent) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const indice = items.findIndex((item) => item.id === value);
    const proximo = items[(indice + (event.key === "ArrowRight" ? 1 : -1) + items.length) % items.length];
    onChange(proximo.id);
    lista.current?.querySelector<HTMLElement>(`[data-tab="${CSS.escape(proximo.id)}"]`)?.focus();
  }

  return (
    <div ref={lista} role="tablist" aria-label={label} onKeyDown={teclado} className="relative flex gap-6 border-b border-fio">
      {items.map((item) => {
        const ativo = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            data-tab={item.id}
            aria-selected={ativo}
            tabIndex={ativo ? 0 : -1}
            onClick={() => onChange(item.id)}
            className={cn("flex h-10 items-center gap-1.5 text-[14px] font-semibold transition-colors", ativo ? "text-tinta" : "text-grafite hover:text-tinta")}
          >
            {item.label}
            {item.count !== undefined && <span className="count font-medium tabular-nums text-grafite">{item.count}</span>}
          </button>
        );
      })}
      {barra && (
        <span
          aria-hidden="true"
          className="tab-bar absolute -bottom-px left-0 h-[2px] rounded-full bg-verde"
          style={{ width: barra.width, transform: `translateX(${barra.left}px)` }}
        />
      )}
    </div>
  );
}
