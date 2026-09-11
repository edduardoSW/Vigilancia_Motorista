import { getTranslations } from "next-intl/server";
import { Wordmark } from "./wordmark";
import { Arrow } from "./icons";
import { Link } from "@/i18n/navigation";
export async function SiteFooter() {
const t = await getTranslations("rodape");
return <footer className="site-footer"><div className="shell"><div className="footer-top"><Link href="/" aria-label="RotaGuard"><Wordmark /></Link><p>{t("marca")}</p><a href="#conteudo" className="back-top">{t("topo")}<Arrow diagonal /></a></div><div className="footer-word" aria-hidden="true">{t("viagem")}<span>↗</span></div><div className="footer-bottom"><span>© 2026 RotaGuard</span><span>{t("estagio")}</span><Link href="/creditos">{t("fotos")}</Link></div></div></footer>;
}
