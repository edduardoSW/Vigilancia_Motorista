import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { WhatsAppButton } from "@/components/whatsapp-button";
import { PinForm } from "./pin-form";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function EntrarPage() {
  const t = await getTranslations("entrar");
  const tc = await getTranslations("contato.mensagens");
  const locale = await getLocale();

  return (
    <section className="com-trilho">
      <div className="shell grid min-h-[70svh] content-center py-20">
        <h1 className="text-[clamp(2.8rem,6vw,5rem)]">{t("titulo")}</h1>
        <p className="texto-longo mt-6 text-grafite">{t("texto")}</p>
        <PinForm
          locale={locale}
          rotuloPin={t("pin")}
          rotuloBotao={t("botao")}
          erros={{ pin: t("erroPin"), bloqueio: t("erroBloqueio"), config: t("erroConfig") }}
        />
        <p className="mt-10 text-grafite">
          <WhatsAppButton mensagem={tc("geral")} rotulo={t("semPin")} className="link-sublinhado" />
        </p>
      </div>
    </section>
  );
}
