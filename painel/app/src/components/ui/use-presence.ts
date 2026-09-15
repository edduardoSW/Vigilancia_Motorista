"use client";

import { useEffect, useRef, useState } from "react";

/** Mantém o elemento na tela durante a animação de saída. Com movimento reduzido a saída é imediata. */
export function usePresence(open: boolean, saidaMs = 160) {
  const [montado, setMontado] = useState(open);
  const [anterior, setAnterior] = useState(open);

  // Abriu: monta já na renderização, sem esperar um efeito.
  if (open !== anterior) {
    setAnterior(open);
    if (open) setMontado(true);
  }

  // Fechou: desmonta depois da animação de saída (na hora, com movimento reduzido).
  useEffect(() => {
    if (open || !montado) return;
    const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = window.setTimeout(() => setMontado(false), reduzido ? 0 : saidaMs);
    return () => window.clearTimeout(timer);
  }, [open, montado, saidaMs]);

  return { montado: montado || open, saindo: montado && !open };
}

/** Esc fecha e o foco volta para onde estava quando a janela abriu. O foco inicial não rola a janela: ela abre do começo. */
export function useEscapeAndFocus(open: boolean, onClose: () => void, alvo: React.RefObject<HTMLElement | null>) {
  const fechar = useRef(onClose);
  useEffect(() => {
    fechar.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const anterior = document.activeElement as HTMLElement | null;
    const primeiro = alvo.current?.querySelector<HTMLElement>("[autofocus], input, select, textarea, button:not([data-close])");
    (primeiro ?? alvo.current)?.focus({ preventScroll: true });
    const tecla = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        fechar.current();
      }
    };
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("keydown", tecla);
      anterior?.focus?.();
    };
  }, [open, alvo]);
}
