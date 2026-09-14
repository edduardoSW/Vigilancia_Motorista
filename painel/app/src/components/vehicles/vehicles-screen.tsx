"use client";

import { useEffect, useState } from "react";
import type { SaveState } from "@/components/drivers/driver-form";
import { plural, useListShortcuts } from "@/components/drivers/use-list-shortcuts";
import { useSession } from "@/components/session-provider";
import { DataTable } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { Drawer } from "@/components/ui/drawer";
import { Kbd } from "@/components/ui/kbd";
import { PageHeader } from "@/components/ui/page-header";
import { SaveButton } from "@/components/ui/save-button";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { veiculoDe, type SituacaoVeiculo } from "@/content";
import { bridge, type Caixa, type Veiculo } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { BoxDrawer } from "./box-drawer";
import { VehicleForm } from "./vehicle-form";
import { nomeDoVeiculo, quando, SITUACAO_CAIXA, SITUACAO_VEICULO, TRANSPORTA } from "./vehicle-labels";

// Veículos e caixas (prévia 6 e spec 015): duas abas, cadastro no diálogo, edição e troca de caixa no painel lateral.
// A coluna "Agora" ainda vem do demo.json enquanto a leitura da caixa de verdade não chega.

type Aba = "veiculos" | "caixas";

const AGORA: Record<SituacaoVeiculo, string> = {
  atencao: "Precisa de atenção",
  importando: "Caixa conectada agora",
  coletada: "Viagem para verificar",
  em_viagem: "Em viagem",
  pronta: "Pronto para sair",
  revisada: "Tudo verificado",
};

const FORM_NOVO = "form-veiculo-novo";
const FORM_EDITAR = "form-veiculo";

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
  const [veiculos, setVeiculos] = useState<Veiculo[] | null>(null);
  const [caixas, setCaixas] = useState<Caixa[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState<Aba>("veiculos");
  const [selVeiculo, setSelVeiculo] = useState<string | null>(null);
  const [selCaixa, setSelCaixa] = useState<string | null>(null);
  const [novo, setNovo] = useState(false);
  const [editando, setEditando] = useState<number | null>(null);
  const [caixaAberta, setCaixaAberta] = useState<number | null>(null);
  const [salvando, setSalvando] = useState<SaveState>("idle");
  const [versaoForm, setVersaoForm] = useState(0);
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
  const veiculoAberto = lista.find((veiculo) => veiculo.id === editando) ?? null;
  const caixaAbertaObj = listaCaixas.find((caixa) => caixa.id === caixaAberta) ?? null;
  const foraDeUso = lista.filter((veiculo) => veiculo.situacao === "fora_de_uso").length;

  const linhasVeiculos = lista
    .filter((veiculo) => verForaDeUso || veiculo.situacao !== "fora_de_uso")
    .map((veiculo) => ({ veiculo, agora: agora(veiculo, caixaDe(veiculo)) }))
    .sort((a, b) => Number(b.agora.alarme) - Number(a.agora.alarme) || a.veiculo.numero.localeCompare(b.veiculo.numero, "pt-BR", { numeric: true }))
    .map(({ veiculo }) => veiculo);
  const linhasCaixas = [...listaCaixas].sort(
    (a, b) => Number(b.situacao !== "ok") - Number(a.situacao !== "ok") || a.codigo.localeCompare(b.codigo, "pt-BR", { numeric: true }),
  );

  function abrirNovo() {
    setAba("veiculos");
    setSalvando("idle");
    setVersaoForm((versao) => versao + 1);
    setNovo(true);
  }

  function abrirVeiculo(veiculo: Veiculo) {
    setSelVeiculo(String(veiculo.id));
    setSalvando("idle");
    setVersaoForm((versao) => versao + 1);
    setEditando(veiculo.id);
  }

  function abrirCaixa(caixa: Caixa) {
    setSelCaixa(String(caixa.id));
    setCaixaAberta(caixa.id);
  }

  useListShortcuts({ onNew: podeEditar ? abrirNovo : undefined, enabled: !novo && editando === null && caixaAberta === null });

  async function aoSalvarVeiculo(salvo: Veiculo) {
    setVeiculos((atual) => {
      const base = atual ?? [];
      return base.some((item) => item.id === salvo.id) ? base.map((item) => (item.id === salvo.id ? salvo : item)) : [...base, salvo];
    });
    setSelVeiculo(String(salvo.id));
    toast({ text: "Veículo salvo" });
    if (novo) setNovo(false);
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

  const carregado = veiculos !== null && caixas !== null;

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

      <div className="mt-6">
        <Tabs
          items={[
            { id: "veiculos", label: "Veículos", count: lista.length - (verForaDeUso ? 0 : foraDeUso) },
            { id: "caixas", label: "Caixas", count: listaCaixas.length },
          ]}
          value={aba}
          onChange={(id: string) => setAba(id as Aba)}
        />
      </div>

      {erro ? (
        <p role="alert" className="mt-6 flex items-center gap-3 text-[14px] text-alarme">
          {erro}
          <button type="button" className="btn btn-small" onClick={recarregar}>
            Tentar de novo
          </button>
        </p>
      ) : aba === "veiculos" ? (
        <div key="veiculos" className="anim-enter mt-3">
          <DataTable
            columns={colunasVeiculos}
            rows={linhasVeiculos}
            getRowId={(veiculo: Veiculo) => String(veiculo.id)}
            selectedId={selVeiculo}
            onSelect={(id) => setSelVeiculo(String(id))}
            onOpen={abrirVeiculo}
            empty={carregado ? "Nenhum veículo cadastrado ainda." : "Carregando…"}
          />
          {foraDeUso > 0 && (
            <button type="button" className="mt-3 text-[13px] font-semibold text-grafite hover:text-tinta" onClick={() => setVerForaDeUso((ver) => !ver)}>
              {verForaDeUso ? "Esconder os fora de uso" : `Mostrar ${plural(foraDeUso, "veículo fora de uso", "veículos fora de uso")}`}
            </button>
          )}
        </div>
      ) : (
        <div key="caixas" className="anim-enter mt-3">
          <DataTable
            columns={colunasCaixas}
            rows={linhasCaixas}
            getRowId={(caixa: Caixa) => String(caixa.id)}
            selectedId={selCaixa}
            onSelect={(id) => setSelCaixa(String(id))}
            onOpen={abrirCaixa}
            empty={carregado ? "Nenhuma caixa ainda. As caixas vêm do arquivo da empresa." : "Carregando…"}
          />
        </div>
      )}

      <Dialog
        width={620}
        open={novo}
        onClose={() => setNovo(false)}
        title="Cadastrar veículo"
        summary="Depois de salvar, a caixa escolhida passa a ser deste veículo."
        footer={
          <>
            <SaveButton state={salvando} type="submit" form={FORM_NOVO}>
              Salvar veículo
            </SaveButton>
            <button type="button" className="btn" onClick={() => setNovo(false)}>
              Cancelar
            </button>
          </>
        }
      >
        {novo && (
          <VehicleForm
            key={versaoForm}
            formId={FORM_NOVO}
            veiculo={null}
            outros={lista}
            caixas={listaCaixas}
            readOnly={!podeEditar}
            onSaved={aoSalvarVeiculo}
            onStateChange={setSalvando}
          />
        )}
      </Dialog>

      <Drawer
        open={veiculoAberto !== null}
        onClose={() => setEditando(null)}
        title={veiculoAberto ? nomeDoVeiculo(veiculoAberto) : ""}
        summary={veiculoAberto ? `Placa ${veiculoAberto.placa} · ${SITUACAO_VEICULO[veiculoAberto.situacao]}` : undefined}
        footer={
          podeEditar ? (
            <>
              <SaveButton state={salvando} type="submit" form={FORM_EDITAR}>
                Salvar veículo
              </SaveButton>
              <button type="button" className="btn" onClick={() => setEditando(null)}>
                Cancelar
              </button>
            </>
          ) : (
            <button type="button" className="btn" onClick={() => setEditando(null)}>
              Fechar
            </button>
          )
        }
      >
        {veiculoAberto && (
          <VehicleForm
            key={versaoForm}
            formId={FORM_EDITAR}
            veiculo={veiculoAberto}
            outros={lista.filter((veiculo) => veiculo.id !== veiculoAberto.id)}
            caixas={listaCaixas}
            readOnly={!podeEditar}
            onSaved={aoSalvarVeiculo}
            onStateChange={setSalvando}
          />
        )}
      </Drawer>

      <BoxDrawer
        caixa={caixaAbertaObj}
        caixas={listaCaixas}
        veiculos={lista}
        readOnly={!podeEditar}
        onClose={() => setCaixaAberta(null)}
        onLinked={aoVincular}
      />
    </section>
  );
}
