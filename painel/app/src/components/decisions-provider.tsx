"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useSession } from "@/components/session-provider";
import { useToast } from "@/components/ui/toast";
import { dados } from "@/content";
import { momentosDaViagem, type ResultadoMomento } from "@/content/moments";
import { bridge, type Decisao } from "@/lib/bridge";

// Decisões sobre os momentos, pela ponte (spec 014, EQP-04): quem entrou decide e o Python grava nome e função.
// Antes de alguém entrar (e no HTML exportado) valem as decisões de demonstração, iguais às que o Python cria.
type Decisions = Record<string, Decisao>;

interface DecisionsContextValue {
  decisions: Decisions;
  /** Momentos com uma chamada à ponte em andamento: os botões deles ficam desligados. */
  pendentes: ReadonlySet<string>;
  decide: (momentId: string, result: ResultadoMomento) => Promise<void>;
  undo: (momentId: string) => Promise<void>;
  toggleCoached: (momentId: string) => Promise<void>;
}

const INITIAL: Decisions = {};
for (const trip of dados.viagens) {
  for (const moment of momentosDaViagem(trip)) {
    if (moment.decisaoInicial) INITIAL[moment.id] = { momento_id: moment.id, ...moment.decisaoInicial, funcao: "administrador" };
  }
}

const DecisionsContext = createContext<DecisionsContextValue | null>(null);

export function DecisionsProvider({ children }: { children: React.ReactNode }) {
  const { usuario } = useSession();
  const { toast } = useToast();
  const [decisions, setDecisions] = useState<Decisions>(INITIAL);
  const [pendentes, setPendentes] = useState<ReadonlySet<string>>(() => new Set());
  const usuarioId = usuario?.id ?? null;

  useEffect(() => {
    if (usuarioId === null) return;
    let vivo = true;
    bridge.decisoes_listar().then((resposta) => {
      if (vivo && resposta.ok) setDecisions(Object.fromEntries(resposta.dados.map((decisao) => [decisao.momento_id, decisao])));
    });
    return () => {
      vivo = false;
    };
  }, [usuarioId]);

  const marcar = (momentId: string, ocupado: boolean) =>
    setPendentes((atual) => {
      const novo = new Set(atual);
      if (ocupado) novo.add(momentId);
      else novo.delete(momentId);
      return novo;
    });

  async function undo(momentId: string) {
    marcar(momentId, true);
    const resposta = await bridge.decisao_desfazer(momentId);
    marcar(momentId, false);
    if (!resposta.ok) return toast({ text: resposta.erro });
    setDecisions((anterior) => {
      const copia = { ...anterior };
      delete copia[momentId];
      return copia;
    });
  }

  async function decide(momentId: string, result: ResultadoMomento) {
    marcar(momentId, true);
    const resposta = await bridge.decisao_registrar(momentId, result);
    marcar(momentId, false);
    if (!resposta.ok) return toast({ text: resposta.erro });
    setDecisions((anterior) => ({ ...anterior, [momentId]: resposta.dados }));
    toast({
      text: result === "confirmado" ? "Momento confirmado" : "Marcado como alarme falso",
      action: { label: "Desfazer", onClick: () => void undo(momentId) },
    });
  }

  async function toggleCoached(momentId: string) {
    const atual = decisions[momentId];
    if (!atual) return;
    marcar(momentId, true);
    const resposta = await bridge.decisao_orientado(momentId, !atual.orientado);
    marcar(momentId, false);
    if (!resposta.ok) return toast({ text: resposta.erro });
    setDecisions((anterior) => ({ ...anterior, [momentId]: resposta.dados }));
  }

  return <DecisionsContext.Provider value={{ decisions, pendentes, decide, undo, toggleCoached }}>{children}</DecisionsContext.Provider>;
}

export function useDecisions() {
  const context = useContext(DecisionsContext);
  if (!context) throw new Error("useDecisions precisa estar dentro do DecisionsProvider");
  return context;
}
