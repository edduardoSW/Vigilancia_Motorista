"use client";

import { useRef } from "react";
import { cn } from "@/lib/utils";

export interface Column<T> {
  id: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  /** Largura CSS da coluna, por exemplo "180px" ou "30%". */
  width?: string;
  align?: "left" | "right";
}

// Tabela densa de programa de computador: cabeçalho grudado no topo, linha de 48 px, hover e linha selecionada.
// ↑/↓ muda a seleção, Enter abre; clicar na linha seleciona e abre.
// K é o tipo do id: texto (motoristas, veículos) ou número (pessoas, atividades).
export function DataTable<T, K extends string | number = string>({
  columns,
  rows,
  getRowId,
  selectedId,
  onSelect,
  onOpen,
  empty,
  label,
}: {
  columns: Column<T>[];
  rows: T[];
  getRowId: (row: T) => K;
  selectedId?: K | null;
  onSelect?: (id: K) => void;
  onOpen?: (row: T) => void;
  empty?: React.ReactNode;
  label?: string;
}) {
  const corpo = useRef<HTMLTableSectionElement>(null);

  function mover(passo: number) {
    if (!rows.length) return;
    const atual = rows.findIndex((row) => getRowId(row) === selectedId);
    const indice = atual === -1 ? (passo > 0 ? 0 : rows.length - 1) : Math.min(rows.length - 1, Math.max(0, atual + passo));
    const id = getRowId(rows[indice]);
    onSelect?.(id);
    corpo.current?.querySelector<HTMLElement>(`[data-row="${CSS.escape(String(id))}"]`)?.scrollIntoView({ block: "nearest" });
  }

  function teclado(event: React.KeyboardEvent) {
    if (event.target instanceof HTMLElement && event.target.closest("input, select, textarea, button, a") && event.target !== event.currentTarget) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      mover(event.key === "ArrowDown" ? 1 : -1);
    } else if (event.key === "Enter") {
      const row = rows.find((item) => getRowId(item) === selectedId);
      if (row) {
        event.preventDefault();
        onOpen?.(row);
      }
    }
  }

  return (
    <div role="grid" aria-label={label} tabIndex={0} onKeyDown={teclado} className="data-table rounded-[2px] focus-visible:outline-offset-4">
      <table className="w-full table-fixed border-collapse text-left text-[14px]">
        <colgroup>
          {columns.map((column) => (
            <col key={column.id} style={column.width ? { width: column.width } : undefined} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.id}
                scope="col"
                className={cn(
                  "sticky top-0 z-10 h-10 border-b border-fio bg-papel px-3 text-[12.5px] font-semibold text-grafite",
                  column.align === "right" && "text-right",
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody ref={corpo}>
          {rows.map((row) => {
            const id = getRowId(row);
            const selecionada = id === selectedId;
            return (
              <tr
                key={id}
                data-row={id}
                aria-selected={selecionada}
                onClick={() => {
                  onSelect?.(id);
                  onOpen?.(row);
                }}
                className={cn(
                  "anim-row h-12 cursor-default border-b border-fio transition-colors",
                  selecionada ? "bg-[#e9efe4]" : "hover:bg-lateral",
                )}
              >
                {columns.map((column, indice) => (
                  <td
                    key={column.id}
                    className={cn(
                      "truncate px-3 py-1.5",
                      column.align === "right" && "text-right",
                      indice === 0 && selecionada && "shadow-[inset_2px_0_0_var(--color-verde)]",
                    )}
                  >
                    {column.cell(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      {!rows.length && <div className="border-b border-fio px-3 py-8 text-[14px] text-grafite">{empty ?? "Nada por aqui."}</div>}
    </div>
  );
}
