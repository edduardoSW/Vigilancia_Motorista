"use client";

import { useEffect, useState } from "react";
import { useListShortcuts } from "@/components/drivers/use-list-shortcuts";
import { useSession, useVisao } from "@/components/session-provider";
import { CardGrid, CardInfo, CardTitulo } from "@/components/ui/card-grid";
import { DataTable } from "@/components/ui/data-table";
import { Kbd } from "@/components/ui/kbd";
import { PageHeader } from "@/components/ui/page-header";
import { Tabs } from "@/components/ui/tabs";
import { ViewToggle } from "@/components/ui/view-toggle";
import { bridge, type Usuario } from "@/lib/bridge";
import { ActivityLog } from "./activity-log";
import { AddPersonDialog } from "./add-person-dialog";
import { PersonDrawer } from "./person-drawer";
import { RolesTable } from "./roles-table";
import { NOME_FUNCAO, quando, situacaoDe } from "./roles";

type Aba = "pessoas" | "atividades";

const plural = (total: number, um: string, varios: string) => `${total} ${total === 1 ? um : varios}`;

// Equipe (spec 014; prévia 7 com a direção "menos cara de IA"; spec 019): só o administrador. Pessoas em lista ou cards,
// e a pessoa abre na janela do centro. O registro de atividades é um histórico e continua só em lista (VIS-01).
export function TeamScreen() {
  const { pode } = useSession();
  const permitido = pode("equipe");
  const [visao, setVisao] = useVisao("equipe");
  const [aba, setAba] = useState<Aba>("pessoas");
  const [pessoas, setPessoas] = useState<Usuario[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const [selecionada, setSelecionada] = useState<number | null>(null);
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

  // Ctrl+N adiciona pessoa; desligado com uma janela aberta, para não abrir uma por cima da outra.
  useListShortcuts({
    onNew: permitido
      ? () => {
          setAba("pessoas");
          setAdicionando(true);
        }
      : undefined,
    enabled: permitido && !adicionando && !painelAberto,
  });

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
  const vazio = pessoas === null ? "Carregando a equipe…" : "Ninguém na equipe ainda.";

  function abrirPessoa(pessoa: Usuario) {
    setSelecionada(pessoa.id);
    setAberta(pessoa.id);
    setPainelAberto(true);
  }

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

      <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
        <Tabs
          items={[
            { id: "pessoas", label: "Pessoas", count: pessoas?.length },
            { id: "atividades", label: "Registro de atividades" },
          ]}
          value={aba}
          onChange={(id: string) => setAba(id as Aba)}
        />
        {aba === "pessoas" && <ViewToggle value={visao} onChange={setVisao} />}
      </div>

      {erro && (
        <p role="alert" className="mt-4 text-[14px] text-alarme">
          {erro}
        </p>
      )}

      <div className="mt-5">
        {aba === "pessoas" ? (
          <div key={`pessoas-${visao}`} className="anim-enter">
            {visao === "lista" ? (
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
                onOpen={abrirPessoa}
                label="Pessoas da equipe"
                empty={vazio}
              />
            ) : (
              <CardGrid
                items={lista}
                getId={(pessoa: Usuario) => pessoa.id}
                selectedId={selecionada}
                onSelect={setSelecionada}
                onOpen={abrirPessoa}
                label="Pessoas da equipe"
                empty={vazio}
                renderCard={(pessoa: Usuario) => (
                  <>
                    <CardTitulo titulo={pessoa.nome} detalhe={`Usuário ${pessoa.usuario}`} />
                    <span className="grid gap-1.5">
                      <CardInfo rotulo="Função">{NOME_FUNCAO[pessoa.funcao]}</CardInfo>
                      <CardInfo rotulo="Último acesso">{quando(pessoa.ultimo_acesso)}</CardInfo>
                      <CardInfo rotulo="Situação">
                        <span className={pessoa.ativo ? undefined : "text-grafite"}>{situacaoDe(pessoa)}</span>
                      </CardInfo>
                    </span>
                  </>
                )}
              />
            )}
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
