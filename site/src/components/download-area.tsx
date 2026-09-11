"use client";
import {useEffect, useSyncExternalStore} from "react";
import {useTranslations} from "next-intl";
import {useRouter} from "@/i18n/navigation";
import {downloads} from "@/content/downloads";
import {hasAccess, signOut} from "@/lib/acesso-local";
import {Arrow} from "./icons";
function subscribe(callback: () => void) {
  window.addEventListener("storage",callback);
  window.addEventListener("rotaguard-acesso",callback);
  const timer=window.setInterval(callback,1000);
  return ()=>{window.removeEventListener("storage",callback);window.removeEventListener("rotaguard-acesso",callback);window.clearInterval(timer);};
}
function snapshot() {try {return hasAccess(window.localStorage);}catch{return false;}}
function serverSnapshot(): boolean|null {return null;}
export function DownloadArea() {
  const t=useTranslations("app");
  const router=useRouter();
  const active=useSyncExternalStore(subscribe,snapshot,serverSnapshot);
  useEffect(()=>{if(active===false) router.replace("/entrar");},[active,router]);
  if(active!==true) return <section className="inner-page shell"><p role="status">{t("carregando")}</p></section>;
  const names={windows:"Windows",macos:"macOS",linux:"Linux",android:"Android",ios:"iPhone / iPad"};
  return <section className="inner-page shell"><div className="download-header"><div><h1>{t("titulo")}</h1><p className="lead">{t("texto")}</p></div><button className="action action-dark" onClick={()=>{try{signOut(window.localStorage);}finally{window.dispatchEvent(new Event("rotaguard-acesso"));router.replace("/entrar");}}}>{t("sair")}<span><Arrow/></span></button></div><ul className="download-list">{downloads.map(d=><li key={d.plataforma}><div><h2>{names[d.plataforma]}</h2><p>{t(d.plataforma)}</p></div>{d.url ? <a href={d.url} className="action action-dark">{t(d.plataforma==="ios"?"abrir":"baixar")}<span><Arrow diagonal/></span></a> : <small>{t("emPreparacao")}</small>}</li>)}</ul></section>;
}
