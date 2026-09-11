"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";
import { Flag } from "@/components/flag";
import { idiomaDe, idiomas } from "@/content/idiomas";
import { Link, usePathname } from "@/i18n/navigation";

export function LanguageSwitcher({ variante = "cabecalho" }: { variante?: "cabecalho" | "menu" }) {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const atual = idiomaDe(locale);
  const [aberto, setAberto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const listaId = useId();

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: PointerEvent) => {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAberto(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAberto(false);
    };
    document.addEventListener("pointerdown", fora);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [aberto]);

  if (variante === "menu") {
    return (
      <ul className="grid gap-1" aria-label={t("idioma")}>
        {idiomas.map((i) => (
          <li key={i.locale}>
            <Link
              href={pathname}
              locale={i.locale}
              hrefLang={i.htmlLang}
              lang={i.htmlLang}
              aria-current={i.locale === locale ? "true" : undefined}
              className="flex min-h-12 items-center gap-3 py-2 aria-[current=true]:font-bold"
            >
              <Flag code={i.bandeira} className="h-4 w-6 shrink-0" />
              <span>{i.pais}</span>
              <span className="text-grafite">· {i.idioma}</span>
            </Link>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div ref={raiz} className="relative">
      <button
        type="button"
        aria-expanded={aberto}
        aria-controls={listaId}
        aria-label={`${t("idioma")}: ${atual.pais} · ${atual.idioma}`}
        onClick={() => setAberto((v) => !v)}
        className="flex min-h-11 items-center gap-2 px-2 text-[0.95rem] hover:bg-papel"
      >
        <Flag code={atual.bandeira} className="h-3.5 w-5 shrink-0" />
        <span>{atual.pais}</span>
        <svg viewBox="0 0 10 6" className="h-1.5 w-2.5" aria-hidden="true">
          <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.4" />
        </svg>
      </button>
      <ul
        id={listaId}
        hidden={!aberto}
        className="absolute right-0 top-full z-50 mt-1 min-w-60 border border-asfalto bg-papel py-1 shadow-[0_12px_32px_rgb(27_27_25/0.16)]"
      >
        {idiomas.map((i) => (
          <li key={i.locale}>
            <Link
              href={pathname}
              locale={i.locale}
              hrefLang={i.htmlLang}
              lang={i.htmlLang}
              aria-current={i.locale === locale ? "true" : undefined}
              onClick={() => setAberto(false)}
              className="flex min-h-11 items-center gap-3 px-3 py-2 hover:bg-concreto aria-[current=true]:font-bold"
            >
              <Flag code={i.bandeira} className="h-3.5 w-5 shrink-0" />
              <span className="grow">{i.pais}</span>
              <span className="text-grafite text-sm">{i.idioma}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
