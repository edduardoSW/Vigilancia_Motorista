"use client";
import {useEffect, useState, useSyncExternalStore} from "react";
import {useTranslations} from "next-intl";
import {useRouter} from "@/i18n/navigation";
import {downloads, type App, type Plataforma} from "@/content/downloads";
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
const nomes: Record<Plataforma,string> = {windows:"Windows",linux:"Linux"};
const textos = {
  painel: {titulo:"painelTitulo",texto:"painelTexto",instrucoes:"painelInstrucoes",windows:"painelWindows",linux:null},
  teste: {titulo:"testeTitulo",texto:"testeTexto",instrucoes:"testeInstrucoes",windows:"testeWindows",linux:"testeLinux"},
} as const;
type Situacao = {disponivel: boolean|null; bytes: number|null};
const megabytes=(bytes: number)=>`${Math.round(bytes/1_048_576)} MB`;
// Painel da empresa (spec 020) e app de teste do script (spec 010): arquivos servidos pelo próprio site em /downloads
// (src/content/downloads.ts). Antes de oferecer o botão, confere se o arquivo está lá; o que ainda não foi gerado aparece
// como "Em preparação". A situação fica guardada pelo endereço do arquivo, porque os dois apps têm Windows.
export function DownloadArea() {
  const t=useTranslations("app");
  const router=useRouter();
  const active=useSyncExternalStore(subscribe,snapshot,serverSnapshot);
  const [situacao,setSituacao]=useState<Record<string,Situacao>>({});
  useEffect(()=>{if(active===false) router.replace("/entrar");},[active,router]);
  useEffect(()=>{
    if(active!==true) return;
    const controle=new AbortController();
    for(const d of downloads){
      fetch(d.url,{method:"HEAD",cache:"no-store",signal:controle.signal})
        .then(resposta=>{
          const bytes=Number(resposta.headers.get("content-length"))||null;
          setSituacao(atual=>({...atual,[d.url]:{disponivel:resposta.ok,bytes:resposta.ok?bytes:null}}));
        })
        // Outro domínio sem CORS (release do GitHub, por exemplo): não dá para conferir, então o botão continua.
        .catch(()=>{if(!controle.signal.aborted) setSituacao(atual=>({...atual,[d.url]:{disponivel:null,bytes:null}}));});
    }
    return ()=>controle.abort();
  },[active]);
  if(active!==true) return <section className="inner-page shell"><p role="status">{t("carregando")}</p></section>;
  return <section className="inner-page shell">
    <div className="download-header"><div><h1>{t("titulo")}</h1><p className="lead">{t("texto")}</p></div><button className="action action-dark" onClick={()=>{try{signOut(window.localStorage);}finally{window.dispatchEvent(new Event("rotaguard-acesso"));router.replace("/entrar");}}}>{t("sair")}<span><Arrow/></span></button></div>
    {(Object.keys(textos) as App[]).map(app=><section key={app} className="download-group" aria-labelledby={`download-${app}`}>
      <h2 id={`download-${app}`}>{t(textos[app].titulo)}</h2><p className="lead">{t(textos[app].texto)}</p>
      <ul className="download-list">{downloads.filter(d=>d.app===app).map(d=>{
        const s=situacao[d.url];
        const descricao=textos[app][d.plataforma];
        return <li key={d.url}><div><h3>{nomes[d.plataforma]}</h3>{descricao&&<p>{t(descricao)}</p>}<small>{d.arquivo}{s?.bytes?` · ${megabytes(s.bytes)}`:""}</small></div>
          {s?.disponivel===false
            ? <span className="action action-dark pointer-events-none opacity-40" aria-disabled="true">{t("emPreparacao")}</span>
            : <a href={d.url} download={d.url.startsWith("/")?d.arquivo:undefined} className="action action-dark" data-evento="download_app" data-app={app} data-plataforma={d.plataforma}>{t("baixar")}<span><Arrow diagonal/></span></a>}
        </li>;
      })}</ul>
      <p className="download-note">{t(textos[app].instrucoes)}</p>
    </section>)}
    <div className="mt-10 grid max-w-3xl gap-3 text-[13px] leading-relaxed text-grafite"><p>{t("aviso")}</p><p>{t("depois")}</p></div>
  </section>;
}
