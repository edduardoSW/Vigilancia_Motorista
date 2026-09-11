"use client";

import { useEffect, useRef, useState } from "react";
import { LanguageSwitcher } from "@/components/language-switcher";
import { WhatsAppButton } from "@/components/whatsapp-button";
import { Link } from "@/i18n/navigation";

interface ItemMenu {
  href: string;
  rotulo: string;
}

export function MobileMenu({
  itens,
  rotuloMenu,
  rotuloFechar,
  rotuloEntrar,
  rotuloWhatsApp,
  mensagemWhatsApp,
}: {
  itens: ItemMenu[];
  rotuloMenu: string;
  rotuloFechar: string;
  rotuloEntrar: string;
  rotuloWhatsApp: string;
  mensagemWhatsApp: string;
}) {
  const [aberto, setAberto] = useState(false);
  const botao = useRef<HTMLButtonElement>(null);
  const painel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aberto) return;
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    painel.current?.querySelector<HTMLElement>("a, button")?.focus();
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAberto(false);
    };
    document.addEventListener("keydown", esc);
    const botaoAtual = botao.current;
    return () => {
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", esc);
      botaoAtual?.focus();
    };
  }, [aberto]);

  return (
    <>
      <button
        ref={botao}
        type="button"
        aria-expanded={aberto}
        aria-controls="menu-celular"
        onClick={() => setAberto(true)}
        className="btn btn-secundario min-h-11 px-4 py-2"
      >
        {rotuloMenu}
      </button>

      <div
        id="menu-celular"
        ref={painel}
        hidden={!aberto}
        role="dialog"
        aria-modal="true"
        aria-label={rotuloMenu}
        className="fixed inset-0 z-50 overflow-y-auto bg-concreto"
      >
        <div className="shell flex min-h-full flex-col gap-8 pb-10">
          <div className="flex h-(--header-h) items-center justify-end">
            <button type="button" onClick={() => setAberto(false)} className="btn btn-secundario min-h-11 px-4 py-2">
              {rotuloFechar}
            </button>
          </div>
          <nav aria-label={rotuloMenu}>
            <ul className="grid border-t border-fio">
              {itens.map((item) => (
                <li key={item.href} className="border-b border-fio">
                  <Link
                    href={item.href}
                    onClick={() => setAberto(false)}
                    className="flex min-h-14 items-center font-titulo text-[2rem] font-bold leading-none"
                  >
                    {item.rotulo}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          <div className="grid gap-3">
            <WhatsAppButton mensagem={mensagemWhatsApp} className="btn btn-primario w-full" rotulo={rotuloWhatsApp} />
            <Link href="/entrar" onClick={() => setAberto(false)} className="btn btn-secundario w-full">
              {rotuloEntrar}
            </Link>
          </div>
          <LanguageSwitcher variante="menu" />
        </div>
      </div>
    </>
  );
}
