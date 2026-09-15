"use client";

import { cn } from "@/lib/utils";

// Cards das telas com lista (spec 019, VIS-01): os mesmos itens, na mesma ordem e com o mesmo filtro da tabela.
// Clicar no card abre a janela do item. Card: nome grande, identificação, situação em frase e poucas informações.
export function CardGrid<T, K extends string | number = string>({
  items,
  getId,
  selectedId,
  onSelect,
  onOpen,
  renderCard,
  empty,
  label,
  minWidth = 264,
}: {
  items: T[];
  getId: (item: T) => K;
  selectedId?: K | null;
  onSelect?: (id: K) => void;
  onOpen?: (item: T) => void;
  renderCard: (item: T) => React.ReactNode;
  empty?: React.ReactNode;
  label?: string;
  /** Largura mínima de cada card, em px. */
  minWidth?: number;
}) {
  if (!items.length) {
    return <div className="rounded-[12px] border border-dashed border-fio px-4 py-8 text-[14px] text-grafite">{empty ?? "Nada por aqui."}</div>;
  }
  return (
    <ul aria-label={label} className="card-grid grid gap-3" style={{ gridTemplateColumns: `repeat(auto-fill, minmax(min(${minWidth}px, 100%), 1fr))` }}>
      {items.map((item) => {
        const id = getId(item);
        const selecionado = id === selectedId;
        return (
          <li key={id} className="min-w-0">
            <button
              type="button"
              data-card={id}
              aria-current={selecionado || undefined}
              onClick={() => {
                onSelect?.(id);
                onOpen?.(item);
              }}
              className={cn(
                "anim-row flex h-full w-full min-w-0 flex-col items-stretch gap-3 rounded-[12px] border bg-superficie p-4 text-left transition-colors",
                selecionado ? "border-verde" : "border-fio hover:border-tinta/30",
              )}
            >
              {renderCard(item)}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** Topo do card: nome grande, a identificação logo abaixo e, à direita, algo curto (situação ou contagem). */
export function CardTitulo({ titulo, detalhe, extra }: { titulo: React.ReactNode; detalhe?: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <span className="flex w-full min-w-0 items-start justify-between gap-3">
      <span className="min-w-0">
        <b className="block truncate text-[16px] font-semibold leading-snug">{titulo}</b>
        {detalhe && <span className="block truncate text-[13px] text-grafite">{detalhe}</span>}
      </span>
      {extra && <span className="shrink-0">{extra}</span>}
    </span>
  );
}

/** Uma linha do card: rótulo à esquerda e valor à direita; em vermelho só quando pede ação. */
export function CardInfo({ rotulo, children, alarme = false }: { rotulo: string; children: React.ReactNode; alarme?: boolean }) {
  return (
    <span className="flex w-full min-w-0 items-baseline justify-between gap-3 text-[13px]">
      <span className="shrink-0 text-grafite">{rotulo}</span>
      <span className={cn("min-w-0 truncate text-right", alarme && "font-semibold text-alarme")}>{children}</span>
    </span>
  );
}
