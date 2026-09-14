"use client";

import { createContext, useContext, useState } from "react";
import { dados, isoLocal } from "@/content";
import { type Decisao, momentosDaViagem, type ResultadoMomento } from "@/content/moments";

// Decisões sobre os momentos, compartilhadas entre a lista de viagens e o relatório. Na prévia ficam só na memória.
type Decisions = Record<string, Decisao>;

interface DecisionsContextValue {
  decisions: Decisions;
  decide: (momentId: string, result: ResultadoMomento) => void;
  undo: (momentId: string) => void;
  toggleCoached: (momentId: string) => void;
}

const INITIAL: Decisions = Object.fromEntries(
  dados.viagens.flatMap((trip) =>
    momentosDaViagem(trip)
      .filter((moment) => moment.decisaoInicial)
      .map((moment) => [moment.id, moment.decisaoInicial as Decisao]),
  ),
);

const DecisionsContext = createContext<DecisionsContextValue | null>(null);

export function DecisionsProvider({ children }: { children: React.ReactNode }) {
  const [decisions, setDecisions] = useState<Decisions>(INITIAL);

  const value: DecisionsContextValue = {
    decisions,
    decide: (momentId, result) =>
      setDecisions((previous) => ({
        ...previous,
        [momentId]: { resultado: result, orientado: false, por: "Você", em: isoLocal(new Date()) },
      })),
    undo: (momentId) =>
      setDecisions((previous) => {
        const copy = { ...previous };
        delete copy[momentId];
        return copy;
      }),
    toggleCoached: (momentId) =>
      setDecisions((previous) =>
        previous[momentId] ? { ...previous, [momentId]: { ...previous[momentId], orientado: !previous[momentId].orientado } } : previous,
      ),
  };

  return <DecisionsContext.Provider value={value}>{children}</DecisionsContext.Provider>;
}

export function useDecisions() {
  const context = useContext(DecisionsContext);
  if (!context) throw new Error("useDecisions precisa estar dentro do DecisionsProvider");
  return context;
}
