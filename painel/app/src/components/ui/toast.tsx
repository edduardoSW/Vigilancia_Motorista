"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export interface ToastInput {
  text: string;
  action?: { label: string; onClick: () => void };
}

type ToastFn = (toast: ToastInput) => void;
type ToastApi = ToastFn & { toast: ToastFn };

interface Item extends ToastInput {
  id: number;
}

const ToastContext = createContext<ToastApi | null>(null);

// Aviso curto que sobe no canto de baixo à direita, com "Desfazer" quando fizer sentido. Some sozinho.
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [itens, setItens] = useState<Item[]>([]);

  const tirar = useCallback((id: number) => setItens((lista) => lista.filter((item) => item.id !== id)), []);

  const api = useMemo<ToastApi>(() => {
    // O id sai da própria lista: um número já usado só volta depois que aquele aviso saiu da tela.
    const toast: ToastFn = (entrada) => {
      setItens((lista) => [...lista.slice(-2), { ...entrada, id: (lista.at(-1)?.id ?? 0) + 1 }]);
    };
    return Object.assign(toast, { toast });
  }, []);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div aria-live="polite" role="status" className="no-print pointer-events-none fixed bottom-5 right-5 z-[60] flex w-[360px] flex-col gap-2">
        {itens.map((item) => (
          <ToastRow key={item.id} item={item} onDone={tirar} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastRow({ item, onDone }: { item: Item; onDone: (id: number) => void }) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDone(item.id), item.action ? 7000 : 4500);
    return () => window.clearTimeout(timer);
  }, [item, onDone]);

  return (
    <div className="anim-toast pointer-events-auto flex items-center gap-3 rounded-[10px] border border-fio bg-aviso py-2.5 pl-4 pr-2 text-[14px] text-sobre-aviso shadow-[0_14px_30px_-18px_rgb(0_0_0/0.6)]">
      <span className="min-w-0 flex-1">{item.text}</span>
      {item.action && (
        <button
          type="button"
          onClick={() => {
            item.action?.onClick();
            onDone(item.id);
          }}
          className="h-8 shrink-0 rounded-[7px] px-2.5 text-[13.5px] font-semibold text-lima transition-colors hover:bg-sobre-aviso/10"
        >
          {item.action.label}
        </button>
      )}
    </div>
  );
}

/** `const toast = useToast()` ou `const { toast } = useToast()`; os dois funcionam. */
export function useToast(): ToastApi {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast precisa estar dentro do ToastProvider");
  return context;
}
