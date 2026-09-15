"use client";

import { useState, type FormEvent } from "react";
import type { SaveState } from "@/components/drivers/driver-form";
import { Choice } from "@/components/ui/choice";
import { Field } from "@/components/ui/field";
import { bridge, type Caixa, type Veiculo } from "@/lib/bridge";
import { normalizarPlaca, validarPlaca } from "@/lib/validators";
import { nomeDoVeiculo, SITUACAO_VEICULO, TIPO_VEICULO, TRANSPORTA } from "./vehicle-labels";

// Formulário do veículo (prévia 6 e spec 015, decisão 4): o mesmo para cadastrar e editar, na janela do veículo
// (spec 019: "Editar" troca os dados por este formulário; "Cancelar" volta para os dados).

interface Campos {
  numero: string;
  placa: string;
  tipo: Veiculo["tipo"];
  transporta: Veiculo["transporta"];
  modelo: string;
  ano: string;
  situacao: Veiculo["situacao"];
  caixa_id: string;
}
type NomeCampo = keyof Campos;
type Erros = Partial<Record<NomeCampo, string>>;

const ORDEM: NomeCampo[] = ["numero", "placa", "tipo", "modelo", "ano", "caixa_id"];

function camposDe(veiculo: Veiculo | null): Campos {
  return {
    numero: veiculo?.numero ?? "",
    placa: veiculo?.placa ?? "",
    tipo: veiculo?.tipo ?? "onibus",
    transporta: veiculo?.transporta ?? "passageiros",
    modelo: veiculo?.modelo ?? "",
    ano: veiculo?.ano ? String(veiculo.ano) : "",
    situacao: veiculo?.situacao ?? "em_uso",
    caixa_id: veiculo?.caixa_id ? String(veiculo.caixa_id) : "",
  };
}

function validar(campos: Campos, outros: Veiculo[]): Erros {
  const erros: Erros = {};
  const numero = campos.numero.trim();
  if (!numero) erros.numero = "Informe o número do veículo.";
  else if (outros.some((outro) => outro.numero === numero)) erros.numero = "Já existe um veículo com este número.";
  const placa = validarPlaca(campos.placa);
  if (placa) erros.placa = placa;
  else if (outros.some((outro) => normalizarPlaca(outro.placa) === normalizarPlaca(campos.placa))) erros.placa = "Já existe um veículo com esta placa.";
  if (campos.ano) {
    const ano = Number(campos.ano);
    if (!/^\d{4}$/.test(campos.ano) || ano < 1980 || ano > new Date().getFullYear() + 1) erros.ano = "Ano inválido. Use 4 números, como 2021.";
  }
  return erros;
}

export function VehicleForm({
  formId,
  veiculo,
  outros,
  caixas,
  readOnly,
  onSaved,
  onStateChange,
}: {
  formId: string;
  veiculo: Veiculo | null;
  outros: Veiculo[];
  caixas: Caixa[];
  readOnly: boolean;
  onSaved: (veiculo: Veiculo) => void;
  onStateChange: (state: SaveState) => void;
}) {
  const [campos, setCampos] = useState(() => camposDe(veiculo));
  const [tocados, setTocados] = useState<Set<NomeCampo>>(() => new Set());
  const [tentou, setTentou] = useState(false);
  const [doServidor, setDoServidor] = useState<Erros>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);

  const locais = validar(campos, outros);
  const erro = (nome: NomeCampo) => doServidor[nome] ?? (tentou || tocados.has(nome) ? locais[nome] : undefined);
  const id = (nome: NomeCampo) => `${formId}-${nome}`;
  // Só as caixas sem veículo (e a que já está neste); caixa bloqueada não entra.
  const livres = caixas.filter((caixa) => caixa.situacao !== "bloqueada" && (caixa.veiculo_id === null || caixa.veiculo_id === veiculo?.id));

  function mudar<K extends NomeCampo>(nome: K, valor: Campos[K]) {
    onStateChange("idle");
    setDoServidor((atual) => ({ ...atual, [nome]: undefined }));
    setCampos((atual) => ({ ...atual, [nome]: valor }));
  }
  const tocar = (nome: NomeCampo) => setTocados((atual) => (atual.has(nome) ? atual : new Set(atual).add(nome)));

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (readOnly) return;
    setTentou(true);
    setErroGeral(null);
    const primeiro = ORDEM.find((nome) => locais[nome]);
    if (primeiro) {
      document.getElementById(id(primeiro))?.focus();
      return;
    }
    onStateChange("saving");
    const resposta = await bridge.veiculo_salvar({
      ...(veiculo ? { id: veiculo.id } : {}),
      numero: campos.numero.trim(),
      placa: normalizarPlaca(campos.placa),
      tipo: campos.tipo,
      transporta: campos.transporta,
      modelo: campos.modelo.trim() || null,
      ano: campos.ano ? Number(campos.ano) : null,
      situacao: campos.situacao,
      caixa_id: campos.caixa_id ? Number(campos.caixa_id) : null,
    });
    if (!resposta.ok) {
      onStateChange("idle");
      const campo = resposta.campo && resposta.campo in campos ? (resposta.campo as NomeCampo) : null;
      if (campo) {
        setDoServidor((atual) => ({ ...atual, [campo]: resposta.erro }));
        document.getElementById(id(campo))?.focus();
      } else {
        setErroGeral(resposta.erro);
      }
      return;
    }
    onStateChange("saved");
    onSaved(resposta.dados);
  }

  return (
    <form id={formId} onSubmit={enviar} noValidate>
      <fieldset disabled={readOnly} className="m-0 grid min-w-0 grid-cols-2 gap-x-4 border-0 p-0">
        <Field
          label="Número do veículo"
          htmlFor={id("numero")}
          hint={campos.numero.trim() ? `Aparece no painel como "${nomeDoVeiculo({ tipo: campos.tipo, numero: campos.numero.trim() })}".` : undefined}
          error={erro("numero")}
        >
          <input
            id={id("numero")}
            className="input"
            value={campos.numero}
            maxLength={10}
            autoFocus
            autoComplete="off"
            onChange={(evento) => mudar("numero", evento.target.value)}
            onBlur={() => tocar("numero")}
            aria-invalid={Boolean(erro("numero"))}
          />
        </Field>
        <Field label="Placa" htmlFor={id("placa")} hint="Placa nova ou antiga." error={erro("placa")}>
          <input
            id={id("placa")}
            className="input"
            value={campos.placa}
            maxLength={8}
            autoComplete="off"
            onChange={(evento) => mudar("placa", evento.target.value.toUpperCase())}
            onBlur={() => tocar("placa")}
            aria-invalid={Boolean(erro("placa"))}
          />
        </Field>
        <Field label="Tipo" htmlFor={id("tipo")}>
          <select id={id("tipo")} className="select" value={campos.tipo} onChange={(evento) => mudar("tipo", evento.target.value as Campos["tipo"])}>
            {Object.entries(TIPO_VEICULO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Marca e modelo" optional htmlFor={id("modelo")} error={erro("modelo")}>
          <input
            id={id("modelo")}
            className="input"
            value={campos.modelo}
            maxLength={60}
            placeholder="Ex.: rodoviário executivo"
            onChange={(evento) => mudar("modelo", evento.target.value)}
          />
        </Field>

        <div className="col-span-2 mb-4">
          <p className="mb-1.5 text-[13.5px] font-semibold">Transporta</p>
          <div className="grid grid-cols-2 gap-3">
            {(Object.keys(TRANSPORTA) as Veiculo["transporta"][]).map((valor) => (
              <Choice
                key={valor}
                name={`${formId}-transporta`}
                value={valor}
                checked={campos.transporta === valor}
                onChange={() => mudar("transporta", valor)}
                title={TRANSPORTA[valor].rotulo}
                description={TRANSPORTA[valor].regra}
              />
            ))}
          </div>
        </div>

        <div className="col-span-2">
          <Field
            label="Caixa instalada"
            htmlFor={id("caixa_id")}
            hint="Só aparecem as caixas da empresa que não estão em outro veículo."
            error={erro("caixa_id")}
          >
            <select id={id("caixa_id")} className="select" value={campos.caixa_id} onChange={(evento) => mudar("caixa_id", evento.target.value)}>
              <option value="">Sem caixa por enquanto</option>
              {livres.map((caixa) => (
                <option key={caixa.id} value={caixa.id}>
                  {caixa.codigo} · {caixa.veiculo_id === veiculo?.id && veiculo ? "instalada neste veículo" : "sem veículo"}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {veiculo && (
          <>
            <Field label="Ano" optional htmlFor={id("ano")} error={erro("ano")}>
              <input
                id={id("ano")}
                className="input"
                inputMode="numeric"
                maxLength={4}
                value={campos.ano}
                onChange={(evento) => mudar("ano", evento.target.value.replace(/\D/g, ""))}
                onBlur={() => tocar("ano")}
                aria-invalid={Boolean(erro("ano"))}
              />
            </Field>
            <Field
              label="Situação"
              htmlFor={id("situacao")}
              hint={campos.situacao === "fora_de_uso" ? "Sai da lista do dia a dia e continua nas viagens antigas." : undefined}
            >
              <select
                id={id("situacao")}
                className="select"
                value={campos.situacao}
                onChange={(evento) => mudar("situacao", evento.target.value as Campos["situacao"])}
              >
                {Object.entries(SITUACAO_VEICULO).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </select>
            </Field>
          </>
        )}

        {erroGeral && (
          <p role="alert" className="col-span-2 text-[13.5px] font-semibold text-alarme">
            {erroGeral}
          </p>
        )}
      </fieldset>
    </form>
  );
}
