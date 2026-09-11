import { getTranslations } from "next-intl/server";
import { LanguageSwitcher } from "@/components/language-switcher";
import { MobileMenu } from "@/components/mobile-menu";
import { ScaleRail } from "@/components/scale-rail";
import { WhatsAppButton } from "@/components/whatsapp-button";
import { Wordmark } from "@/components/wordmark";
import { Link } from "@/i18n/navigation";

export const navegacao = [
  { chave: "comoFunciona", href: "/#cabine" },
  { chave: "chegada", href: "/#chegada" },
  { chave: "motoristas", href: "/#motoristas" },
  { chave: "piloto", href: "/#piloto" },
  { chave: "perguntas", href: "/#perguntas" },
] as const;

export async function SiteHeader() {
  const t = await getTranslations("nav");
  const tc = await getTranslations("contato.mensagens");

  return (
    <>
      <header className="com-trilho sticky top-0 z-40 border-b border-fio bg-concreto">
        <div className="shell flex h-(--header-h) items-center gap-6">
          <Link href="/" aria-label={t("inicio")} className="shrink-0 text-[1rem]">
            <Wordmark />
          </Link>

          <nav aria-label={t("rotulo")} className="ml-auto hidden lg:block">
            <ul className="flex items-center gap-1">
              {navegacao.map((item) => (
                <li key={item.chave}>
                  <Link href={item.href} className="flex min-h-11 items-center px-3 text-[0.95rem] hover:underline">
                    {t(item.chave)}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <div className="ml-auto hidden items-center gap-2 lg:ml-0 lg:flex">
            <LanguageSwitcher />
            <Link href="/entrar" className="flex min-h-11 items-center px-2 text-[0.95rem] link-sublinhado">
              {t("entrar")}
            </Link>
            <WhatsAppButton mensagem={tc("geral")} className="btn btn-primario min-h-11 py-2" rotulo={t("whatsapp")} />
          </div>

          <div className="ml-auto flex items-center gap-2 lg:hidden">
            <MobileMenu
              itens={navegacao.map((item) => ({ href: item.href, rotulo: t(item.chave) }))}
              rotuloMenu={t("menu")}
              rotuloFechar={t("fechar")}
              rotuloEntrar={t("entrar")}
              rotuloWhatsApp={t("whatsapp")}
              mensagemWhatsApp={tc("geral")}
            />
          </div>
        </div>
      </header>
      <ScaleRail />
    </>
  );
}
