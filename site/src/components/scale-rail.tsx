"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { escalas, type EscalaId } from "@/content/escalas";

/**
 * Régua de escala: a navegação da direção "Escalas".
 * No computador (≥ 80rem) é uma régua fixa na borda esquerda; abaixo disso, uma faixa fina sob o cabeçalho.
 * Cada seção com data-escala="<id>" acende o seu ponto quando cruza o meio da tela.
 */
export function ScaleRail() {
  const t = useTranslations("escalas");
  const [ativa, setAtiva] = useState<EscalaId | null>(null);

  useEffect(() => {
    const secoes = Array.from(document.querySelectorAll<HTMLElement>("[data-escala]"));
    if (secoes.length === 0) return;
    const observer = new IntersectionObserver(
      (entradas) => {
        for (const entrada of entradas) {
          if (entrada.isIntersecting) setAtiva(entrada.target.getAttribute("data-escala") as EscalaId);
        }
      },
      { rootMargin: "-45% 0px -54% 0px" }
    );
    secoes.forEach((s) => observer.observe(s));
    const fimDasEscalas = document.querySelector("[data-fim-escalas]");
    const observerFim = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting && e.boundingClientRect.top < window.innerHeight / 2) setAtiva(null);
      },
      { rootMargin: "-45% 0px -54% 0px" }
    );
    if (fimDasEscalas) observerFim.observe(fimDasEscalas);
    return () => {
      observer.disconnect();
      observerFim.disconnect();
    };
  }, []);

  const indiceAtivo = escalas.findIndex((e) => e.id === ativa);
  const atual = indiceAtivo >= 0 ? escalas[indiceAtivo] : null;

  return (
    <>
      <nav
        aria-label={t("rotulo")}
        className="fixed left-0 top-(--header-h) bottom-0 z-30 hidden w-(--rail) border-r border-fio bg-concreto xl:block"
      >
        <ol className="relative flex h-full flex-col justify-center gap-[clamp(0.6rem,2.2vh,1.4rem)] pl-4">
          {escalas.map((e, i) => {
            const ligada = e.id === ativa;
            const passou = indiceAtivo >= 0 && i < indiceAtivo;
            return (
              <li key={e.id} className="relative">
                <a
                  href={`#${e.secao}`}
                  aria-current={ligada ? "location" : undefined}
                  className={`group flex flex-col gap-0.5 pr-2 leading-none transition-colors ${
                    ligada ? "text-asfalto" : passou ? "text-grafite" : "text-fio-forte hover:text-grafite"
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <span
                      aria-hidden="true"
                      className={`block h-px transition-all ${ligada ? "w-4 bg-asfalto" : "w-2 bg-current"}`}
                    />
                    <span className={`numero whitespace-nowrap text-[0.62rem] ${ligada ? "font-bold" : ""}`}>{e.valor}</span>
                  </span>
                  <span className="etiqueta pl-[1.1rem] text-[0.58rem]">{t(e.id)}</span>
                </a>
                {e.imagem && escalas[i + 1]?.imagem ? (
                  <span
                    aria-hidden="true"
                    className="absolute -left-2.5 top-0 h-[calc(100%+clamp(0.6rem,2.2vh,1.4rem)+1.4rem)] border-l border-alarme"
                  />
                ) : null}
                {e.imagem && !escalas[i + 1]?.imagem ? (
                  <span aria-hidden="true" className="etiqueta absolute -left-3.5 top-full mt-1 text-[0.5rem] text-alarme [writing-mode:vertical-rl] rotate-180">
                    {t("fronteira")}
                  </span>
                ) : null}
              </li>
            );
          })}
        </ol>
      </nav>

      <div
        aria-hidden="true"
        className={`sticky top-(--header-h) z-30 border-b border-fio bg-concreto xl:hidden ${atual ? "" : "hidden"}`}
      >
        <div className="shell flex h-7 items-center gap-3">
          <span className="numero text-[0.7rem] font-bold">{atual?.valor}</span>
          <span className="etiqueta text-[0.62rem] text-grafite">{atual ? t(atual.id) : ""}</span>
          <span className="ml-auto flex gap-1">
            {escalas.map((e, i) => (
              <span
                key={e.id}
                className={`block h-1.5 w-3 ${i <= indiceAtivo ? "bg-asfalto" : "border border-fio-forte"}`}
              />
            ))}
          </span>
        </div>
      </div>
    </>
  );
}
