"use client";

import { useEffect, useRef, useState } from "react";
import { DriverForm, SITUACAO_MOTORISTA, type SaveState } from "@/components/drivers/driver-form";
import { plural, semAcento, useListShortcuts } from "@/components/drivers/use-list-shortcuts";
import { useSession } from "@/components/session-provider";
import { DataTable } from "@/components/ui/data-table";
import { Drawer } from "@/components/ui/drawer";
import { Kbd } from "@/components/ui/kbd";
import { PageHeader } from "@/components/ui/page-header";
import { SaveButton } from "@/components/ui/save-button";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { bridge, type Motorista } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { diasAte, formatarData, hojeIso, mascararCpf, mesAno, situacaoCnh } from "@/lib/validators";

// Motoristas (prévia 4 e spec 015): lista densa por situação, busca e painel lateral para ver, editar e cadastrar.
// Consulta vê tudo só para leitura; cadastrar e exportar são de administrador e supervisor (spec 014).

type Aba = Motorista["situacao"];
type Aberto = { tipo: "novo" } | { tipo: "editar"; id: number } | null;

const ABAS: Aba[] = ["ativo", "afastado", "desligado"];
const NOME_ABA: Record<Aba, string> = { ativo: "Ativos", afastado: "Afastados", desligado: "Desligados" };
const VAZIO: Record<Aba, string> = {
  ativo: "Nenhum motorista ativo ainda.",
  afastado: "Nenhum motorista afastado.",
  desligado: "Nenhum motorista desligado.",
};
const FORM_ID = "form-motorista";

const momentos = (total: number) => (total === 0 ? "Nenhum momento confirmado" : plural(total, "momento confirmado", "momentos confirmados"));

function validade(motorista: Motorista, hoje: string) {
  const data = motorista.cnh_validade;
  const situacao = situacaoCnh(data, hoje);
  if (situacao === "vencida") return { texto: `Vencida em ${formatarData(data)}`, alarme: true };
  if (situacao === "vence_em_breve") {
    const dias = diasAte(data, hoje);
    return { texto: `${dias === 0 ? "Vence hoje" : `Vence em ${plural(dias, "dia", "dias")}`} (${formatarData(data)})`, alarme: true };
  }
  return { texto: `Vale até ${mesAno(data)}`, alarme: false };
}

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
  const [lista, setLista] = useState<Motorista[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState<Aba>("ativo");
  const [busca, setBusca] = useState("");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [aberto, setAberto] = useState<Aberto>(null);
  const [salvando, setSalvando] = useState<SaveState>("idle");
  const [versaoForm, setVersaoForm] = useState(0);
  const [exportando, setExportando] = useState(false);
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

  async function tentarDeNovo() {
    setErro(null);
    const resposta = await bridge.motoristas_listar();
    if (resposta.ok) setLista(resposta.dados);
    else setErro(resposta.erro);
  }

  const todos = lista ?? [];
  const motorista = aberto?.tipo === "editar" ? (todos.find((item) => item.id === aberto.id) ?? null) : null;
  const termo = semAcento(busca.trim());
  const linhas = todos
    .filter((item) => item.situacao === aba)
    .filter((item) => !termo || semAcento(`${item.nome} ${item.nome_curto} ${item.matricula}`).includes(termo))
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));

  function abrirNovo() {
    setSalvando("idle");
    setVersaoForm((versao) => versao + 1);
    setAberto({ tipo: "novo" });
  }

  function abrir(item: Motorista) {
    setSelecionado(String(item.id));
    setSalvando("idle");
    setVersaoForm((versao) => versao + 1);
    setAberto({ tipo: "editar", id: item.id });
  }

  const fechar = () => setAberto(null);

  useListShortcuts({ onNew: podeEditar ? abrirNovo : undefined, searchRef: buscaRef, enabled: !aberto });

  function aoSalvar(salvo: Motorista) {
    setLista((atual) => {
      const base = atual ?? [];
      return base.some((item) => item.id === salvo.id) ? base.map((item) => (item.id === salvo.id ? salvo : item)) : [...base, salvo];
    });
    setAba(salvo.situacao);
    setSelecionado(String(salvo.id));
    toast({ text: "Motorista salvo" });
    // Cadastro novo fecha e a linha entra na lista; edição fica aberta mostrando "Salvo".
    if (aberto?.tipo === "novo") setAberto(null);
  }

  async function exportar(item: Motorista) {
    setExportando(true);
    const resposta = await bridge.motorista_exportar(item.id);
    setExportando(false);
    if (!resposta.ok) {
      toast({ text: resposta.erro });
      return;
    }
    toast({ text: `Dados de ${item.nome_curto} salvos em ${resposta.dados.caminho}` });
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
        const aviso = validade(item, hoje);
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
          <span className="block leading-5">{item.termo.data ? `Assinado em ${formatarData(item.termo.data)}` : "Assinado"}</span>
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
          <span className="block text-[13px] leading-4 text-grafite">{momentos(item.confirmados_30d)}</span>
        </>
      ),
    },
  ];

  const cnhAberta = motorista ? validade(motorista, hoje) : null;

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
        <label className="relative block w-[300px]">
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
      </div>

      {erro ? (
        <p role="alert" className="mt-6 flex items-center gap-3 text-[14px] text-alarme">
          {erro}
          <button type="button" className="btn btn-small" onClick={tentarDeNovo}>
            Tentar de novo
          </button>
        </p>
      ) : (
        <div className="mt-3">
          <DataTable
            columns={colunas}
            rows={linhas}
            getRowId={(item: Motorista) => String(item.id)}
            selectedId={selecionado}
            onSelect={(id) => setSelecionado(String(id))}
            onOpen={abrir}
            empty={lista === null ? "Carregando…" : busca.trim() ? `Nenhum motorista encontrado para "${busca.trim()}".` : VAZIO[aba]}
          />
        </div>
      )}

      <Drawer
        width={540}
        open={Boolean(aberto)}
        onClose={fechar}
        title={aberto?.tipo === "novo" ? "Cadastrar motorista" : (motorista?.nome ?? "")}
        summary={
          aberto?.tipo === "novo"
            ? "O nome e a matrícula aparecem nos relatórios das viagens."
            : motorista
              ? `Matrícula ${motorista.matricula} · ${SITUACAO_MOTORISTA[motorista.situacao]}`
              : undefined
        }
        footer={
          podeEditar ? (
            <>
              <SaveButton state={salvando} type="submit" form={FORM_ID}>
                Salvar motorista
              </SaveButton>
              <button type="button" className="btn" onClick={fechar}>
                Cancelar
              </button>
            </>
          ) : (
            <button type="button" className="btn" onClick={fechar}>
              Fechar
            </button>
          )
        }
      >
        {motorista && cnhAberta && (
          <div className="mb-6 border-b border-fio pb-5">
            <dl className="grid grid-cols-[130px_minmax(0,1fr)] gap-y-2 text-[13.5px]">
              <dt className="text-grafite">Últimos 30 dias</dt>
              <dd>
                {plural(motorista.viagens_30d, "viagem", "viagens")} · {momentos(motorista.confirmados_30d).toLowerCase()}
              </dd>
              <dt className="text-grafite">Carteira</dt>
              <dd className={cn(cnhAberta.alarme && "font-semibold text-alarme")}>
                Categoria {motorista.cnh_categoria} · {cnhAberta.texto}
              </dd>
              <dt className="text-grafite">Termo</dt>
              <dd className={cn(!motorista.termo.assinado && "font-semibold text-alarme")}>
                {motorista.termo.assinado
                  ? `Assinado${motorista.termo.data ? ` em ${formatarData(motorista.termo.data)}` : ""}${motorista.termo.versao ? `, versão ${motorista.termo.versao}` : ""}`
                  : "Falta registrar. Os vídeos das viagens ficam trancados até registrar."}
              </dd>
              {motorista.cpf && (
                <>
                  <dt className="text-grafite">CPF</dt>
                  <dd>{mascararCpf(motorista.cpf)}</dd>
                </>
              )}
            </dl>
            {podeEditar && (
              <button type="button" className="btn btn-small mt-4" disabled={exportando} onClick={() => exportar(motorista)}>
                {exportando ? "Exportando…" : "Exportar dados deste motorista"}
              </button>
            )}
          </div>
        )}
        {(aberto?.tipo === "novo" || motorista) && (
          <DriverForm
            key={versaoForm}
            formId={FORM_ID}
            motorista={motorista}
            outros={todos.filter((item) => item.id !== motorista?.id)}
            readOnly={!podeEditar}
            onSaved={aoSalvar}
            onStateChange={setSalvando}
          />
        )}
      </Drawer>
    </section>
  );
}
