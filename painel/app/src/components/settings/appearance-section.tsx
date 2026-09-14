"use client";

import { useState } from "react";
import type { Configuracoes } from "@/lib/bridge";
import { SaveButton } from "@/components/ui/save-button";
import { Section, useSaveSection } from "./section";

// Aparência (spec 016, decisão 8): tema claro e a opção de texto maior.
export function AppearanceSection({ config, onSaved }: { config: Configuracoes; onSaved: (config: Configuracoes) => void }) {
  const [textoMaior, setTextoMaior] = useState(config.aparencia.texto_maior);
  const { state, erro, salvar } = useSaveSection(onSaved);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    const salvo = await salvar("aparencia", { texto_maior: textoMaior }, textoMaior ? "Texto maior ligado." : "Texto no tamanho normal.");
    if (salvo) document.documentElement.toggleAttribute("data-texto-maior", textoMaior);
  }

  return (
    <Section title="Aparência" summary="Vale para todas as pessoas que usam este computador.">
      <form onSubmit={enviar} noValidate>
        <label className="flex cursor-pointer items-start gap-3 border-b border-fio py-5">
          <input type="checkbox" className="mt-1 size-4 accent-verde" checked={textoMaior} onChange={(e) => setTextoMaior(e.target.checked)} />
          <span>
            <span className="block text-[15px] font-semibold">Texto maior</span>
            <span className="mt-1 block text-[13.5px] text-grafite">Aumenta as letras do painel para quem lê melhor assim.</span>
          </span>
        </label>
        {erro && (
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
