"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  type Acao,
  bridge,
  type Estado,
  podeFazer,
  PREFERENCIAS_PADRAO,
  type Preferencias,
  type PreferenciasEntrada,
  type TelaComVisao,
  type Usuario,
  type Visao,
} from "@/lib/bridge";

// Quem entrou e o que pode fazer. O estado vem sempre da ponte; nada fica guardado no navegador (ENT-07).
// Spec 019: as preferências (tema e lista ou cards) também vêm da ponte, por pessoa.
interface SessionValue {
  estado: Estado | null;
  usuario: Usuario | null;
  pode: (acao: Acao) => boolean;
  atualizar: () => Promise<void>;
  sair: () => Promise<void>;
  /** Frase simples quando nem o estado inicial pôde ser lido. */
  falha: string | null;
  /** As da pessoa que entrou; sem sessão, as padrão. */
  preferencias: Preferencias;
  salvarPreferencias: (valores: PreferenciasEntrada) => Promise<void>;
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

  // A tela troca na hora; se a ponte recusar, o estado volta como estava.
  const salvarPreferencias = useCallback(
    async (valores: PreferenciasEntrada) => {
      setEstado((atual) =>
        atual?.preferencias
          ? {
              ...atual,
              tema: valores.tema ?? atual.tema,
              preferencias: { tema: valores.tema ?? atual.preferencias.tema, visao: { ...atual.preferencias.visao, ...valores.visao } },
            }
          : atual,
      );
      const resposta = await bridge.preferencias_salvar(valores);
      if (!resposta.ok) await atualizar();
    },
    [atualizar],
  );

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
  const preferencias = estado?.preferencias ?? PREFERENCIAS_PADRAO;
  const value = useMemo<SessionValue>(
    () => ({ estado, usuario, pode: (acao) => podeFazer(usuario?.funcao, acao), atualizar, sair, falha, preferencias, salvarPreferencias }),
    [estado, usuario, atualizar, sair, falha, preferencias, salvarPreferencias],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession precisa estar dentro do SessionProvider");
  return context;
}

/** Lista ou cards de uma tela, guardado por pessoa (spec 019, VIS-02). */
export function useVisao(tela: TelaComVisao): [Visao, (visao: Visao) => void] {
  const { preferencias, salvarPreferencias } = useSession();
  return [preferencias.visao[tela], (visao) => void salvarPreferencias({ visao: { [tela]: visao } })];
}
