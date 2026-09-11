"use client";

import { useSyncExternalStore } from "react";

function assinar(avisar: () => void) {
  const id = window.setInterval(avisar, 15_000);
  return () => window.clearInterval(id);
}

const minutoAtual = () => Math.floor(Date.now() / 60_000);
const semHoraNoServidor = () => null;

/** Minuto atual (epoch em minutos), só no navegador. No servidor é null: a hora do build não vale para o visitante. */
export function useMinuto(): number | null {
  return useSyncExternalStore(assinar, minutoAtual, semHoraNoServidor);
}
