"use client";

import { useEffect, useState } from "react";
import { bridge, type Usuario } from "@/lib/bridge";
import { useSession } from "@/components/session-provider";
import { DataTable } from "@/components/ui/data-table";
import { Kbd } from "@/components/ui/kbd";
import { PageHeader } from "@/components/ui/page-header";
import { Tabs } from "@/components/ui/tabs";
import { ActivityLog } from "./activity-log";
import { AddPersonDialog } from "./add-person-dialog";
import { PersonDrawer } from "./person-drawer";
import { RolesTable } from "./roles-table";
import { NOME_FUNCAO, quando, situacaoDe } from "./roles";

type Aba = "pessoas" | "atividades";

const plural = (total: number, um: string, varios: string) => `${total} ${total === 1 ? um : varios}`;

// Equipe (spec 014; prévia 7 com a direção "menos cara de IA"): só o administrador.
export function TeamScreen() {
  const { pode } = useSession();
  const permitido = pode("equipe");
  const [aba, setAba] = useState<Aba>("pessoas");
  const [pessoas, setPessoas] = useState<Usuario[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const [selecionada, setSelecionada] = useState<string | number | null>(null);
  const [aberta, setAberta] = useState<number | null>(null);
  const [painelAberto, setPainelAberto] = useState(false);
  const [adicionando, setAdicionando] = useState(false);

  useEffect(() => {
    if (!permitido) return;
    let vivo = true;
    bridge.equipe_listar().then((resposta) => {
      if (!vivo) return;
      if (resposta.ok) {
        setPessoas(resposta.dados);
        setErro(null);
      } else setErro(resposta.erro);
    });
    return () => {
      vivo = false;
    };
  }, [permitido, versao]);

  useEffect(() => {
    if (!permitido) return;
    const aoTeclar = (evento: KeyboardEvent) => {
      if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === "n") {
        evento.preventDefault();
        setAba("pessoas");
        setAdicionando(true);
      }
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [permitido]);

  if (!permitido) {
    return (
      <section className="anim-enter max-w-[1040px] px-14 pb-16 pt-[34px]">
        <PageHeader title="Equipe" summary="Só o administrador vê esta área." guide={{ capitulo: "equipe" }} />
      </section>
    );
  }

  const lista = pessoas ?? [];
  const ativas = lista.filter((pessoa) => pessoa.ativo).length;
  const desativadas = lista.length - ativas;
  const resumo = pessoas
    ? [plural(lista.length, "pessoa", "pessoas"), plural(ativas, "ativa", "ativas"), desativadas ? plural(desativadas, "desativada", "desativadas") : null]
        .filter(Boolean)
        .join(" · ")
    : "Carregando…";
  const recarregar = () => setVersao((valor) => valor + 1);
  const pessoaAberta = lista.find((pessoa) => pessoa.id === aberta) ?? null;

  return (
    <section className="anim-enter max-w-[1040px] px-14 pb-16 pt-[34px]">
      <PageHeader
        title="Equipe"
        summary={resumo}
        guide={{ capitulo: "equipe" }}
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setAdicionando(true)}>
            Adicionar pessoa <Kbd>Ctrl N</Kbd>
          </button>
        }
      />

      <div className="mt-6">
        <Tabs
          items={[
            { id: "pessoas", label: "Pessoas", count: pessoas?.length },
            { id: "atividades", label: "Registro de atividades" },
          ]}
          value={aba}
          onChange={(id: string) => setAba(id as Aba)}
        />
      </div>

      {erro && (
        <p role="alert" className="mt-4 text-[14px] text-alarme">
          {erro}
        </p>
      )}

      <div className="mt-5">
        {aba === "pessoas" ? (
          <div key="pessoas" className="anim-enter">
            <DataTable
              columns={[
                {
                  id: "pessoa",
                  header: "Pessoa",
                  cell: (pessoa: Usuario) => (
                    <span className="block truncate">
                      <b className="font-semibold">{pessoa.nome}</b>
                      <span className="text-grafite"> · {pessoa.usuario}</span>
                    </span>
                  ),
                },
                { id: "funcao", header: "Função", width: "170px", cell: (pessoa: Usuario) => NOME_FUNCAO[pessoa.funcao] },
                { id: "acesso", header: "Último acesso", width: "170px", cell: (pessoa: Usuario) => quando(pessoa.ultimo_acesso) },
                {
                  id: "situacao",
                  header: "Situação",
                  width: "200px",
                  cell: (pessoa: Usuario) => <span className={pessoa.ativo ? undefined : "text-grafite"}>{situacaoDe(pessoa)}</span>,
                },
              ]}
              rows={lista}
              getRowId={(pessoa: Usuario) => pessoa.id}
              selectedId={selecionada}
              onSelect={setSelecionada}
              onOpen={(pessoa: Usuario) => {
                setAberta(pessoa.id);
                setPainelAberto(true);
              }}
              label="Pessoas da equipe"
              empty={pessoas === null ? "Carregando a equipe…" : "Ninguém na equipe ainda."}
            />
            <RolesTable />
          </div>
        ) : (
          <ActivityLog key="atividades" pessoas={lista} />
        )}
      </div>

      <AddPersonDialog open={adicionando} onClose={() => setAdicionando(false)} onCreated={recarregar} />
      <PersonDrawer open={painelAberto} pessoa={pessoaAberta} onClose={() => setPainelAberto(false)} onChanged={recarregar} />
    </section>
  );
}
