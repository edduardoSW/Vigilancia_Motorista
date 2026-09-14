"use client";

import { useState } from "react";
import type { SaveState } from "@/components/drivers/driver-form";
import { Drawer } from "@/components/ui/drawer";
import { Field } from "@/components/ui/field";
import { SaveButton } from "@/components/ui/save-button";
import { bridge, type Caixa, type Veiculo } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { nomeDoVeiculo, quando, SITUACAO_CAIXA } from "./vehicle-labels";

// Caixa (spec 015, decisão 5): o painel não cria caixa; só mostra a situação e vincula ou troca de veículo.
// Trocar guarda o histórico no Python: as viagens antigas continuam com o veículo de antes (CXA-02).

export function BoxDrawer({
  caixa,
  caixas,
  veiculos,
  readOnly,
  onClose,
  onLinked,
}: {
  caixa: Caixa | null;
  caixas: Caixa[];
  veiculos: Veiculo[];
  readOnly: boolean;
  onClose: () => void;
  onLinked: (caixa: Caixa, veiculoAnterior: number | null) => void;
}) {
  const atual = caixa?.veiculo_id ? String(caixa.veiculo_id) : "";
  const [paraCaixa, setParaCaixa] = useState<number | null>(caixa?.id ?? null);
  const [destino, setDestino] = useState(atual);
  const [estado, setEstado] = useState<SaveState>("idle");
  const [erro, setErro] = useState<string | null>(null);

  // Outra caixa aberta: começa de novo com o veículo dela.
  if ((caixa?.id ?? null) !== paraCaixa) {
    setParaCaixa(caixa?.id ?? null);
    setDestino(atual);
    setEstado("idle");
    setErro(null);
  }

  const bloqueada = caixa?.situacao === "bloqueada";
  const veiculoAtual = veiculos.find((veiculo) => veiculo.id === caixa?.veiculo_id);
  const veiculoDestino = veiculos.find((veiculo) => String(veiculo.id) === destino);
  const codigo = (id: number | null) => caixas.find((item) => item.id === id)?.codigo;
  const opcoes = veiculos.filter((veiculo) => veiculo.situacao !== "fora_de_uso" || veiculo.id === caixa?.veiculo_id);
  const outraCaixa = veiculoDestino?.caixa_id && veiculoDestino.caixa_id !== caixa?.id ? codigo(veiculoDestino.caixa_id) : undefined;

  async function vincular() {
    if (!caixa || readOnly || bloqueada || destino === atual) return;
    setEstado("saving");
    setErro(null);
    const anterior = caixa.veiculo_id;
    const resposta = await bridge.caixa_vincular(caixa.id, destino ? Number(destino) : null);
    if (!resposta.ok) {
      setEstado("idle");
      setErro(resposta.erro);
      return;
    }
    setEstado("saved");
    onLinked(resposta.dados, anterior);
  }

  return (
    <Drawer
      open={Boolean(caixa)}
      onClose={onClose}
      title={caixa ? `Caixa ${caixa.codigo}` : ""}
      summary={caixa ? (veiculoAtual ? `Instalada no veículo ${veiculoAtual.numero}` : "Sem veículo") : undefined}
      footer={
        readOnly || bloqueada ? (
          <button type="button" className="btn" onClick={onClose}>
            Fechar
          </button>
        ) : (
          <>
            <SaveButton state={estado} type="button" onClick={vincular} disabled={destino === atual && estado !== "saved"}>
              Salvar troca
            </SaveButton>
            <button type="button" className="btn" onClick={onClose}>
              Cancelar
            </button>
          </>
        )
      }
    >
      {caixa && (
        <>
          <dl className="grid grid-cols-[130px_minmax(0,1fr)] gap-y-2 border-b border-fio pb-5 text-[13.5px]">
            <dt className="text-grafite">Situação</dt>
            <dd>
              <span className={cn("block", caixa.situacao !== "ok" && "font-semibold text-alarme")}>{SITUACAO_CAIXA[caixa.situacao]}</span>
              {caixa.detalhe && <span className="block text-grafite">{caixa.detalhe}</span>}
            </dd>
            <dt className="text-grafite">Última coleta</dt>
            <dd>{quando(caixa.ultima_coleta) ?? "Nunca coletada"}</dd>
            <dt className="text-grafite">Versão do programa</dt>
            <dd>{caixa.versao ?? "Ainda não informada"}</dd>
          </dl>

          <div className="mt-5">
            <Field
              label="Veículo"
              htmlFor="caixa-veiculo"
              hint={
                bloqueada
                  ? "Caixa bloqueada pela RotaGuard não importa viagem e não vai para outro veículo."
                  : outraCaixa
                    ? `A caixa ${outraCaixa} sai deste veículo e fica sem veículo.`
                    : "Trocar de veículo guarda o histórico: as viagens antigas continuam com o veículo de antes."
              }
              error={erro ?? undefined}
            >
              <select
                id="caixa-veiculo"
                className="select"
                value={destino}
                disabled={readOnly || bloqueada}
                onChange={(evento) => {
                  setEstado("idle");
                  setDestino(evento.target.value);
                }}
              >
                <option value="">Sem veículo</option>
                {opcoes.map((veiculo) => (
                  <option key={veiculo.id} value={veiculo.id}>
                    {nomeDoVeiculo(veiculo)}
                    {veiculo.caixa_id && veiculo.caixa_id !== caixa.id ? ` · hoje com a ${codigo(veiculo.caixa_id) ?? "outra caixa"}` : ""}
                  </option>
                ))}
              </select>
            </Field>
          </div>
        </>
      )}
    </Drawer>
  );
}
