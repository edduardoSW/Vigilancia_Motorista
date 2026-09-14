"use client";

import { useState } from "react";
import type { Configuracoes } from "@/lib/bridge";
import { SaveButton } from "@/components/ui/save-button";
import { Row, Section, useSaveSection } from "./section";

// Regras da viagem (spec 016, decisão 3): a empresa pode diminuir a direção contínua, nunca passar da lei.
export const MAXIMO_DIRECAO_MIN = 330;
export const MINIMO_DIRECAO_MIN = 60;
export const MENSAGEM_LEI = "O máximo é 5 h 30, pela lei (CTB, art. 67-C)";

export function erroDirecao(total: number) {
  if (!Number.isFinite(total)) return "Escreva as horas e os minutos.";
  if (total > MAXIMO_DIRECAO_MIN) return MENSAGEM_LEI;
  if (total < MINIMO_DIRECAO_MIN) return "O mínimo é 1 h.";
  return null;
}

const textoDuracao = (total: number) => `${Math.floor(total / 60)} h${total % 60 ? ` ${String(total % 60).padStart(2, "0")}` : ""}`;

export function RulesSection({ config, onSaved }: { config: Configuracoes; onSaved: (config: Configuracoes) => void }) {
  const atual = config.regras.direcao_continua_min;
  const [horas, setHoras] = useState(String(Math.floor(atual / 60)));
  const [minutos, setMinutos] = useState(String(atual % 60));
  const { state, erro, setErro, salvar } = useSaveSection(onSaved);

  const total = Number(horas || "0") * 60 + Number(minutos || "0");
  const aviso = erroDirecao(total);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (aviso) return setErro({ texto: aviso, campo: "direcao_continua_min" });
    await salvar("regras", { direcao_continua_min: total }, `Direção contínua: ${textoDuracao(atual)} → ${textoDuracao(total)}.`);
  }

  const mensagem = aviso ?? (erro?.campo === "direcao_continua_min" || !erro?.campo ? erro?.texto : undefined);

  return (
    <Section title="Regras da viagem" summary="Valem para as viagens lidas depois de salvar. As viagens antigas guardam a regra com que foram lidas.">
      <form onSubmit={enviar} noValidate>
        <Row
          label="Direção contínua"
          description="Tempo dirigindo sem pausa até o painel apontar. A empresa pode diminuir, não aumentar."
          htmlFor="direcao-horas"
          error={mensagem}
        >
          <div className="flex items-center gap-2 text-[14px]">
            <input
              id="direcao-horas"
              className="input w-[72px]"
              type="number"
              inputMode="numeric"
              min={1}
              max={5}
              value={horas}
              aria-label="Horas"
              aria-invalid={Boolean(aviso)}
              onChange={(e) => setHoras(e.target.value)}
            />
            <span>h</span>
            <input
              className="input w-[72px]"
              type="number"
              inputMode="numeric"
              min={0}
              max={59}
              step={5}
              value={minutos}
              aria-label="Minutos"
              aria-invalid={Boolean(aviso)}
              onChange={(e) => setMinutos(e.target.value)}
            />
            <span>min</span>
          </div>
        </Row>
        <Row label="Madrugada" description="Horário em que a direção é marcada como madrugada no relatório. Não muda nesta versão.">
          <p className="pt-0.5 text-[15px]">00:00 a 06:59</p>
        </Row>
        <Row label="Descanso" description="Pausa mínima pelo tipo de transporte. Não muda nesta versão.">
          <p className="pt-0.5 text-[15px]">Carga: 30 min a cada 6 h</p>
          <p className="text-[15px]">Passageiros: 30 min a cada 4 h</p>
        </Row>
        <div className="pt-5">
          <SaveButton state={state}>Salvar</SaveButton>
        </div>
      </form>
    </Section>
  );
}
