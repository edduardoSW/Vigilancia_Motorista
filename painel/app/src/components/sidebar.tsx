"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLayoutEffect, useRef, useState } from "react";
import { EVENTO_BUSCA } from "@/components/command-palette";
import { useDecisions } from "@/components/decisions-provider";
import { Wordmark } from "@/components/icons";
import { itemAtivo, itensDoMenu, type ItemMenu } from "@/components/menu";
import { useSession } from "@/components/session-provider";
import { OPCOES_TEMA } from "@/components/theme-options";
import { Glyph } from "@/components/ui/glyph";
import { Kbd } from "@/components/ui/kbd";
import { dados, nomeDoVeiculo, veiculoDe } from "@/content";
import { momentosDaViagem } from "@/content/moments";
import { NOME_FUNCAO } from "@/lib/bridge";
import { cn } from "@/lib/utils";

// Menu da janela (spec 014, áreas do painel; spec 019): a busca, uma linha curta com a caixa conectada enquanto houver, as
// áreas na ordem da spec (sem as que a função não abre) e, embaixo, o teste neste computador, o guia, quem entrou e o tema.
// A barrinha desliza até a tela aberta. Viagens mostra quantos momentos faltam verificar; os outros itens não têm contador.
const MOMENTOS = dados.viagens.flatMap((viagem) => momentosDaViagem(viagem).map((momento) => momento.id));

export function Sidebar() {
  const rota = usePathname() || "/";
  const { estado, usuario, pode, sair, preferencias, salvarPreferencias } = useSession();
  const { decisions } = useDecisions();
  const itens = itensDoMenu(pode);
  const ativo = itemAtivo(rota, itens);
  const paraVer = MOMENTOS.filter((id) => !decisions[id]).length;
  const coleta = dados.coletas[0];
  const veiculoDaColeta = coleta ? veiculoDe(coleta.veiculo) : undefined;

  const coluna = useRef<HTMLElement>(null);
  const [barra, setBarra] = useState<{ top: number; height: number } | null>(null);

  useLayoutEffect(() => {
    const medir = () => {
      const link = coluna.current?.querySelector<HTMLElement>('[data-menu][aria-current="page"]');
      setBarra(link ? { top: link.offsetTop, height: link.offsetHeight } : null);
    };
    medir();
    const observador = new ResizeObserver(medir);
    if (coluna.current) observador.observe(coluna.current);
    return () => observador.disconnect();
  }, [ativo, itens.length]);

  const item = (entrada: ItemMenu) => {
    const marcado = entrada.href === ativo;
    return (
      <li key={entrada.href}>
        <Link
          href={entrada.href}
          data-menu
          aria-current={marcado ? "page" : undefined}
          className={cn(
            "relative flex h-11 items-center gap-3 rounded-[10px] px-3 text-[14.5px] transition-colors",
            marcado ? "font-semibold" : "text-tinta/85 hover:bg-superficie/60 hover:text-tinta",
          )}
        >
          <Glyph name={entrada.icone} size={18} className={marcado ? "text-verde" : "text-grafite"} />
          <span className="min-w-0 flex-1 truncate">{entrada.rotulo}</span>
          {entrada.href === "/viagens/" && paraVer > 0 && (
            <span className="count rounded-[7px] bg-lima px-2 py-[3px] text-[12.5px] font-bold tabular-nums text-sobre-lima">{paraVer} para ver</span>
          )}
        </Link>
      </li>
    );
  };

  return (
    <aside ref={coluna} className="no-print relative flex h-[var(--altura-janela)] flex-col overflow-y-auto border-r border-fio bg-lateral px-3 pb-4 pt-[22px]">
      {barra && (
        <span
          aria-hidden="true"
          className="menu-bar pointer-events-none absolute inset-x-3 top-0 rounded-[10px] bg-superficie shadow-[0_1px_2px_rgb(0_0_0/0.08),0_0_0_1px_var(--color-fio)]"
          style={{ height: barra.height, transform: `translateY(${barra.top}px)` }}
        />
      )}

      <div className="flex items-center gap-2.5 px-3">
        <Wordmark />
        {estado?.empresa && <span className="ml-auto truncate text-[12px] font-medium text-grafite">{estado.empresa.nome}</span>}
      </div>

      <button
        type="button"
        onClick={() => window.dispatchEvent(new Event(EVENTO_BUSCA))}
        className="mt-5 flex h-9 items-center gap-2 rounded-[9px] border border-fio bg-superficie/70 px-3 text-[13.5px] text-grafite transition-colors hover:border-tinta/25 hover:text-tinta"
      >
        <Glyph name="search" size={16} />
        Buscar
        <Kbd className="ml-auto">Ctrl K</Kbd>
      </button>

      {/* Caixa conectada numa linha só (spec 019, INT-02): o andamento completo fica no Início. */}
      {coleta && (
        <Link
          href="/#caixa-conectada"
          data-caixa-conectada
          title={`Caixa do ${veiculoDaColeta ? nomeDoVeiculo(veiculoDaColeta.tipo, veiculoDaColeta.prefixo) : coleta.caixa} conectada: lendo o registro`}
          className="mt-2 flex h-9 items-center gap-2.5 rounded-[9px] px-3 text-[13px] text-grafite transition-colors hover:bg-superficie/60 hover:text-tinta"
        >
          <span aria-hidden="true" className="pulse-dot" />
          <span className="min-w-0 flex-1 truncate">Caixa conectada</span>
          <span className="tabular-nums">{coleta.progresso}%</span>
        </Link>
      )}

      {/* Sem min-h-0: numa janela baixa o menu rola inteiro, em vez de o rodapé passar por cima de quem entrou. */}
      <nav aria-label="Menu" className="mt-3 flex flex-1 flex-col">
        <ul>{itens.filter((entrada) => entrada.grupo === "principal").map(item)}</ul>
        <ul className="mt-auto border-t border-fio pt-2">{itens.filter((entrada) => entrada.grupo === "rodape").map(item)}</ul>
      </nav>

      {usuario && (
        <div className="mt-2 border-t border-fio px-3 pt-3">
          <div className="flex items-center gap-3">
            <div className="min-w-0 flex-1">
              <b className="block truncate text-[14px] font-semibold">{usuario.nome}</b>
              <span className="block text-[12.5px] text-grafite">{NOME_FUNCAO[usuario.funcao]}</span>
            </div>
            <button type="button" className="btn btn-small" onClick={() => void sair()}>
              Sair
            </button>
          </div>
          {/* Tema da pessoa (spec 019, ESC-01): muda na hora e fica guardado pela ponte. */}
          <div className="mt-3 flex items-center justify-between gap-3">
            <span className="text-[13px] text-grafite">Tema</span>
            <div role="group" aria-label="Tema" className="inline-flex items-center gap-0.5 rounded-[9px] border border-fio bg-superficie p-0.5">
              {OPCOES_TEMA.map((opcao) => {
                const marcado = preferencias.tema === opcao.valor;
                return (
                  <button
                    key={opcao.valor}
                    type="button"
                    data-tema-opcao={opcao.valor}
                    aria-pressed={marcado}
                    aria-label={opcao.rotulo}
                    title={opcao.rotulo}
                    onClick={() => void salvarPreferencias({ tema: opcao.valor })}
                    className={cn("grid size-8 place-items-center rounded-[7px] transition-colors", marcado ? "bg-selecao text-tinta" : "text-grafite hover:text-tinta")}
                  >
                    <Glyph name={opcao.icone} size={16} />
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
