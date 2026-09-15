"use client";

import { useState } from "react";
import type { Configuracoes } from "@/lib/bridge";
import { useSession } from "@/components/session-provider";
import { OPCOES_TEMA } from "@/components/theme-options";
import { Choice } from "@/components/ui/choice";
import { SaveButton } from "@/components/ui/save-button";
import { Section, useSaveSection } from "./section";

// Aparência (spec 016, decisão 8; spec 019, ESC-01): o tema de quem entrou, que muda na hora e fica guardado pela ponte,
// e o texto maior, que vale para todas as pessoas deste computador.
export function AppearanceSection({ config, onSaved }: { config: Configuracoes; onSaved: (config: Configuracoes) => void }) {
  const [textoMaior, setTextoMaior] = useState(config.aparencia.texto_maior);
  const { state, erro, salvar } = useSaveSection(onSaved);
  const { atualizar, preferencias, salvarPreferencias } = useSession();

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    const salvo = await salvar("aparencia", { texto_maior: textoMaior }, textoMaior ? "Texto maior ligado." : "Texto no tamanho normal.");
    if (!salvo) return;
    document.documentElement.toggleAttribute("data-texto-maior", textoMaior);
    await atualizar(); // o estado da sessão passa a trazer o texto maior para as próximas telas
  }

  return (
    <Section title="Aparência" summary="O tema vale só para você. O texto maior vale para todas as pessoas que usam este computador.">
      <fieldset className="border-b border-fio pb-5">
        <legend className="text-[15px] font-semibold">Tema</legend>
        <p className="mt-1 text-[13.5px] text-grafite">Muda na hora e fica guardado para a próxima vez que você entrar. Também dá para trocar no pé do menu.</p>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {OPCOES_TEMA.map((opcao) => (
            <Choice
              key={opcao.valor}
              name="tema"
              value={opcao.valor}
              checked={preferencias.tema === opcao.valor}
              onChange={() => void salvarPreferencias({ tema: opcao.valor })}
              title={opcao.rotulo}
              description={opcao.explicacao}
            />
          ))}
        </div>
      </fieldset>
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
