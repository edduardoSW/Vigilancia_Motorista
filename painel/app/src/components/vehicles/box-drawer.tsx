"use client";

import { useState } from "react";
import { DetailList, DetailRow } from "@/components/drivers/detail-list";
import type { SaveState } from "@/components/drivers/driver-form";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { SaveButton } from "@/components/ui/save-button";
import { bridge, type Caixa, type Veiculo } from "@/lib/bridge";
import { nomeDoVeiculo, quando, SITUACAO_CAIXA } from "./vehicle-labels";

// Janela da caixa, no centro (spec 015 decisão 5; spec 019 MOD-01): o painel não cria caixa; só mostra a situação e
// vincula ou troca de veículo. Trocar guarda o histórico no Python: as viagens antigas continuam com o veículo de antes
// (CXA-02). Já é uma janela de ações: não tem "ver antes de editar".

export function BoxDrawer({
  open,
  abertura,
  caixa,
  caixas,
  veiculos,
  readOnly,
  onClose,
  onLinked,
}: {
  open: boolean;
  /** Muda a cada abertura: a escolha do veículo recomeça do que está salvo. */
  abertura: number;
  caixa: Caixa | null;
  caixas: Caixa[];
  veiculos: Veiculo[];
  readOnly: boolean;
  onClose: () => void;
  onLinked: (caixa: Caixa, veiculoAnterior: number | null) => void;
}) {
  const atual = caixa?.veiculo_id ? String(caixa.veiculo_id) : "";
  const [aberturaAtendida, setAberturaAtendida] = useState<string | null>(null);
  const [destino, setDestino] = useState(atual);
  const [estado, setEstado] = useState<SaveState>("idle");
  const [erro, setErro] = useState<string | null>(null);

  // Abriu (a mesma caixa de novo ou outra): começa com o veículo salvo. Ao fechar, o conteúdo fica até a janela sumir.
  const chave = caixa ? `${caixa.id}-${abertura}` : null;
  if (open && chave !== aberturaAtendida) {
    setAberturaAtendida(chave);
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
  const motivo = caixa?.detalhe ?? (bloqueada ? "Não importa viagem." : null);

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
    <Dialog
      width={560}
      open={open && caixa !== null}
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
          <DetailList>
            <DetailRow label="Situação" alarm={caixa.situacao !== "ok"}>
              {SITUACAO_CAIXA[caixa.situacao]}
            </DetailRow>
            {motivo && <DetailRow label="Motivo">{motivo}</DetailRow>}
            <DetailRow label="Última coleta" muted={!caixa.ultima_coleta}>
              {quando(caixa.ultima_coleta) ?? "Nunca coletada"}
            </DetailRow>
            <DetailRow label="Versão do programa" muted={!caixa.versao}>
              {caixa.versao ?? "Ainda não informada"}
            </DetailRow>
            {readOnly && (
              <DetailRow label="Veículo" muted={!veiculoAtual}>
                {veiculoAtual ? nomeDoVeiculo(veiculoAtual) : "Sem veículo"}
              </DetailRow>
            )}
          </DetailList>

          {!readOnly && (
            <div className="mt-5 border-t border-fio pt-5">
              <Field
                className="mb-0"
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
                  disabled={bloqueada}
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
          )}
        </>
      )}
    </Dialog>
  );
}
