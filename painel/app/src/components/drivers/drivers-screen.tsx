"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { DriverDetails } from "@/components/drivers/driver-details";
import { avisoCnh, SITUACAO_MOTORISTA, termoCurto, textoMomentos } from "@/components/drivers/driver-data";
import { DriverForm, type SaveState } from "@/components/drivers/driver-form";
import { plural, semAcento, useListShortcuts } from "@/components/drivers/use-list-shortcuts";
import { useSession, useVisao } from "@/components/session-provider";
import { CardGrid, CardInfo, CardTitulo } from "@/components/ui/card-grid";
import { DataTable } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { Kbd } from "@/components/ui/kbd";
import { PageHeader } from "@/components/ui/page-header";
import { SaveButton } from "@/components/ui/save-button";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { ViewToggle } from "@/components/ui/view-toggle";
import { bridge, type Motorista } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { diasAte, hojeIso, mesAno, situacaoCnh } from "@/lib/validators";

// Motoristas (prévia 4, specs 015 e 019): abas por situação, busca, lista ou cards e a janela no centro.
// Abrir um motorista mostra os dados e o termo; "Editar" troca para o formulário na mesma janela (INT-01).
// Consulta vê tudo só para leitura; cadastrar, editar, termo e exportar são de administrador e supervisor (spec 014).

type Aba = Motorista["situacao"];
/** O que a janela mostra: o formulário do cadastro novo, os dados de um motorista ou o formulário para editar. */
type Janela = { modo: "novo" } | { modo: "ver"; id: number; recemCadastrado: boolean } | { modo: "editar"; id: number };

const ABAS: Aba[] = ["ativo", "afastado", "desligado"];
const NOME_ABA: Record<Aba, string> = { ativo: "Ativos", afastado: "Afastados", desligado: "Desligados" };
const VAZIO: Record<Aba, string> = {
  ativo: "Nenhum motorista ativo ainda.",
  afastado: "Nenhum motorista afastado.",
  desligado: "Nenhum motorista desligado.",
};
const FORM_ID = "form-motorista";

/** Subtítulo com número real: "5 ativos · 1 CNH vence em 12 dias · 1 sem termo". */
function resumo(lista: Motorista[], hoje: string) {
  const ativos = lista.filter((motorista) => motorista.situacao === "ativo");
  const partes = [plural(ativos.length, "ativo", "ativos")];
  const emBreve = ativos.filter((motorista) => situacaoCnh(motorista.cnh_validade, hoje) === "vence_em_breve");
  if (emBreve.length === 1) {
    const dias = diasAte(emBreve[0].cnh_validade, hoje);
    partes.push(dias === 0 ? "1 CNH vence hoje" : `1 CNH vence em ${plural(dias, "dia", "dias")}`);
  } else if (emBreve.length > 1) {
    partes.push(`${emBreve.length} CNHs vencem em até 30 dias`);
  }
  const vencidas = ativos.filter((motorista) => situacaoCnh(motorista.cnh_validade, hoje) === "vencida").length;
  if (vencidas) partes.push(plural(vencidas, "CNH vencida", "CNHs vencidas"));
  const semTermo = ativos.filter((motorista) => !motorista.termo.assinado).length;
  if (semTermo) partes.push(`${semTermo} sem termo`);
  return partes.join(" · ");
}

export function DriversScreen() {
  const { pode } = useSession();
  const podeEditar = pode("cadastrar");
  const { toast } = useToast();
  const [visao, setVisao] = useVisao("motoristas");
  const [lista, setLista] = useState<Motorista[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState<Aba>("ativo");
  const [busca, setBusca] = useState("");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [janela, setJanela] = useState<Janela | null>(null);
  const [aberta, setAberta] = useState(false);
  // Cada abertura começa do zero; ao fechar, o conteúdo fica na tela até a janela terminar de sumir.
  const [abertura, setAbertura] = useState(0);
  const [salvando, setSalvando] = useState<SaveState>("idle");
  const buscaRef = useRef<HTMLInputElement>(null);
  const hoje = hojeIso();

  useEffect(() => {
    let vivo = true;
    bridge.motoristas_listar().then((resposta) => {
      if (!vivo) return;
      if (resposta.ok) setLista(resposta.dados);
      else setErro(resposta.erro);
    });
    return () => {
      vivo = false;
    };
  }, []);

  // A busca rápida (Ctrl+K) pede para abrir um motorista com ?abrir=<id>. Ajuste na renderização, sem efeito.
  const params = useSearchParams();
  const pedido = params.get("abrir") ? params.toString() : null;
  const [pedidoAtendido, setPedidoAtendido] = useState<string | null>(null);
  if (pedido && lista && pedido !== pedidoAtendido) {
    setPedidoAtendido(pedido);
    const escolhido = lista.find((item) => String(item.id) === params.get("abrir"));
    if (escolhido) {
      setAba(escolhido.situacao);
      abrir(escolhido);
    }
  }

  async function tentarDeNovo() {
    setErro(null);
    const resposta = await bridge.motoristas_listar();
    if (resposta.ok) setLista(resposta.dados);
    else setErro(resposta.erro);
  }

  const todos = lista ?? [];
  const motorista = janela && janela.modo !== "novo" ? (todos.find((item) => item.id === janela.id) ?? null) : null;
  const termo = semAcento(busca.trim());
  const linhas = todos
    .filter((item) => item.situacao === aba)
    .filter((item) => !termo || semAcento(`${item.nome} ${item.nome_curto} ${item.matricula}`).includes(termo))
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  const vazio = lista === null ? "Carregando…" : busca.trim() ? `Nenhum motorista encontrado para "${busca.trim()}".` : VAZIO[aba];

  function abrirNovo() {
    setSalvando("idle");
    setAbertura((valor) => valor + 1);
    setJanela({ modo: "novo" });
    setAberta(true);
  }

  function abrir(item: Motorista) {
    setSelecionado(String(item.id));
    setAbertura((valor) => valor + 1);
    setJanela({ modo: "ver", id: item.id, recemCadastrado: false });
    setAberta(true);
  }

  function editar(id: number) {
    setSalvando("idle");
    setJanela({ modo: "editar", id });
  }

  const fechar = () => setAberta(false);

  useListShortcuts({ onNew: podeEditar ? abrirNovo : undefined, searchRef: buscaRef, enabled: !aberta });

  function atualizarNaLista(salvo: Motorista) {
    setLista((atual) => {
      const base = atual ?? [];
      return base.some((item) => item.id === salvo.id) ? base.map((item) => (item.id === salvo.id ? salvo : item)) : [...base, salvo];
    });
  }

  function aoSalvar(salvo: Motorista, novo: boolean) {
    atualizarNaLista(salvo);
    setAba(salvo.situacao);
    setSelecionado(String(salvo.id));
    toast({ text: novo ? "Motorista cadastrado" : "Motorista salvo" });
    // Salvou: a janela volta para os dados. No cadastro novo, "Importar termo assinado" vem em destaque.
    setJanela({ modo: "ver", id: salvo.id, recemCadastrado: novo });
  }

  const colunas = [
    {
      id: "motorista",
      header: "Motorista",
      cell: (item: Motorista) => (
        <>
          <b className="block font-semibold leading-5">{item.nome}</b>
          <span className="block text-[13px] leading-4 text-grafite">Matrícula {item.matricula}</span>
        </>
      ),
    },
    {
      id: "carteira",
      header: "Carteira",
      cell: (item: Motorista) => {
        const aviso = avisoCnh(item.cnh_validade, hoje);
        return (
          <>
            <span className="block leading-5">Categoria {item.cnh_categoria}</span>
            <span className={cn("block text-[13px] leading-4", aviso.alarme ? "font-semibold text-alarme" : "text-grafite")}>{aviso.texto}</span>
          </>
        );
      },
    },
    {
      id: "termo",
      header: "Termo",
      cell: (item: Motorista) =>
        item.termo.assinado ? (
          <>
            <span className="block leading-5">{termoCurto(item)}</span>
            <span className="block text-[13px] leading-4 text-grafite">{item.termo.arquivo ? item.termo.arquivo.nome : "Sem o arquivo do termo"}</span>
          </>
        ) : (
          <>
            <span className="block font-semibold leading-5 text-alarme">Falta registrar</span>
            <span className="block text-[13px] leading-4 text-grafite">Vídeos trancados até registrar</span>
          </>
        ),
    },
    {
      id: "ultimos",
      header: "Últimos 30 dias",
      cell: (item: Motorista) => (
        <>
          <span className="block leading-5">{plural(item.viagens_30d, "viagem", "viagens")}</span>
          <span className="block text-[13px] leading-4 text-grafite">{textoMomentos(item.confirmados_30d)}</span>
        </>
      ),
    },
  ];

  function card(item: Motorista) {
    const cnh = avisoCnh(item.cnh_validade, hoje);
    return (
      <>
        <CardTitulo titulo={item.nome} detalhe={`Matrícula ${item.matricula}`} />
        <span className="grid gap-1.5">
          <CardInfo rotulo="CNH" alarme={cnh.alarme}>
            {cnh.alarme ? cnh.curto : `Categoria ${item.cnh_categoria} · até ${mesAno(item.cnh_validade)}`}
          </CardInfo>
          <CardInfo rotulo="Termo" alarme={!item.termo.assinado}>
            {item.termo.assinado ? termoCurto(item) : "Falta registrar"}
          </CardInfo>
          <CardInfo rotulo="Últimos 30 dias">{plural(item.viagens_30d, "viagem", "viagens")}</CardInfo>
        </span>
      </>
    );
  }

  function conteudoDaJanela() {
    if (!janela) return null;
    if (janela.modo === "novo") {
      return (
        <DriverForm
          key={`novo-${abertura}`}
          formId={FORM_ID}
          motorista={null}
          outros={todos}
          readOnly={!podeEditar}
          onSaved={(salvo) => aoSalvar(salvo, true)}
          onStateChange={setSalvando}
        />
      );
    }
    if (!motorista) return null;
    if (janela.modo === "editar") {
      return (
        <DriverForm
          key={`editar-${motorista.id}-${abertura}`}
          formId={FORM_ID}
          motorista={motorista}
          outros={todos.filter((item) => item.id !== motorista.id)}
          readOnly={!podeEditar}
          onSaved={(salvo) => aoSalvar(salvo, false)}
          onStateChange={setSalvando}
        />
      );
    }
    return (
      <DriverDetails
        key={`ver-${motorista.id}-${abertura}`}
        motorista={motorista}
        hoje={hoje}
        podeCadastrar={podeEditar}
        destacarTermo={janela.recemCadastrado}
        onChanged={atualizarNaLista}
      />
    );
  }

  function rodapeDaJanela() {
    if (!janela) return undefined;
    if (janela.modo === "ver") {
      return (
        <>
          {podeEditar && (
            <button type="button" className="btn" onClick={() => editar(janela.id)}>
              Editar
            </button>
          )}
          <button type="button" className="btn" onClick={fechar}>
            Fechar
          </button>
        </>
      );
    }
    const voltarPara = janela.modo === "editar" ? janela.id : null;
    return (
      <>
        <SaveButton state={salvando} type="submit" form={FORM_ID}>
          Salvar motorista
        </SaveButton>
        <button
          type="button"
          className="btn"
          onClick={() => (voltarPara === null ? fechar() : setJanela({ modo: "ver", id: voltarPara, recemCadastrado: false }))}
        >
          Cancelar
        </button>
      </>
    );
  }

  return (
    <section className="anim-enter px-14 pb-16 pt-[34px]">
      <PageHeader
        title="Motoristas"
        summary={lista ? resumo(lista, hoje) : erro ? "Não deu para carregar" : "Carregando…"}
        guide={{ capitulo: "motoristas" }}
        actions={
          podeEditar ? (
            <button type="button" className="btn btn-primary" onClick={abrirNovo}>
              Cadastrar motorista <Kbd>Ctrl N</Kbd>
            </button>
          ) : undefined
        }
      />

      <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
        <Tabs
          items={ABAS.map((id) => ({ id, label: NOME_ABA[id], count: todos.filter((item) => item.situacao === id).length }))}
          value={aba}
          onChange={(id: string) => {
            setAba(id as Aba);
            setSelecionado(null);
          }}
        />
        <div className="flex items-center gap-2">
          <label className="relative block w-[280px]">
            <span className="sr-only">Buscar motorista</span>
            <input
              ref={buscaRef}
              type="text"
              enterKeyHint="search"
              className="input pr-10"
              placeholder="Buscar por nome ou matrícula"
              value={busca}
              onChange={(evento) => setBusca(evento.target.value)}
              onKeyDown={(evento) => {
                if (evento.key !== "Escape") return;
                setBusca("");
                evento.currentTarget.blur();
              }}
            />
            <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2">
              <Kbd>/</Kbd>
            </span>
          </label>
          <ViewToggle value={visao} onChange={setVisao} />
        </div>
      </div>

      {erro ? (
        <p role="alert" className="mt-6 flex items-center gap-3 text-[14px] text-alarme">
          {erro}
          <button type="button" className="btn btn-small" onClick={tentarDeNovo}>
            Tentar de novo
          </button>
        </p>
      ) : (
        <div key={visao} className="anim-enter mt-4">
          {visao === "lista" ? (
            <DataTable
              columns={colunas}
              rows={linhas}
              getRowId={(item: Motorista) => String(item.id)}
              selectedId={selecionado}
              onSelect={(id) => setSelecionado(String(id))}
              onOpen={abrir}
              label="Motoristas"
              empty={vazio}
            />
          ) : (
            <CardGrid
              items={linhas}
              getId={(item: Motorista) => String(item.id)}
              selectedId={selecionado}
              onSelect={setSelecionado}
              onOpen={abrir}
              renderCard={card}
              label="Motoristas"
              empty={vazio}
            />
          )}
        </div>
      )}

      <Dialog
        width={600}
        open={aberta && (janela?.modo === "novo" || motorista !== null)}
        onClose={fechar}
        title={janela?.modo === "novo" ? "Cadastrar motorista" : (motorista?.nome ?? "")}
        summary={
          janela?.modo === "novo"
            ? "O nome e a matrícula aparecem nos relatórios das viagens."
            : motorista
              ? `Matrícula ${motorista.matricula} · ${janela?.modo === "editar" ? "Editando o cadastro" : SITUACAO_MOTORISTA[motorista.situacao]}`
              : undefined
        }
        footer={rodapeDaJanela()}
      >
        {conteudoDaJanela()}
      </Dialog>
    </section>
  );
}
