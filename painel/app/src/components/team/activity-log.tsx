"use client";

import { useEffect, useState } from "react";
import { bridge, type Atividade, type Usuario } from "@/lib/bridge";
import { DataTable } from "@/components/ui/data-table";
import { useToast } from "@/components/ui/toast";
import { quando } from "./roles";

// Registro de atividades (spec 014, decisão 11): quem, quando, o quê e em quê, com a conferência de integridade.
const ACOES: Record<string, string> = {
  entrou: "Entrou",
  errou_senha: "Errou a senha",
  saiu: "Saiu",
  bloqueou: "Bloqueou a tela",
  desbloqueou: "Desbloqueou a tela",
  abriu_video: "Abriu vídeo",
  confirmou: "Confirmou momento",
  alarme_falso: "Marcou alarme falso",
  orientou: "Registrou orientação",
  desfez: "Desfez decisão",
  cadastrou: "Cadastrou",
  editou: "Editou",
  desativou: "Desativou",
  reativou: "Reativou",
  mudou_configuracao: "Mudou configuração",
  fez_copia: "Fez cópia de segurança",
  exportou: "Exportou",
};

const textoDaAcao = (acao: string) => ACOES[acao] ?? acao.charAt(0).toUpperCase() + acao.slice(1).replace(/_/g, " ");

export function ActivityLog({ pessoas }: { pessoas: Usuario[] }) {
  const { toast } = useToast();
  const [usuarioId, setUsuarioId] = useState("");
  const [itens, setItens] = useState<Atividade[] | null>(null);
  const [integro, setIntegro] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [selecionada, setSelecionada] = useState<string | number | null>(null);
  const [exportando, setExportando] = useState(false);

  useEffect(() => {
    let vivo = true;
    bridge.atividades_listar(usuarioId ? { usuario_id: Number(usuarioId) } : {}).then((resposta) => {
      if (!vivo) return;
      if (resposta.ok) {
        setItens(resposta.dados.itens);
        setIntegro(resposta.dados.integro);
        setErro(null);
      } else setErro(resposta.erro);
    });
    return () => {
      vivo = false;
    };
  }, [usuarioId]);

  async function exportar() {
    setExportando(true);
    const resposta = await bridge.atividades_exportar();
    setExportando(false);
    if (resposta.ok) toast({ text: `Registro salvo em ${resposta.dados.caminho}` });
    else toast({ text: resposta.erro });
  }

  return (
    <div className="anim-enter">
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-[14px] text-grafite" htmlFor="filtro-pessoa">
          Pessoa
          <select id="filtro-pessoa" className="select w-[220px]" value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)}>
            <option value="">Todas</option>
            {pessoas.map((pessoa) => (
              <option key={pessoa.id} value={pessoa.id}>
                {pessoa.nome}
              </option>
            ))}
          </select>
        </label>
        <p className={integro ? "text-[14px] text-grafite" : "text-[14px] font-semibold text-alarme"} role={integro ? undefined : "alert"}>
          {integro ? "O registro está completo e sem alteração" : "Alguma linha do registro foi alterada ou apagada"}
        </p>
        <button type="button" className="btn btn-small ml-auto" onClick={exportar} disabled={exportando}>
          {exportando ? "Exportando…" : "Exportar CSV"}
        </button>
      </div>

      {erro && (
        <p role="alert" className="mt-4 text-[14px] text-alarme">
          {erro}
        </p>
      )}

      <div className="mt-4">
        <DataTable
          columns={[
            { id: "quando", header: "Quando", width: "170px", cell: (item: Atividade) => quando(item.em) },
            { id: "quem", header: "Quem", width: "180px", cell: (item: Atividade) => item.usuario ?? "Ninguém entrou" },
            { id: "oque", header: "O quê", width: "220px", cell: (item: Atividade) => textoDaAcao(item.acao) },
            {
              id: "emque",
              header: "Em quê",
              cell: (item: Atividade) => (
                <span className="block truncate" title={item.detalhe ?? undefined}>
                  {[item.alvo, item.detalhe].filter(Boolean).join(" · ") || "—"}
                </span>
              ),
            },
          ]}
          rows={itens ?? []}
          getRowId={(item: Atividade) => item.id}
          selectedId={selecionada}
          onSelect={setSelecionada}
          label="Registro de atividades"
          empty={itens === null ? "Carregando o registro…" : "Nada registrado para esta pessoa."}
        />
      </div>
    </div>
  );
}
