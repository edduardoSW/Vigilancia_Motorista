"use client";

import { useEffect, useRef, type RefObject } from "react";

// Atalhos das telas de lista (contrato do painel): Ctrl+N cadastra e "/" vai para a busca.
// Desligado enquanto um painel lateral ou diálogo está aberto, para não abrir um cadastro por cima do outro.
export function useListShortcuts({
  onNew,
  searchRef,
  enabled = true,
}: {
  onNew?: () => void;
  searchRef?: RefObject<HTMLInputElement | null>;
  enabled?: boolean;
}) {
  const novo = useRef(onNew);
  useEffect(() => {
    novo.current = onNew;
  });

  useEffect(() => {
    if (!enabled) return;
    function aoTeclar(evento: KeyboardEvent) {
      const alvo = evento.target as HTMLElement | null;
      const digitando = !!alvo && (alvo.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(alvo.tagName));
      if ((evento.ctrlKey || evento.metaKey) && !evento.shiftKey && !evento.altKey && evento.key.toLowerCase() === "n") {
        if (!novo.current) return;
        evento.preventDefault();
        novo.current();
        return;
      }
      if (evento.key === "/" && !digitando && searchRef?.current) {
        evento.preventDefault();
        searchRef.current.focus();
        searchRef.current.select();
      }
    }
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [enabled, searchRef]);
}

/** "1 viagem", "12 viagens". */
export const plural = (total: number, um: string, varios: string) => `${total} ${total === 1 ? um : varios}`;

/** Compara sem acento e sem diferença de maiúsculas, para a busca. */
export const semAcento = (texto: string) =>
  texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
