import type {Metadata} from "next";
import Image from "next/image";
import {getTranslations} from "next-intl/server";
import {Link} from "@/i18n/navigation";
import {PinForm} from "./pin-form";
export const metadata:Metadata={robots:{index:false,follow:false}};
export default async function EntrarPage(){
const t=await getTranslations("entrar");const h=await getTranslations("home");
return <section className="inner-page shell access-layout"><div><p className="eyebrow mb-6">{t("rotulo")}</p><h1>{t("titulo")}</h1><p className="lead">{t("texto")}</p><PinForm/><Link href="/" className="text-link mt-6">{t("voltar")} ↗</Link></div><div className="access-visual"><Image src="/midia/rotaguard/caixa-conceito.webp" alt={h("deviceAlt")} width={1536} height={1024} sizes="50vw"/><p>{h("concept")}</p></div></section>;
}
