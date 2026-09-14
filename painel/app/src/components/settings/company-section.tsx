"use client";

import { useState } from "react";
import type { Configuracoes } from "@/lib/bridge";
import { Field } from "@/components/ui/field";
import { SaveButton } from "@/components/ui/save-button";
import { Section, useSaveSection } from "./section";

type Empresa = Configuracoes["empresa"];

const CAMPOS: { id: keyof Empresa; label: string; optional?: boolean; hint?: string }[] = [
  { id: "nome", label: "Nome da empresa", hint: "Aparece no menu e no topo dos relatórios." },
  { id: "razao_social", label: "Razão social", optional: true },
  { id: "cnpj", label: "CNPJ", optional: true },
  { id: "telefone", label: "Telefone", optional: true },
  { id: "endereco", label: "Endereço", optional: true },
];

export function CompanySection({ config, onSaved }: { config: Configuracoes; onSaved: (config: Configuracoes) => void }) {
  const [valores, setValores] = useState<Empresa>(config.empresa);
  const { state, erro, setErro, salvar } = useSaveSection(onSaved);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!valores.nome.trim()) return setErro({ texto: "Escreva o nome da empresa.", campo: "nome" });
    await salvar("empresa", { ...valores, nome: valores.nome.trim() }, "Dados da empresa salvos.");
  }

  return (
    <Section title="Empresa" summary="Os dados que saem no topo dos relatórios impressos.">
      <form className="grid max-w-[560px] gap-5 pt-5" onSubmit={enviar} noValidate>
        {CAMPOS.map((campo) => (
          <Field
            key={campo.id}
            label={campo.label}
            optional={campo.optional}
            hint={campo.hint}
            htmlFor={`empresa-${campo.id}`}
            error={erro?.campo === campo.id ? erro.texto : undefined}
          >
            <input
              id={`empresa-${campo.id}`}
              className="input"
              value={valores[campo.id]}
              onChange={(e) => setValores({ ...valores, [campo.id]: e.target.value })}
            />
          </Field>
        ))}
        {erro && !erro.campo && (
          <p role="alert" className="text-[14px] text-alarme">
            {erro.texto}
          </p>
        )}
        <div>
          <SaveButton state={state}>Salvar</SaveButton>
        </div>
      </form>
    </Section>
  );
}
