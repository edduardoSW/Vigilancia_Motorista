"use client";

import { useRef } from "react";
import { cn } from "@/lib/utils";

const ALTURA = 40;

// Lista lateral com indicador que desliza até o item escolhido (Configurações e Guia). ↑/↓ troca o item.
export function SideList<T extends string>({
  label,
  items,
  value,
  onChange,
}: {
  label: string;
  items: { id: T; label: string; prefix?: string }[];
  value: T;
  onChange: (id: T) => void;
}) {
  const lista = useRef<HTMLUListElement>(null);
  const indice = Math.max(0, items.findIndex((item) => item.id === value));

  function aoTeclar(evento: React.KeyboardEvent) {
    if (evento.key !== "ArrowDown" && evento.key !== "ArrowUp") return;
    evento.preventDefault();
    const proximo = Math.min(items.length - 1, Math.max(0, indice + (evento.key === "ArrowDown" ? 1 : -1)));
    onChange(items[proximo].id);
    lista.current?.querySelectorAll("button")[proximo]?.focus();
  }

  return (
    <nav aria-label={label} className="relative" onKeyDown={aoTeclar}>
      <span
        aria-hidden="true"
        className="absolute inset-x-0 top-0 rounded-[8px] border-l-2 border-verde bg-superficie shadow-[0_1px_2px_rgb(0_0_0/0.06)] transition-transform duration-200 ease-[cubic-bezier(.2,.8,.2,1)]"
        style={{ height: ALTURA, transform: `translateY(${indice * ALTURA}px)` }}
      />
      <ul ref={lista} className="relative">
        {items.map((item) => {
          const ativo = item.id === value;
          return (
            <li key={item.id}>
              <button
                type="button"
                aria-current={ativo ? "true" : undefined}
                onClick={() => onChange(item.id)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-[8px] px-3 text-left text-[14px] transition-colors",
                  ativo ? "font-semibold" : "text-grafite hover:text-tinta",
                )}
                style={{ height: ALTURA }}
              >
                {item.prefix && <span className="w-5 text-[13px] font-normal text-grafite">{item.prefix}</span>}
                <span className="truncate">{item.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
