import { DetailList, DetailRow, DetailSection } from "@/components/drivers/detail-list";
import type { Caixa, Veiculo } from "@/lib/bridge";
import { quando, SITUACAO_CAIXA, SITUACAO_VEICULO, TIPO_VEICULO, TRANSPORTA } from "./vehicle-labels";

// Dados do veículo antes de editar (spec 019, INT-01): o cadastro e a caixa instalada, em rótulo e valor.
// "Editar", no rodapé da janela, troca para o formulário. Vermelho só quando a caixa pede atenção.
export function VehicleDetails({
  veiculo,
  caixa,
  agora,
  podeCadastrar,
}: {
  veiculo: Veiculo;
  caixa: Caixa | undefined;
  /** O "Agora" da lista (viagem para verificar, em viagem…). */
  agora: { texto: string; alarme: boolean };
  podeCadastrar: boolean;
}) {
  const transporta = TRANSPORTA[veiculo.transporta];
  const regra = transporta.regra.charAt(0).toLowerCase() + transporta.regra.slice(1);
  const motivo = caixa?.detalhe ?? (caixa?.situacao === "bloqueada" ? "Não importa viagem." : null);

  return (
    <div className="grid gap-5">
      <DetailSection title="Veículo">
        <DetailList>
          <DetailRow label="Tipo">{TIPO_VEICULO[veiculo.tipo]}</DetailRow>
          <DetailRow label="Placa">{veiculo.placa}</DetailRow>
          <DetailRow label="Marca e modelo" muted={!veiculo.modelo}>
            {veiculo.modelo ?? "Não informado"}
          </DetailRow>
          <DetailRow label="Ano" muted={!veiculo.ano}>
            {veiculo.ano ?? "Não informado"}
          </DetailRow>
          <DetailRow label="Transporta">
            {transporta.rotulo} · {regra}
          </DetailRow>
          <DetailRow label="Situação">{SITUACAO_VEICULO[veiculo.situacao]}</DetailRow>
          {veiculo.situacao === "em_uso" && caixa && !agora.alarme && <DetailRow label="Agora">{agora.texto}</DetailRow>}
        </DetailList>
      </DetailSection>

      <DetailSection title="Caixa instalada">
        {caixa ? (
          <DetailList>
            <DetailRow label="Caixa">{caixa.codigo}</DetailRow>
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
          </DetailList>
        ) : (
          <p className="text-[14px] text-grafite">
            {podeCadastrar ? "Nenhuma caixa neste veículo. Para instalar uma, use Editar." : "Nenhuma caixa neste veículo."}
          </p>
        )}
      </DetailSection>
    </div>
  );
}
