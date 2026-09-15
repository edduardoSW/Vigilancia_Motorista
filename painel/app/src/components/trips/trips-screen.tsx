"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useDecisions } from "@/components/decisions-provider";
import { plural, semAcento, useListShortcuts } from "@/components/drivers/use-list-shortcuts";
import { useVisao } from "@/components/session-provider";
import { CardGrid, CardInfo, CardTitulo } from "@/components/ui/card-grid";
import { DataTable } from "@/components/ui/data-table";
import { Glyph } from "@/components/ui/glyph";
import { Kbd } from "@/components/ui/kbd";
import { PageHeader } from "@/components/ui/page-header";
import { Tabs } from "@/components/ui/tabs";
import { ViewToggle } from "@/components/ui/view-toggle";
import { dados, dia, duracao, hora, minutosEntre, motoristaDe, nomeDoVeiculo, type Viagem } from "@/content";
import { momentosDaViagem } from "@/content/moments";

// Viagens (spec 014, áreas do painel): as viagens lidas das caixas, com o que falta verificar, busca e dia da chegada.
// Em lista ou cards (spec 019, VIS-01), com o motorista em destaque (VIA-01). Enter ou clique abre o relatório.
// Enquanto a leitura da caixa de verdade não chega, as viagens vêm do demo.json.

type Aba = "pendentes" | "revisadas" | "todas";

interface Linha {
  viagem: Viagem;
  total: number;
  pendentes: number;
}

const ABAS: Aba[] = ["pendentes", "revisadas", "todas"];
const NOME_ABA: Record<Aba, string> = { pendentes: "Para verificar", revisadas: "Revisadas", todas: "Todas" };
const VAZIO: Record<Aba, string> = {
  pendentes: "Nenhuma viagem para verificar.",
  revisadas: "Nenhuma viagem revisada ainda.",
  todas: "Nenhuma viagem lida ainda. Elas aparecem aqui quando a caixa for lida neste computador.",
};

const VIAGENS = [...dados.viagens]
  .sort((a, b) => Date.parse(b.chegada) - Date.parse(a.chegada))
  .map((viagem) => ({ viagem, momentos: momentosDaViagem(viagem).map((momento) => momento.id) }));

const naAba = (aba: Aba, linha: Linha) => aba === "todas" || (aba === "pendentes" ? linha.pendentes > 0 : linha.pendentes === 0);
const nomeDoMotorista = (viagem: Viagem) => motoristaDe(viagem.motorista)?.nome ?? "Não confirmado";

function Situacao({ linha }: { linha: Linha }) {
  if (linha.pendentes > 0) {
    return <span className="rounded-[7px] bg-lima px-2 py-[3px] text-[12.5px] font-bold tabular-nums text-sobre-lima">{linha.pendentes} para ver</span>;
  }
  return <span className="text-[13px] text-grafite">{linha.total === 0 ? "Nada para verificar" : "Revisada"}</span>;
}

export function TripsScreen() {
  const router = useRouter();
  const { decisions } = useDecisions();
  const [visao, setVisao] = useVisao("viagens");
  const [aba, setAba] = useState<Aba>("pendentes");
  const [busca, setBusca] = useState("");
  const [chegada, setChegada] = useState("");
  const [selecionada, setSelecionada] = useState<string | null>(null);
  const buscaRef = useRef<HTMLInputElement>(null);
  useListShortcuts({ searchRef: buscaRef });

  const linhas: Linha[] = VIAGENS.map(({ viagem, momentos }) => ({
    viagem,
    total: momentos.length,
    pendentes: momentos.filter((id) => !decisions[id]).length,
  }));
  const pendentes = linhas.reduce((soma, linha) => soma + linha.pendentes, 0);
  const termo = semAcento(busca.trim());
  const visiveis = linhas
    .filter((linha) => naAba(aba, linha))
    .filter((linha) => !chegada || linha.viagem.chegada.slice(0, 10) === chegada)
    .filter((linha) => {
      if (!termo) return true;
      const { viagem } = linha;
      return semAcento(`${nomeDoVeiculo(viagem.tipo, viagem.veiculo)} ${viagem.linha} ${nomeDoMotorista(viagem)}`).includes(termo);
    });
  const vazio = termo || chegada ? "Nenhuma viagem com esse filtro." : VAZIO[aba];
  const abrir = (linha: Linha) => router.push(`/viagens/${linha.viagem.id}/`);

  const colunas = [
    {
      id: "viagem",
      header: "Viagem",
      cell: ({ viagem }: Linha) => (
        <>
          <b className="block font-semibold leading-5">{nomeDoVeiculo(viagem.tipo, viagem.veiculo)}</b>
          <span className="block truncate text-[13px] leading-4 text-grafite">{viagem.linha}</span>
        </>
      ),
    },
    {
      id: "motorista",
      header: "Motorista",
      width: "21%",
      cell: ({ viagem }: Linha) => <b className="font-semibold">{nomeDoMotorista(viagem)}</b>,
    },
    {
      id: "chegada",
      header: "Chegada",
      width: "22%",
      cell: ({ viagem }: Linha) => (
        <>
          <span className="block leading-5 tabular-nums">
            {dia(viagem.chegada)} às {hora(viagem.chegada)}
          </span>
          <span className="block text-[13px] leading-4 text-grafite">{duracao(minutosEntre(viagem.saida, viagem.chegada))} de viagem</span>
        </>
      ),
    },
    { id: "momentos", header: "Momentos", width: "15%", cell: (linha: Linha) => <Situacao linha={linha} /> },
  ];

  return (
    <section className="px-14 pb-16 pt-[34px]">
      <PageHeader
        title="Viagens"
        summary={`${plural(linhas.length, "viagem", "viagens")} · ${pendentes ? plural(pendentes, "momento para verificar", "momentos para verificar") : "tudo verificado"}`}
        guide={{ capitulo: "verificar-momentos" }}
      />

      <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
        <Tabs
          label="Viagens por situação"
          items={ABAS.map((id) => ({ id, label: NOME_ABA[id], count: linhas.filter((linha) => naAba(id, linha)).length }))}
          value={aba}
          onChange={(id: string) => {
            setAba(id as Aba);
            setSelecionada(null);
          }}
        />
        <div className="flex items-center gap-2">
          <input type="date" aria-label="Dia da chegada" className="input w-[170px]" value={chegada} onChange={(evento) => setChegada(evento.target.value)} />
          <label className="relative block w-[260px]">
            <span className="sr-only">Buscar viagem</span>
            <input
              ref={buscaRef}
              type="text"
              enterKeyHint="search"
              className="input pr-10"
              placeholder="Veículo, motorista ou linha"
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

      <div className="mt-3">
        {visao === "lista" ? (
          <DataTable
            label="Viagens"
            columns={colunas}
            rows={visiveis}
            getRowId={(linha: Linha) => linha.viagem.id}
            selectedId={selecionada}
            onSelect={(id) => setSelecionada(String(id))}
            onOpen={abrir}
            empty={vazio}
          />
        ) : (
          <CardGrid
            label="Viagens"
            items={visiveis}
            getId={(linha: Linha) => linha.viagem.id}
            selectedId={selecionada}
            onSelect={setSelecionada}
            onOpen={abrir}
            empty={vazio}
            renderCard={(linha: Linha) => (
              <>
                <CardTitulo titulo={nomeDoVeiculo(linha.viagem.tipo, linha.viagem.veiculo)} detalhe={linha.viagem.linha} extra={<Situacao linha={linha} />} />
                <span className="flex min-w-0 items-center gap-2 border-y border-fio py-2.5 text-[14.5px]">
                  <Glyph name="driver" size={17} className="shrink-0 text-grafite" />
                  <span className="shrink-0 text-grafite">Motorista</span>
                  <b className="min-w-0 truncate font-semibold">{nomeDoMotorista(linha.viagem)}</b>
                </span>
                <CardInfo rotulo="Chegada">
                  {dia(linha.viagem.chegada)} às {hora(linha.viagem.chegada)}
                </CardInfo>
                <CardInfo rotulo="Duração">{duracao(minutosEntre(linha.viagem.saida, linha.viagem.chegada))}</CardInfo>
              </>
            )}
          />
        )}
      </div>
    </section>
  );
}
