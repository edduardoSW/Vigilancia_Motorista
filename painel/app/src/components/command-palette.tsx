"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { buscarNaPaleta, type ItemBusca } from "@/components/command-search";
import { itensDoMenu } from "@/components/menu";
import { useSession } from "@/components/session-provider";
import { Glyph } from "@/components/ui/glyph";
import { Kbd } from "@/components/ui/kbd";
import { useEscapeAndFocus, usePresence } from "@/components/ui/use-presence";
import { nomeDoVeiculo as nomeNaFrota } from "@/components/vehicles/vehicle-labels";
import { dados, dia, hora, motoristaDe, nomeDoVeiculo } from "@/content";
import { buscarNoGuia } from "@/content/guide";
import { bridge, type Motorista, type Veiculo } from "@/lib/bridge";
import { cn } from "@/lib/utils";

/** O botão "Buscar" do menu abre a busca rápida com este evento. */
export const EVENTO_BUSCA = "rotaguard:busca";

// Busca rápida (Ctrl+K, contrato do painel): ir para uma tela, achar viagem, motorista, veículo ou capítulo do guia.
// ↑/↓ escolhe, Enter abre, Esc fecha. Motorista e veículo abrem na janela no centro da tela deles (?abrir=).
const VIAGENS: ItemBusca[] = dados.viagens.map((viagem) => ({
  id: `viagem-${viagem.id}`,
  grupo: "Viagens",
  titulo: nomeDoVeiculo(viagem.tipo, viagem.veiculo),
  detalhe: `${viagem.linha} · chegou ${dia(viagem.chegada)} às ${hora(viagem.chegada)}`,
  palavras: `viagem ${motoristaDe(viagem.motorista)?.nome ?? ""}`,
  href: `/viagens/${viagem.id}/`,
}));

export function CommandPalette() {
  const router = useRouter();
  const { pode } = useSession();
  const [aberta, setAberta] = useState(false);
  const [aberturaVista, setAberturaVista] = useState(false);
  const [consulta, setConsulta] = useState("");
  const [indice, setIndice] = useState(0);
  const [cadastros, setCadastros] = useState<{ motoristas: Motorista[]; veiculos: Veiculo[] }>({ motoristas: [], veiculos: [] });
  const caixa = useRef<HTMLDivElement>(null);
  const lista = useRef<HTMLUListElement>(null);
  const { montado, saindo } = usePresence(aberta, 140);
  useEscapeAndFocus(aberta, () => setAberta(false), caixa);

  // Cada abertura começa com a busca vazia (ajuste na renderização, sem efeito).
  if (aberta !== aberturaVista) {
    setAberturaVista(aberta);
    if (aberta) {
      setConsulta("");
      setIndice(0);
    }
  }

  useEffect(() => {
    const teclar = (evento: KeyboardEvent) => {
      if ((evento.ctrlKey || evento.metaKey) && !evento.shiftKey && !evento.altKey && evento.key.toLowerCase() === "k") {
        evento.preventDefault();
        setAberta((valor) => !valor);
      }
    };
    const abrir = () => setAberta(true);
    window.addEventListener("keydown", teclar);
    window.addEventListener(EVENTO_BUSCA, abrir);
    return () => {
      window.removeEventListener("keydown", teclar);
      window.removeEventListener(EVENTO_BUSCA, abrir);
    };
  }, []);

  useEffect(() => {
    if (!aberta) return;
    let vivo = true;
    Promise.all([bridge.motoristas_listar(), bridge.veiculos_listar()]).then(([motoristas, veiculos]) => {
      if (vivo) setCadastros({ motoristas: motoristas.ok ? motoristas.dados : [], veiculos: veiculos.ok ? veiculos.dados : [] });
    });
    return () => {
      vivo = false;
    };
  }, [aberta]);

  const telas = useMemo<ItemBusca[]>(
    () => itensDoMenu(pode).map((item) => ({ id: `tela-${item.href}`, grupo: "Telas", titulo: item.rotulo, href: item.href })),
    [pode],
  );

  const resultados = useMemo(() => {
    if (!consulta.trim()) return telas;
    const motoristas = cadastros.motoristas.map((motorista) => ({
      id: `motorista-${motorista.id}`,
      grupo: "Motoristas",
      titulo: motorista.nome,
      detalhe: `Matrícula ${motorista.matricula}`,
      palavras: `motorista ${motorista.nome_curto}`,
      href: `/motoristas/?abrir=${motorista.id}`,
    }));
    const veiculos = cadastros.veiculos.map((veiculo) => ({
      id: `veiculo-${veiculo.id}`,
      grupo: "Veículos",
      titulo: nomeNaFrota(veiculo),
      detalhe: veiculo.placa,
      palavras: `veiculo ${veiculo.modelo ?? ""}`,
      href: `/veiculos/?abrir=${veiculo.id}`,
    }));
    const guia = buscarNoGuia(consulta)
      .slice(0, 5)
      .map((achado) => ({
        id: `guia-${achado.capituloId}-${achado.topicoId ?? "inicio"}`,
        grupo: "Guia de uso",
        titulo: achado.titulo,
        detalhe: `Capítulo ${achado.capituloNumero} · ${achado.capituloTitulo}`,
        palavras: consulta,
        href: `/guia/?capitulo=${achado.capituloId}${achado.topicoId ? `&passo=${achado.topicoId}` : ""}`,
      }));
    return buscarNaPaleta(consulta, [...telas, ...VIAGENS, ...motoristas, ...veiculos, ...guia]);
  }, [consulta, telas, cadastros]);

  const selecionado = resultados.length ? Math.min(indice, resultados.length - 1) : -1;

  useEffect(() => {
    lista.current?.querySelector<HTMLElement>('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
  }, [selecionado]);

  function ir(item: ItemBusca) {
    setAberta(false);
    // O carimbo faz a tela abrir de novo o mesmo motorista ou veículo quando ele é escolhido duas vezes seguidas.
    router.push(item.href.includes("abrir=") ? `${item.href}&n=${Date.now()}` : item.href);
  }

  function teclar(evento: React.KeyboardEvent<HTMLInputElement>) {
    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      if (resultados.length) setIndice((selecionado + (evento.key === "ArrowDown" ? 1 : -1) + resultados.length) % resultados.length);
    } else if (evento.key === "Enter" && selecionado >= 0) {
      evento.preventDefault();
      ir(resultados[selecionado]);
    }
  }

  if (!montado) return null;
  const titulos = resultados.map((item, posicao) => (posicao === 0 || resultados[posicao - 1].grupo !== item.grupo ? item.grupo : null));

  return (
    <div className="no-print fixed inset-0 z-[55] grid place-items-center p-6">
      <div aria-hidden="true" onClick={() => setAberta(false)} className={cn("veu absolute inset-0", saindo ? "anim-fade-out" : "anim-fade")} />
      <div
        ref={caixa}
        role="dialog"
        aria-modal="true"
        aria-label="Busca rápida"
        tabIndex={-1}
        className={cn(
          // Altura fixa: no centro da tela, a janela não pula enquanto os resultados mudam.
          "relative flex h-[min(520px,calc(var(--altura-janela)-96px))] w-[min(620px,100%)] flex-col overflow-hidden rounded-[14px] border border-fio bg-elevada shadow-[0_24px_60px_-30px_rgb(0_0_0/0.45)] outline-none",
          saindo ? "anim-dialog-out" : "anim-dialog",
        )}
      >
        <label className="flex items-center gap-3 border-b border-fio px-4">
          <Glyph name="search" size={18} className="shrink-0 text-grafite" />
          <span className="sr-only">Buscar</span>
          <input
            autoFocus
            value={consulta}
            onChange={(evento) => {
              setConsulta(evento.target.value);
              setIndice(0);
            }}
            onKeyDown={teclar}
            role="combobox"
            aria-expanded="true"
            aria-controls="busca-resultados"
            aria-activedescendant={selecionado >= 0 ? `busca-${resultados[selecionado].id}` : undefined}
            placeholder="Ir para uma tela, motorista, veículo ou guia"
            autoComplete="off"
            spellCheck={false}
            className="h-[52px] min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-apagado"
          />
          <Kbd>Esc</Kbd>
        </label>

        <ul ref={lista} id="busca-resultados" role="listbox" aria-label="Resultados" className="min-h-0 flex-1 overflow-y-auto p-2">
          {resultados.map((item, posicao) => (
            <li key={item.id} role="presentation">
              {titulos[posicao] && <p className="px-3 pb-1 pt-2.5 text-[12.5px] font-semibold text-grafite">{titulos[posicao]}</p>}
              <div
                id={`busca-${item.id}`}
                role="option"
                aria-selected={posicao === selecionado}
                onMouseMove={() => setIndice(posicao)}
                onClick={() => ir(item)}
                className={cn("flex h-11 cursor-default items-center gap-3 rounded-[8px] px-3 text-[14px]", posicao === selecionado && "bg-lateral")}
              >
                <span className="min-w-0 flex-1 truncate">
                  <b className="font-semibold">{item.titulo}</b>
                  {item.detalhe && <span className="text-grafite"> · {item.detalhe}</span>}
                </span>
                {posicao === selecionado && <Kbd>Enter</Kbd>}
              </div>
            </li>
          ))}
        </ul>
        {!resultados.length && <p className="px-5 pb-6 pt-2 text-[14px] text-grafite">Nada encontrado com “{consulta.trim()}”. Tente outra palavra.</p>}
        <p className="border-t border-fio px-4 py-2.5 text-[12.5px] text-grafite">↑ ↓ para escolher · Enter para abrir</p>
      </div>
    </div>
  );
}
