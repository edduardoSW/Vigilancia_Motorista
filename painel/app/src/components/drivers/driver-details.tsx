"use client";

import { useState } from "react";
import { useToast } from "@/components/ui/toast";
import { bridge, type Motorista } from "@/lib/bridge";
import { formatarData, mascararCpf } from "@/lib/validators";
import { DetailList, DetailRow, DetailSection } from "./detail-list";
import { avisoCnh, SITUACAO_MOTORISTA, textoMomentos } from "./driver-data";
import { DriverTerm } from "./driver-term";
import { plural } from "./use-list-shortcuts";

// Dados do motorista antes de editar (spec 019, INT-01): o termo de ciência (com as ações para quem pode cadastrar),
// a carteira e o resto do cadastro. "Editar", no rodapé da janela, troca para o formulário.
export function DriverDetails({
  motorista,
  hoje,
  podeCadastrar,
  destacarTermo,
  onChanged,
}: {
  motorista: Motorista;
  hoje: string;
  podeCadastrar: boolean;
  /** Logo depois do cadastro novo, "Importar termo assinado" recebe o foco. */
  destacarTermo: boolean;
  onChanged: (motorista: Motorista) => void;
}) {
  const { toast } = useToast();
  const [exportando, setExportando] = useState(false);
  const cnh = avisoCnh(motorista.cnh_validade, hoje);

  async function exportar() {
    setExportando(true);
    const resposta = await bridge.motorista_exportar(motorista.id);
    setExportando(false);
    if (!resposta.ok) {
      toast({ text: resposta.erro });
      return;
    }
    toast({ text: `Dados de ${motorista.nome_curto} salvos em ${resposta.dados.caminho}` });
  }

  return (
    <div className="grid gap-5">
      <DetailSection title="Termo de ciência">
        <DriverTerm motorista={motorista} podeCadastrar={podeCadastrar} destacar={destacarTermo} onChanged={onChanged} />
      </DetailSection>

      <DetailSection title="Carteira de motorista">
        <DetailList>
          <DetailRow label="Número da CNH">{motorista.cnh_numero}</DetailRow>
          <DetailRow label="Categoria">{motorista.cnh_categoria}</DetailRow>
          <DetailRow label="Validade" alarm={cnh.alarme}>
            {cnh.alarme ? cnh.texto : formatarData(motorista.cnh_validade)}
          </DetailRow>
        </DetailList>
      </DetailSection>

      <DetailSection title="Cadastro">
        <DetailList>
          <DetailRow label="Nome nos relatórios">{motorista.nome_curto}</DetailRow>
          <DetailRow label="Situação">{SITUACAO_MOTORISTA[motorista.situacao]}</DetailRow>
          <DetailRow label="Telefone" muted={!motorista.telefone}>
            {motorista.telefone ?? "Não informado"}
          </DetailRow>
          <DetailRow label="CPF" muted={!motorista.cpf}>
            {motorista.cpf ? mascararCpf(motorista.cpf) : "Não informado"}
          </DetailRow>
          <DetailRow label="Últimos 30 dias">
            {plural(motorista.viagens_30d, "viagem", "viagens")} · {textoMomentos(motorista.confirmados_30d).toLowerCase()}
          </DetailRow>
          {motorista.observacoes && <DetailRow label="Observações">{motorista.observacoes}</DetailRow>}
        </DetailList>
        {podeCadastrar && (
          <button type="button" className="btn btn-small mt-4" disabled={exportando} onClick={exportar}>
            {exportando ? "Exportando…" : "Exportar dados deste motorista"}
          </button>
        )}
      </DetailSection>
    </div>
  );
}
