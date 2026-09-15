"use client";

import { Glyph } from "@/components/ui/glyph";
import type { Visao } from "@/lib/bridge";
import { cn } from "@/lib/utils";

// Botão "Lista | Cards" das telas com lista (spec 019, VIS-01). A escolha fica guardada por pessoa, pela ponte.
export function ViewToggle({ value, onChange, className }: { value: Visao; onChange: (visao: Visao) => void; className?: string }) {
  return (
    <div role="group" aria-label="Mostrar como" className={cn("inline-flex h-10 shrink-0 items-center gap-0.5 rounded-[9px] border border-fio bg-superficie p-0.5", className)}>
      {(["lista", "cards"] as const).map((opcao) => (
        <button
          key={opcao}
          type="button"
          data-visao={opcao}
          aria-pressed={value === opcao}
          onClick={() => onChange(opcao)}
          className={cn(
            "inline-flex h-full items-center gap-1.5 rounded-[7px] px-2.5 text-[13px] font-semibold transition-colors",
            value === opcao ? "bg-selecao text-tinta" : "text-grafite hover:text-tinta",
          )}
        >
          <Glyph name={opcao === "lista" ? "list" : "grid"} size={16} />
          {opcao === "lista" ? "Lista" : "Cards"}
        </button>
      ))}
    </div>
  );
}
