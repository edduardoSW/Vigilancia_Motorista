"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { SaveState } from "@/components/drivers/driver-form";
import { plural, useListShortcuts } from "@/components/drivers/use-list-shortcuts";
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
import { veiculoDe, type SituacaoVeiculo } from "@/content";
import { bridge, type Caixa, type Veiculo } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { BoxDrawer } from "./box-drawer";
import { VehicleDetails } from "./vehicle-details";
import { VehicleForm } from "./vehicle-form";
import { nomeDoVeiculo, quando, SITUACAO_CAIXA, SITUACAO_VEICULO, TRANSPORTA } from "./vehicle-labels";

// Veículos e caixas (prévia 6, specs 015 e 019): duas abas, cada uma em lista ou cards, e a janela no centro.
// Abrir um veículo mostra os dados; "Editar" troca para o formulário na mesma janela (INT-01). A caixa abre a janela
// de troca de veículo. A coluna "Agora" ainda vem do demo.json enquanto a leitura da caixa de verdade não chega.

type Aba = "veiculos" | "caixas";
/** O que a janela do veículo mostra: o formulário do cadastro novo, os dados ou o formulário para editar. */
type Janela = { modo: "novo" } | { modo: "ver"; id: number } | { modo: "editar"; id: number };

const AGORA: Record<SituacaoVeiculo, string> = {
  atencao: "Precisa de atenção",
  importando: "Caixa conectada agora",
  coletada: "Viagem para verificar",
  em_viagem: "Em viagem",
  pronta: "Pronto para sair",
  revisada: "Tudo verificado",
};

const FORM_ID = "form-veiculo";

function agora(veiculo: Veiculo, caixa: Caixa | undefined) {
  if (veiculo.situacao !== "em_uso") return { texto: SITUACAO_VEICULO[veiculo.situacao], alarme: false, lendo: false };
  if (!caixa) return { texto: "Sem caixa instalada", alarme: false, lendo: false };
  if (caixa.situacao === "bloqueada") return { texto: "Caixa bloqueada", alarme: true, lendo: false };
  if (caixa.situacao === "atencao") return { texto: "Precisa de atenção", alarme: true, lendo: false };
  const demo = veiculoDe(veiculo.numero);
  if (!demo || demo.situacao === "atencao") return { texto: "Sem novidade", alarme: false, lendo: false };
  return { texto: AGORA[demo.situacao], alarme: false, lendo: demo.situacao === "importando" };
}

/** "7 veículos · 8 caixas, 1 sem veículo · 1 precisa de atenção". */
function resumo(veiculos: Veiculo[], caixas: Caixa[]) {
  const emUso = veiculos.filter((veiculo) => veiculo.situacao !== "fora_de_uso").length;
  const livres = caixas.filter((caixa) => caixa.veiculo_id === null && caixa.situacao !== "bloqueada").length;
  const atencao = caixas.filter((caixa) => caixa.situacao === "atencao").length;
  const partes = [plural(emUso, "veículo", "veículos"), `${plural(caixas.length, "caixa", "caixas")}${livres ? `, ${livres} sem veículo` : ""}`];
  if (atencao) partes.push(`${atencao} ${atencao === 1 ? "precisa" : "precisam"} de atenção`);
  return partes.join(" · ");
}

export function VehiclesScreen() {
  const { pode } = useSession();
  const podeEditar = pode("cadastrar");
  const { toast } = useToast();
  const [visaoVeiculos, setVisaoVeiculos] = useVisao("veiculos");
  const [visaoCaixas, setVisaoCaixas] = useVisao("caixas");
  const [veiculos, setVeiculos] = useState<Veiculo[] | null>(null);
  const [caixas, setCaixas] = useState<Caixa[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState<Aba>("veiculos");
  const [selVeiculo, setSelVeiculo] = useState<string | null>(null);
  const [selCaixa, setSelCaixa] = useState<string | null>(null);
  const [janela, setJanela] = useState<Janela | null>(null);
  const [aberta, setAberta] = useState(false);
  // Cada abertura (veículo ou caixa) começa do zero; ao fechar, o conteúdo fica até a janela terminar de sumir.
  const [abertura, setAbertura] = useState(0);
  const [caixaAberta, setCaixaAberta] = useState<number | null>(null);
  const [caixaVisivel, setCaixaVisivel] = useState(false);
  const [salvando, setSalvando] = useState<SaveState>("idle");
  const [verForaDeUso, setVerForaDeUso] = useState(false);

  useEffect(() => {
    let vivo = true;
    Promise.all([bridge.veiculos_listar(), bridge.caixas_listar()]).then(([rv, rc]) => {
      if (!vivo) return;
      if (!rv.ok) return setErro(rv.erro);
      if (!rc.ok) return setErro(rc.erro);
      setVeiculos(rv.dados);
      setCaixas(rc.dados);
    });
    return () => {
      vivo = false;
    };
  }, []);

  // A busca rápida (Ctrl+K) pede para abrir um veículo com ?abrir=<id>. Ajuste na renderização, sem efeito.
  const params = useSearchParams();
  const pedido = params.get("abrir") ? params.toString() : null;
  const [pedidoAtendido, setPedidoAtendido] = useState<string | null>(null);
  if (pedido && veiculos && pedido !== pedidoAtendido) {
    setPedidoAtendido(pedido);
    const escolhido = veiculos.find((veiculo) => String(veiculo.id) === params.get("abrir"));
    if (escolhido) {
      setAba("veiculos");
      abrirVeiculo(escolhido);
    }
  }

  async function recarregar() {
    const [rv, rc] = await Promise.all([bridge.veiculos_listar(), bridge.caixas_listar()]);
    if (!rv.ok) return setErro(rv.erro);
    if (!rc.ok) return setErro(rc.erro);
    setErro(null);
    setVeiculos(rv.dados);
    setCaixas(rc.dados);
  }

  const lista = veiculos ?? [];
  const listaCaixas = caixas ?? [];
  const caixaDe = (veiculo: Veiculo) => listaCaixas.find((caixa) => caixa.id === veiculo.caixa_id);
  const veiculoAberto = janela && janela.modo !== "novo" ? (lista.find((veiculo) => veiculo.id === janela.id) ?? null) : null;
  const caixaAbertaObj = listaCaixas.find((caixa) => caixa.id === caixaAberta) ?? null;
  const foraDeUso = lista.filter((veiculo) => veiculo.situacao === "fora_de_uso").length;
  const carregado = veiculos !== null && caixas !== null;
  const visao = aba === "veiculos" ? visaoVeiculos : visaoCaixas;

  const linhasVeiculos = lista
    .filter((veiculo) => verForaDeUso || veiculo.situacao !== "fora_de_uso")
    .map((veiculo) => ({ veiculo, agora: agora(veiculo, caixaDe(veiculo)) }))
    .sort((a, b) => Number(b.agora.alarme) - Number(a.agora.alarme) || a.veiculo.numero.localeCompare(b.veiculo.numero, "pt-BR", { numeric: true }))
    .map(({ veiculo }) => veiculo);
  const linhasCaixas = [...listaCaixas].sort(
    (a, b) => Number(b.situacao !== "ok") - Number(a.situacao !== "ok") || a.codigo.localeCompare(b.codigo, "pt-BR", { numeric: true }),
  );
  const vazioVeiculos = carregado ? "Nenhum veículo cadastrado ainda." : "Carregando…";
  const vazioCaixas = carregado ? "Nenhuma caixa ainda. As caixas vêm do arquivo da empresa." : "Carregando…";

  function abrirNovo() {
    setAba("veiculos");
    setSalvando("idle");
    setAbertura((valor) => valor + 1);
    setJanela({ modo: "novo" });
    setAberta(true);
  }

  function abrirVeiculo(veiculo: Veiculo) {
    setSelVeiculo(String(veiculo.id));
    setAbertura((valor) => valor + 1);
    setJanela({ modo: "ver", id: veiculo.id });
    setAberta(true);
  }

  function editar(id: number) {
    setSalvando("idle");
    setJanela({ modo: "editar", id });
  }

  function abrirCaixa(caixa: Caixa) {
    setSelCaixa(String(caixa.id));
    setCaixaAberta(caixa.id);
    setAbertura((valor) => valor + 1);
    setCaixaVisivel(true);
  }

  const fechar = () => setAberta(false);

  useListShortcuts({ onNew: podeEditar ? abrirNovo : undefined, enabled: !aberta && !caixaVisivel });

  async function aoSalvarVeiculo(salvo: Veiculo, novo: boolean) {
    setVeiculos((atual) => {
      const base = atual ?? [];
      return base.some((item) => item.id === salvo.id) ? base.map((item) => (item.id === salvo.id ? salvo : item)) : [...base, salvo];
    });
    setSelVeiculo(String(salvo.id));
    toast({ text: novo ? "Veículo cadastrado" : "Veículo salvo" });
    // Salvou: a janela volta para os dados do veículo.
    setJanela({ modo: "ver", id: salvo.id });
    // A caixa escolhida sai da lista de livres (e de outro veículo, se estava lá).
    await recarregar();
  }

  async function aoVincular(caixa: Caixa, anterior: number | null) {
    await recarregar();
    const destino = lista.find((veiculo) => veiculo.id === caixa.veiculo_id);
    toast({
      text: destino ? `Caixa ${caixa.codigo} vinculada ao veículo ${destino.numero}` : `Caixa ${caixa.codigo} ficou sem veículo`,
      action: {
        label: "Desfazer",
        onClick: async () => {
          const resposta = await bridge.caixa_vincular(caixa.id, anterior);
          if (!resposta.ok) return toast({ text: resposta.erro });
          await recarregar();
          toast({ text: "Troca desfeita" });
        },
      },
    });
  }

  const colunasVeiculos = [
    {
      id: "veiculo",
      header: "Veículo",
      cell: (veiculo: Veiculo) => (
        <>
          <b className="block font-semibold leading-5">{nomeDoVeiculo(veiculo)}</b>
          <span className="block text-[13px] leading-4 text-grafite">{veiculo.modelo ?? "Sem modelo informado"}</span>
        </>
      ),
    },
    { id: "placa", header: "Placa", width: "14%", cell: (veiculo: Veiculo) => veiculo.placa },
    { id: "transporta", header: "Transporta", width: "14%", cell: (veiculo: Veiculo) => TRANSPORTA[veiculo.transporta].rotulo },
    {
      id: "caixa",
      header: "Caixa",
      cell: (veiculo: Veiculo) => {
        const caixa = caixaDe(veiculo);
        return caixa ? caixa.codigo : <span className="text-grafite">Sem caixa</span>;
      },
    },
    {
      id: "agora",
      header: "Agora",
      cell: (veiculo: Veiculo) => {
        const situacao = agora(veiculo, caixaDe(veiculo));
        return (
          <span className={cn("inline-flex items-center gap-2", situacao.alarme && "font-semibold text-alarme")}>
            {situacao.lendo && <span aria-hidden="true" className="pulse-dot size-2 rounded-full bg-verde" />}
            {situacao.texto}
          </span>
        );
      },
    },
  ];

  const colunasCaixas = [
    { id: "caixa", header: "Caixa", width: "12%", cell: (caixa: Caixa) => <b className="font-semibold">{caixa.codigo}</b> },
    {
      id: "veiculo",
      header: "Veículo",
      cell: (caixa: Caixa) => {
        const veiculo = lista.find((item) => item.id === caixa.veiculo_id);
        return veiculo ? nomeDoVeiculo(veiculo) : <span className="text-grafite">Sem veículo</span>;
      },
    },
    {
      id: "situacao",
      header: "Situação",
      width: "36%",
      cell: (caixa: Caixa) =>
        caixa.situacao === "ok" ? (
          SITUACAO_CAIXA.ok
        ) : (
          <>
            <span className="block font-semibold leading-5 text-alarme">{SITUACAO_CAIXA[caixa.situacao]}</span>
            <span className="block max-w-[420px] truncate text-[13px] leading-4 text-grafite" title={caixa.detalhe ?? undefined}>
              {caixa.detalhe ?? (caixa.situacao === "bloqueada" ? "Não importa viagem." : "")}
            </span>
          </>
        ),
    },
    { id: "coleta", header: "Última coleta", cell: (caixa: Caixa) => quando(caixa.ultima_coleta) ?? <span className="text-grafite">Nunca coletada</span> },
    { id: "versao", header: "Versão", cell: (caixa: Caixa) => caixa.versao ?? <span className="text-grafite">—</span> },
  ];

  function cardVeiculo(veiculo: Veiculo) {
    const caixa = caixaDe(veiculo);
    const situacao = agora(veiculo, caixa);
    return (
      <>
        <CardTitulo titulo={nomeDoVeiculo(veiculo)} detalhe={`Placa ${veiculo.placa}`} />
        <span className="grid gap-1.5">
          <CardInfo rotulo="Caixa">{caixa ? caixa.codigo : <span className="text-grafite">Sem caixa</span>}</CardInfo>
          <CardInfo rotulo="Transporta">{TRANSPORTA[veiculo.transporta].rotulo}</CardInfo>
          <CardInfo rotulo="Agora" alarme={situacao.alarme}>
            {situacao.texto}
          </CardInfo>
        </span>
      </>
    );
  }

  function cardCaixa(caixa: Caixa) {
    const veiculo = lista.find((item) => item.id === caixa.veiculo_id);
    const motivo = caixa.situacao === "ok" ? null : (caixa.detalhe ?? (caixa.situacao === "bloqueada" ? "Não importa viagem." : null));
    return (
      <>
        <CardTitulo titulo={caixa.codigo} detalhe={veiculo ? nomeDoVeiculo(veiculo) : "Sem veículo"} />
        <span className="grid gap-1.5">
          <CardInfo rotulo="Situação" alarme={caixa.situacao !== "ok"}>
            {SITUACAO_CAIXA[caixa.situacao]}
          </CardInfo>
          <CardInfo rotulo="Última coleta">{quando(caixa.ultima_coleta) ?? <span className="text-grafite">Nunca coletada</span>}</CardInfo>
          <CardInfo rotulo="Versão">{caixa.versao ?? <span className="text-grafite">Não informada</span>}</CardInfo>
        </span>
        {motivo && <span className="line-clamp-2 text-[13px] text-grafite">{motivo}</span>}
      </>
    );
  }

  function conteudoDaJanela() {
    if (!janela) return null;
    if (janela.modo === "novo") {
      return (
        <VehicleForm
          key={`novo-${abertura}`}
          formId={FORM_ID}
          veiculo={null}
          outros={lista}
          caixas={listaCaixas}
          readOnly={!podeEditar}
          onSaved={(salvo) => aoSalvarVeiculo(salvo, true)}
          onStateChange={setSalvando}
        />
      );
    }
    if (!veiculoAberto) return null;
    if (janela.modo === "editar") {
      return (
        <VehicleForm
          key={`editar-${veiculoAberto.id}-${abertura}`}
          formId={FORM_ID}
          veiculo={veiculoAberto}
          outros={lista.filter((veiculo) => veiculo.id !== veiculoAberto.id)}
          caixas={listaCaixas}
          readOnly={!podeEditar}
          onSaved={(salvo) => aoSalvarVeiculo(salvo, false)}
          onStateChange={setSalvando}
        />
      );
    }
    const caixa = caixaDe(veiculoAberto);
    return <VehicleDetails veiculo={veiculoAberto} caixa={caixa} agora={agora(veiculoAberto, caixa)} podeCadastrar={podeEditar} />;
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
          Salvar veículo
        </SaveButton>
        <button type="button" className="btn" onClick={() => (voltarPara === null ? fechar() : setJanela({ modo: "ver", id: voltarPara }))}>
          Cancelar
        </button>
      </>
    );
  }

  return (
    <section className="anim-enter px-14 pb-16 pt-[34px]">
      <PageHeader
        title="Veículos e caixas"
        summary={carregado ? resumo(lista, listaCaixas) : erro ? "Não deu para carregar" : "Carregando…"}
        guide={{ capitulo: "veiculos" }}
        actions={
          podeEditar ? (
            <button type="button" className="btn btn-primary" onClick={abrirNovo}>
              Cadastrar veículo <Kbd>Ctrl N</Kbd>
            </button>
          ) : undefined
        }
      />

      <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
        <Tabs
          items={[
            { id: "veiculos", label: "Veículos", count: lista.length - (verForaDeUso ? 0 : foraDeUso) },
            { id: "caixas", label: "Caixas", count: listaCaixas.length },
          ]}
          value={aba}
          onChange={(id: string) => setAba(id as Aba)}
        />
        <ViewToggle value={visao} onChange={aba === "veiculos" ? setVisaoVeiculos : setVisaoCaixas} />
      </div>

      {erro ? (
        <p role="alert" className="mt-6 flex items-center gap-3 text-[14px] text-alarme">
          {erro}
          <button type="button" className="btn btn-small" onClick={recarregar}>
            Tentar de novo
          </button>
        </p>
      ) : aba === "veiculos" ? (
        <div key={`veiculos-${visao}`} className="anim-enter mt-4">
          {visao === "lista" ? (
            <DataTable
              columns={colunasVeiculos}
              rows={linhasVeiculos}
              getRowId={(veiculo: Veiculo) => String(veiculo.id)}
              selectedId={selVeiculo}
              onSelect={(id) => setSelVeiculo(String(id))}
              onOpen={abrirVeiculo}
              label="Veículos"
              empty={vazioVeiculos}
            />
          ) : (
            <CardGrid
              items={linhasVeiculos}
              getId={(veiculo: Veiculo) => String(veiculo.id)}
              selectedId={selVeiculo}
              onSelect={setSelVeiculo}
              onOpen={abrirVeiculo}
              renderCard={cardVeiculo}
              label="Veículos"
              empty={vazioVeiculos}
            />
          )}
          {foraDeUso > 0 && (
            <button type="button" className="mt-3 text-[13px] font-semibold text-grafite hover:text-tinta" onClick={() => setVerForaDeUso((ver) => !ver)}>
              {verForaDeUso ? "Esconder os fora de uso" : `Mostrar ${plural(foraDeUso, "veículo fora de uso", "veículos fora de uso")}`}
            </button>
          )}
        </div>
      ) : (
        <div key={`caixas-${visao}`} className="anim-enter mt-4">
          {visao === "lista" ? (
            <DataTable
              columns={colunasCaixas}
              rows={linhasCaixas}
              getRowId={(caixa: Caixa) => String(caixa.id)}
              selectedId={selCaixa}
              onSelect={(id) => setSelCaixa(String(id))}
              onOpen={abrirCaixa}
              label="Caixas"
              empty={vazioCaixas}
            />
          ) : (
            <CardGrid
              items={linhasCaixas}
              getId={(caixa: Caixa) => String(caixa.id)}
              selectedId={selCaixa}
              onSelect={setSelCaixa}
              onOpen={abrirCaixa}
              renderCard={cardCaixa}
              label="Caixas"
              empty={vazioCaixas}
            />
          )}
        </div>
      )}

      <Dialog
        width={600}
        open={aberta && (janela?.modo === "novo" || veiculoAberto !== null)}
        onClose={fechar}
        title={janela?.modo === "novo" ? "Cadastrar veículo" : veiculoAberto ? nomeDoVeiculo(veiculoAberto) : ""}
        summary={
          janela?.modo === "novo"
            ? "Depois de salvar, a caixa escolhida passa a ser deste veículo."
            : veiculoAberto
              ? `Placa ${veiculoAberto.placa} · ${janela?.modo === "editar" ? "Editando o cadastro" : SITUACAO_VEICULO[veiculoAberto.situacao]}`
              : undefined
        }
        footer={rodapeDaJanela()}
      >
        {conteudoDaJanela()}
      </Dialog>

      <BoxDrawer
        open={caixaVisivel}
        abertura={abertura}
        caixa={caixaAbertaObj}
        caixas={listaCaixas}
        veiculos={lista}
        readOnly={!podeEditar}
        onClose={() => setCaixaVisivel(false)}
        onLinked={aoVincular}
      />
    </section>
  );
}
