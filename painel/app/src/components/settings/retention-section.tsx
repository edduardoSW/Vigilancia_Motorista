"use client";

import Link from "next/link";
import { useState } from "react";
import type { Configuracoes } from "@/lib/bridge";
import { SaveButton } from "@/components/ui/save-button";
import { Row, Section, useSaveSection } from "./section";

type Guarda = Configuracoes["guarda"];

// Opções da spec 016, decisão 4 (padrões 30 dias, 5 anos e 5 anos).
const DIAS_VIDEO: Guarda["videos_dias"][] = [7, 15, 30, 60, 90];
const ANOS: Guarda["registros_anos"][] = [1, 2, 5];
const anos = (total: number) => `${total} ${total === 1 ? "ano" : "anos"}`;

export function RetentionSection({ config, onSaved }: { config: Configuracoes; onSaved: (config: Configuracoes) => void }) {
  const [valores, setValores] = useState<Guarda>(config.guarda);
  const { state, erro, salvar } = useSaveSection(onSaved);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    await salvar("guarda", valores, "Prazos de guarda salvos.");
  }

  const erroDo = (campo: keyof Guarda) => (erro?.campo === campo ? erro.texto : undefined);

  return (
    <Section title="Vídeos e guarda dos dados" summary="Depois do prazo, o painel apaga sozinho e anota o que apagou.">
      <form onSubmit={enviar} noValidate>
        <Row
          label="Vídeos curtos"
          description="Contados a partir do dia em que a caixa foi lida. O relatório da viagem continua depois que o vídeo é apagado."
          htmlFor="guarda-videos"
          error={erroDo("videos_dias")}
        >
          <select
            id="guarda-videos"
            className="select w-full"
            value={valores.videos_dias}
            onChange={(e) => setValores({ ...valores, videos_dias: Number(e.target.value) as Guarda["videos_dias"] })}
          >
            {DIAS_VIDEO.map((dias) => (
              <option key={dias} value={dias}>
                {dias} dias
              </option>
            ))}
          </select>
        </Row>
        <Row
          label="Registro das viagens e decisões"
          description="O que a caixa registrou e o que a equipe decidiu em cada momento."
          htmlFor="guarda-registros"
          error={erroDo("registros_anos")}
        >
          <select
            id="guarda-registros"
            className="select w-full"
            value={valores.registros_anos}
            onChange={(e) => setValores({ ...valores, registros_anos: Number(e.target.value) as Guarda["registros_anos"] })}
          >
            {ANOS.map((total) => (
              <option key={total} value={total}>
                {anos(total)}
              </option>
            ))}
          </select>
        </Row>
        <Row
          label="Dados de motorista desligado"
          description="Nome, CNH, telefone e CPF. Depois do prazo, as viagens antigas ficam com “Motorista desligado” no lugar do nome."
          htmlFor="guarda-desligados"
          error={erroDo("desligados_anos")}
        >
          <select
            id="guarda-desligados"
            className="select w-full"
            value={valores.desligados_anos}
            onChange={(e) => setValores({ ...valores, desligados_anos: Number(e.target.value) as Guarda["desligados_anos"] })}
          >
            {ANOS.map((total) => (
              <option key={total} value={total}>
                {anos(total)} depois de sair
              </option>
            ))}
          </select>
        </Row>
        <Row label="Quem pode ver os vídeos" description="Vem da função de cada pessoa, na área Equipe.">
          <p className="text-[15px]">Administrador e Supervisor</p>
          <Link href="/equipe/" className="text-[13.5px] font-semibold text-verde hover:underline">
            Ver as funções
          </Link>
        </Row>
        {erro && !erro.campo && (
          <p role="alert" className="pt-4 text-[14px] text-alarme">
            {erro.texto}
          </p>
        )}
        <div className="pt-5">
          <SaveButton state={state}>Salvar</SaveButton>
        </div>
      </form>
    </Section>
  );
}
