"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { LanguageSwitcher } from "./language-switcher";
import { Wordmark } from "./wordmark";
import { Arrow } from "./icons";
import { Link } from "@/i18n/navigation";
export function SiteHeader() {
const t = useTranslations("nav");
const [open, setOpen] = useState(false);
return <header className="site-header"><div className="header-inner">
<Link href="/" aria-label={t("inicio")} onClick={() => setOpen(false)}><Wordmark /></Link>
<nav className="desktop-nav" aria-label={t("rotulo")}>{["produto","operacao","frotas"].map(id => <Link key={id} href={`/#${id}`}>{t(id)}</Link>)}</nav>
<div className="header-actions"><LanguageSwitcher /><Link href="/entrar" className="login-link">{t("entrar")}<Arrow diagonal /></Link><Link href="/#contato" className="header-cta">{t("contato")}<Arrow diagonal /></Link>
<button className="menu-toggle" aria-expanded={open} aria-controls="mobile-nav" aria-label={open ? t("fechar") : t("menu")} onClick={() => setOpen(!open)}>{open ? "×" : <svg width="23" height="16" aria-hidden="true"><path d="M0 2h23M0 8h23M0 14h23" stroke="currentColor" strokeWidth="1.5" /></svg>}</button></div>
{open && <nav id="mobile-nav" className="mobile-nav" aria-label={t("rotulo")} onKeyDown={e => {if(e.key === "Escape") setOpen(false);}}>{["produto","operacao","frotas","contato"].map(id => <Link key={id} href={`/#${id}`} onClick={() => setOpen(false)}>{t(id)}<Arrow diagonal /></Link>)}<Link href="/entrar" onClick={() => setOpen(false)}>{t("entrar")}<Arrow diagonal /></Link></nav>}
</div></header>;
}
