"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { type Acao, bridge, type Estado, podeFazer, type Usuario } from "@/lib/bridge";

// Quem entrou e o que pode fazer. O estado vem sempre da ponte; nada fica guardado no navegador (ENT-07).
interface SessionValue {
  estado: Estado | null;
  usuario: Usuario | null;
  pode: (acao: Acao) => boolean;
  atualizar: () => Promise<void>;
  sair: () => Promise<void>;
  /** Frase simples quando nem o estado inicial pôde ser lido. */
  falha: string | null;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [falha, setFalha] = useState<string | null>(null);

  const atualizar = useCallback(async () => {
    const resposta = await bridge.estado();
    if (resposta.ok) {
      setEstado(resposta.dados);
      setFalha(null);
    } else {
      setFalha(resposta.erro);
    }
  }, []);

  const sair = useCallback(async () => {
    await bridge.sair();
    await atualizar();
  }, [atualizar]);

  useEffect(() => {
    let vivo = true;
    bridge.estado().then((resposta) => {
      if (!vivo) return;
      if (resposta.ok) setEstado(resposta.dados);
      else setFalha(resposta.erro);
    });
    return () => {
      vivo = false;
    };
  }, []);

  const usuario = estado?.sessao ?? null;
  const value = useMemo<SessionValue>(
    () => ({ estado, usuario, pode: (acao) => podeFazer(usuario?.funcao, acao), atualizar, sair, falha }),
    [estado, usuario, atualizar, sair, falha],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession precisa estar dentro do SessionProvider");
  return context;
}
