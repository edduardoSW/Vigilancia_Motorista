"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession } from "@/components/session-provider";
import { CardGrid, CardInfo, CardTitulo } from "@/components/ui/card-grid";
import { DataTable } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { PageHeader } from "@/components/ui/page-header";
import { Tabs } from "@/components/ui/tabs";
import { ViewToggle } from "@/components/ui/view-toggle";
import { bridge, type AparelhoRemoto, type RemotosLista, type SessaoRemota, type Visao } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { dataHora, duracaoTexto, haQuanto, resumoDaSessao, resumoDaTela, statusDaCentral, textoRisco } from "./remote-data";
import { SessionDetails } from "./session-details";

const ATUALIZAR_MS = 10_000;
type Aba = "computadores" | "sessoes";

/** "Testando agora · risco médio" (com o ponto pulsando) ou "Último sinal há 2 h". */
function Situacao({ aparelho, agora }: { aparelho: AparelhoRemoto; agora: number }) {
  if (aparelho.revogado_em) return <span className="text-grafite">Desligado da empresa {haQuanto(aparelho.revogado_em, agora)}</span>;
  if (!aparelho.testando_agora) return <span className="text-grafite">Último sinal {haQuanto(aparelho.ultimo_sinal, agora)}</span>;
  const risco = textoRisco(aparelho.risco_atual);
  return (
    <span className="inline-flex items-center gap-2">
      <span aria-hidden="true" className="pulse-dot" />
      <span>
        <b className="font-semibold">Testando agora</b> <span className={cn(risco.alarme ? "font-semibold text-alarme" : "text-grafite")}>· {risco.texto}</span>
      </span>
    </span>
  );
}

function situacaoDaSessao(sessao: SessaoRemota) {
  if (sessao.em_andamento) return "Em andamento";
  if (sessao.sem_fim) return "Sem fim registrado";
  return "Encerrada";
}

// Testes à distância (spec 026, decisão 8): o que o RotaGuard Script de outros computadores mandou para a central e o
// painel já baixou. Tudo vem do banco local: sem a central, a tela continua com o que já tinha (PCE-05).
export function RemoteScreen() {
  const { pode } = useSession();
  const [lista, setLista] = useState<RemotosLista | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState<Aba>("sessoes");
  const [visao, setVisao] = useState<Visao>("cards");
  const [filtro, setFiltro] = useState<AparelhoRemoto | null>(null);
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [aberta, setAberta] = useState<SessaoRemota | null>(null);
  const [agora, setAgora] = useState(() => Date.now());

  // A Ponte busca na central a cada 30 s; aqui só relê o banco local a cada 10 s, enquanto a tela está aberta.
  useEffect(() => {
    let vivo = true;
    const ler = () =>
      bridge.remotos_listar().then((resposta) => {
        if (!vivo) return;
        setAgora(Date.now());
        if (resposta.ok) {
          setLista(resposta.dados);
          setErro(null);
        } else setErro(resposta.erro);
      });
    void ler();
    const vigia = window.setInterval(() => void ler(), ATUALIZAR_MS);
    return () => {
      vivo = false;
      window.clearInterval(vigia);
    };
  }, []);

  const aparelhos = lista?.aparelhos ?? [];
  const sessoes = (lista?.sessoes ?? []).filter((sessao) => !filtro || sessao.aparelho_uid === filtro.uid);
  const status = lista ? statusDaCentral(lista.central, agora) : null;
  const vazio = !lista ? "Carregando…" : !lista.central.conectado && !lista.aparelhos.length ? "Nada baixado ainda." : undefined;

  function verSessoesDe(aparelho: AparelhoRemoto) {
    setFiltro(aparelho);
    setAba("sessoes");
    setSelecionado(null);
  }

  const colunasComputadores = [
    {
      id: "nome",
      header: "Computador",
      cell: (item: AparelhoRemoto) => (
        <>
          <b className="block font-semibold leading-5">{item.nome}</b>
          <span className="block text-[13px] leading-4 text-grafite">{[item.computador, item.programa].filter(Boolean).join(" · ") || "Sem detalhes"}</span>
        </>
      ),
    },
    { id: "situacao", header: "Situação", cell: (item: AparelhoRemoto) => <Situacao aparelho={item} agora={agora} /> },
    {
      id: "sessoes",
      header: "Sessões",
      cell: (item: AparelhoRemoto) => <span className="tabular-nums">{item.sessoes}</span>,
      width: "110px",
    },
    { id: "pareado", header: "Conectado desde", cell: (item: AparelhoRemoto) => <span className="tabular-nums text-grafite">{dataHora(item.pareado_em)}</span> },
  ];

  const colunasSessoes = [
    {
      id: "computador",
      header: "Computador",
      width: "26%",
      cell: (item: SessaoRemota) => (
        <>
          <b className="block font-semibold leading-5">{item.aparelho_nome}</b>
          <span className="block text-[13px] leading-4 text-grafite">{dataHora(item.iniciada_em)}</span>
        </>
      ),
    },
    {
      id: "situacao",
      header: "Situação",
      width: "20%",
      cell: (item: SessaoRemota) => (
        <>
          <span className="flex items-center gap-2 leading-5">
            {item.em_andamento && <span aria-hidden="true" className="pulse-dot" />}
            {situacaoDaSessao(item)}
          </span>
          <span className="block text-[13px] leading-4 text-grafite">{duracaoTexto(item.resumo.duracao_s)}</span>
        </>
      ),
    },
    { id: "resumo", header: "Resumo", cell: (item: SessaoRemota) => <span className="text-[13.5px] tabular-nums">{resumoDaSessao(item)}</span> },
  ];

  function cardComputador(item: AparelhoRemoto) {
    return (
      <>
        <CardTitulo titulo={item.nome} detalhe={item.computador ?? item.programa ?? undefined} />
        <span className="text-[13.5px]">
          <Situacao aparelho={item} agora={agora} />
        </span>
        <span className="grid gap-1.5">
          <CardInfo rotulo="Sessões">{item.sessoes}</CardInfo>
          <CardInfo rotulo="Conectado desde">{dataHora(item.pareado_em)}</CardInfo>
        </span>
      </>
    );
  }

  function cardSessao(item: SessaoRemota) {
    return (
      <>
        <CardTitulo titulo={item.aparelho_nome} detalhe={dataHora(item.iniciada_em)} />
        <span className="grid gap-1.5">
          <CardInfo rotulo="Situação">
            {item.em_andamento && <span aria-hidden="true" className="pulse-dot mr-2 align-middle" />}
            {situacaoDaSessao(item)}
          </CardInfo>
          <CardInfo rotulo="Duração">{duracaoTexto(item.resumo.duracao_s)}</CardInfo>
          <CardInfo rotulo="Eventos">{item.eventos ?? 0}</CardInfo>
          <CardInfo rotulo="Trechos">{item.trechos ? `${item.trechos_baixados ?? 0} de ${item.trechos} ${item.trechos === 1 ? "baixado" : "baixados"}` : "nenhum"}</CardInfo>
        </span>
      </>
    );
  }

  const abrirSessao = (item: SessaoRemota) => {
    setSelecionado(item.uid);
    setAberta(item);
  };

  return (
    <section className="anim-enter px-14 pb-16 pt-[34px]">
      <PageHeader title="Testes à distância" summary={lista ? resumoDaTela(lista) : erro ? "Não deu para carregar" : "Carregando…"} />

      {status && (
        <p className={cn("-mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[14px]", status.alarme ? "font-semibold text-alarme" : "text-grafite")}>
          <span>{status.texto}</span>
          {!lista?.central.conectado && pode("configuracoes") && (
            <Link href="/configuracoes/" className="font-semibold text-tinta hover:underline">
              Conectar em Configurações › Central
            </Link>
          )}
        </p>
      )}

      {lista && !lista.central.conectado && !lista.aparelhos.length ? (
        <div className="mt-8 max-w-[640px] rounded-[12px] border border-fio bg-superficie p-5">
          <h2 className="font-titulo text-[18px] font-semibold">Como ver o teste de outro computador</h2>
          <ol className="mt-3 grid list-decimal gap-1.5 pl-5 text-[14px]">
            <li>Em Configurações › Central, conecte este painel com o usuário da empresa na central.</li>
            <li>Ainda lá, gere um código para o outro computador.</li>
            <li>No outro computador, abra o RotaGuard Script › Conectar à empresa e digite o código.</li>
          </ol>
          <p className="mt-3 text-[13.5px] text-grafite">
            Os eventos, o resumo de cada sessão e os trechos de vídeo chegam aqui e ficam guardados neste computador.
          </p>
        </div>
      ) : (
        <>
          <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
            <Tabs
              items={[
                { id: "sessoes", label: "Sessões", count: sessoes.length },
                { id: "computadores", label: "Computadores", count: aparelhos.length },
              ]}
              value={aba}
              onChange={(id) => {
                setAba(id as Aba);
                setSelecionado(null);
              }}
            />
            <ViewToggle value={visao} onChange={setVisao} />
          </div>

          {aba === "sessoes" && filtro && (
            <p className="mt-3 text-[14px] text-grafite">
              Sessões de <b className="font-semibold text-tinta">{filtro.nome}</b> ·{" "}
              <button type="button" className="font-semibold text-tinta hover:underline" onClick={() => setFiltro(null)}>
                Mostrar todas
              </button>
            </p>
          )}

          {erro && (
            <p role="alert" className="mt-4 text-[14px] text-alarme">
              {erro}
            </p>
          )}

          <div key={`${aba}-${visao}`} className="anim-enter mt-4">
            {aba === "computadores" ? (
              visao === "lista" ? (
                <DataTable
                  columns={colunasComputadores}
                  rows={aparelhos}
                  getRowId={(item: AparelhoRemoto) => item.uid}
                  selectedId={selecionado}
                  onSelect={(id) => setSelecionado(id)}
                  onOpen={verSessoesDe}
                  label="Computadores"
                  empty={vazio ?? "Nenhum computador conectado ainda."}
                />
              ) : (
                <CardGrid
                  items={aparelhos}
                  getId={(item: AparelhoRemoto) => item.uid}
                  selectedId={selecionado}
                  onSelect={setSelecionado}
                  onOpen={verSessoesDe}
                  renderCard={cardComputador}
                  label="Computadores"
                  empty={vazio ?? "Nenhum computador conectado ainda."}
                />
              )
            ) : visao === "lista" ? (
              <DataTable
                columns={colunasSessoes}
                rows={sessoes}
                getRowId={(item: SessaoRemota) => item.uid}
                selectedId={selecionado}
                onSelect={(id) => setSelecionado(id)}
                onOpen={abrirSessao}
                label="Sessões"
                empty={vazio ?? "Nenhuma sessão de teste ainda."}
              />
            ) : (
              <CardGrid
                items={sessoes}
                getId={(item: SessaoRemota) => item.uid}
                selectedId={selecionado}
                onSelect={setSelecionado}
                onOpen={abrirSessao}
                renderCard={cardSessao}
                label="Sessões"
                empty={vazio ?? "Nenhuma sessão de teste ainda."}
              />
            )}
          </div>
        </>
      )}

      <Dialog
        width={760}
        open={aberta !== null}
        onClose={() => setAberta(null)}
        title={aberta ? `Sessão de ${aberta.aparelho_nome}` : ""}
        summary={aberta ? `${dataHora(aberta.iniciada_em)} · ${situacaoDaSessao(aberta)} · ${resumoDaSessao(aberta)}` : undefined}
        footer={
          <button type="button" className="btn" onClick={() => setAberta(null)}>
            Fechar
          </button>
        }
      >
        {aberta && <SessionDetails key={aberta.uid} sessaoUid={aberta.uid} />}
      </Dialog>
    </section>
  );
}
