"use client";

import { useState } from "react";
import type { Configuracoes } from "@/lib/bridge";
import { useSession } from "@/components/session-provider";
import { SaveButton } from "@/components/ui/save-button";
import { Row, Section, useSaveSection } from "./section";

// Acesso (spec 014, decisão 7): minutos sem uso até bloquear a tela, de 5 a 60.
export function AccessSection({ config, onSaved }: { config: Configuracoes; onSaved: (config: Configuracoes) => void }) {
  const { atualizar } = useSession();
  const [minutos, setMinutos] = useState(String(config.acesso.bloqueio_min));
  const { state, erro, setErro, salvar } = useSaveSection(onSaved);
  const total = Number(minutos);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!Number.isInteger(total) || total < 5 || total > 60) return setErro({ texto: "Escolha de 5 a 60 minutos.", campo: "bloqueio_min" });
    if (await salvar("acesso", { bloqueio_min: total }, `A tela bloqueia depois de ${total} min sem uso.`)) await atualizar();
  }

  return (
    <Section title="Acesso" summary="Quem sair de perto do computador não deixa o painel aberto para outra pessoa.">
      <form onSubmit={enviar} noValidate>
        <Row
          label="Bloquear a tela depois de"
          description="Tempo sem mexer no painel. Para voltar, a pessoa digita a senha dela e continua na mesma tela."
          htmlFor="acesso-minutos"
          error={erro?.texto}
        >
          <div className="flex items-center gap-2 text-[14px]">
            <input
              id="acesso-minutos"
              className="input w-[88px]"
              type="number"
              inputMode="numeric"
              min={5}
              max={60}
              value={minutos}
              onChange={(e) => setMinutos(e.target.value)}
            />
            <span>minutos</span>
          </div>
        </Row>
        <div className="pt-5">
          <SaveButton state={state}>Salvar</SaveButton>
        </div>
      </form>
    </Section>
  );
}
