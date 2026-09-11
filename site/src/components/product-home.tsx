"use client";
import Image from "next/image";
import {useState} from "react";
import {useTranslations} from "next-intl";
import {Arrow, Symbol} from "./icons";
import {Link} from "@/i18n/navigation";
import {linkWhatsApp, linkTelefone} from "@/content/site";
const media = "/midia/rotaguard/";
export function ProductHome() {
const t=useTranslations("home");
const [feature,setFeature]=useState(0);
const [stage,setStage]=useState(2);
const [fleet,setFleet]=useState("bus");
const contact=linkWhatsApp(t(fleet==="bus" ? "messageBus" : "messageTruck"));
const phone=linkTelefone();
return <>
<section className="hero">
  <Image src={media+"onibus-rodoviario.webp"} alt={t("busAlt")} fill sizes="100vw" quality={80} loading="eager" fetchPriority="high" className="hero-photo" />
  <div className="hero-shade" />
  <div className="hero-content">
    <p className="eyebrow"><span className="status-dot" />{t("eyebrow")}</p>
    <h1>{t("headline1")}<br/>{t("headline2")}<br/><span>{t("headline3")}</span></h1>
    <p className="hero-description">{t("intro")}</p>
    <a href="#produto" className="action action-lime">{t("discover")}<span><Arrow diagonal /></span></a>
  </div>
  <div className="hero-bottom"><span>{t("heroFoot")}</span><a href="#produto">{t("scroll")}<span>↓</span></a></div>
  <a href="#produto" className="hero-device" aria-label={t("discover")}><div className="hero-device-top"><span>ROTAGUARD / 01</span><Arrow diagonal /></div><Image src={media+"caixa-conceito.webp"} alt={t("deviceAlt")} width={380} height={253} sizes="250px" /><div className="hero-device-bottom"><span>{t("deviceMini")}</span><small>{t("conceptShort")}</small></div></a>
</section>
<div className="promise-strip shell">{["sound","offline","log"].map((icon,i)=><div key={icon}><Symbol kind={icon}/><span>{t("promise"+i)}</span><small>0{i+1}</small></div>)}</div>
<section id="produto" className="product-section section-space"><div className="shell">
  <div className="section-heading"><p className="eyebrow">{t("productLabel")}</p><h2>{t("productTitle1")}<br/><span className="muted-title">{t("productTitle2")}</span></h2><p>{t("productIntro")}</p></div>
  <div className="product-layout">
    <div className="product-stage"><div className="product-stage-label"><span>ROTAGUARD</span><span>{t("deviceLabel")}</span></div><span className="product-type" aria-hidden="true">RG—01</span>
      <Image src={media+"caixa-conceito.webp"} alt={t("deviceAlt")} width={1536} height={1024} sizes="(max-width: 800px) 100vw, 58vw" className="product-image" />
      <div className="hotspot-group" aria-label={t("explore")}>{[0,1,2].map(i=><button className={`hotspot hotspot-${i}`} key={i} aria-pressed={feature===i} aria-label={t("featureTitle"+i)} onClick={()=>setFeature(i)}>0{i+1}</button>)}</div>
      <p className="concept-caption">{t("concept")}</p>
    </div>
    <div className="feature-list">{["eye","sound","log"].map((icon,i)=><div className="feature-item" key={icon} data-active={feature===i}><button onClick={()=>setFeature(i)} aria-expanded={feature===i} aria-controls={`feature-${i}`}><span className="feature-index">0{i+1}</span><h3>{t("featureTitle"+i)}</h3><span className="feature-plus">{feature===i ? "−" : "+"}</span></button><div id={`feature-${i}`} hidden={feature!==i}><p>{t("featureText"+i)}</p><Symbol kind={icon}/></div></div>)}<a className="text-link" href="#operacao">{t("operationLink")}<Arrow diagonal /></a><details className="engineering"><summary>{t("engineeringTitle")}<span>+</span></summary><video controls playsInline muted preload="none" poster="/midia/rotaguard/engenharia-poster.webp" aria-label={t("engineeringTitle")}><source src="/midia/rotaguard/estudo-engenharia.mp4" type="video/mp4"/></video><p>{t("engineeringNote")}</p></details></div>
  </div>
</div></section>
<section id="frotas" className="fleet-section section-space"><div className="shell">
 <div className="section-heading"><p className="eyebrow">{t("fleetLabel")}</p><h2>{t("fleetTitle1")}<br/><span className="muted-title">{t("fleetTitle2")}</span></h2><p>{t("fleetIntro")}</p></div>
 <div className="fleet-tabs" role="tablist" aria-label={t("fleetSelector")}>{["bus","truck"].map(id=><button type="button" key={id} role="tab" id={`tab-${id}`} aria-selected={fleet===id} aria-controls="fleet-panel" tabIndex={fleet===id ? 0 : -1} onClick={()=>setFleet(id)} onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();const next=e.key==="Home"?"bus":e.key==="End"?"truck":fleet==="bus"?"truck":"bus";setFleet(next);document.getElementById("tab-"+next)?.focus();}}}><Symbol kind={id}/>{t(id+"Title")}<Arrow diagonal/></button>)}</div>
 <div className="fleet-panel" role="tabpanel" id="fleet-panel" aria-labelledby={`tab-${fleet}`} tabIndex={0}>
 <Image key={fleet} src={media+(fleet==="bus"?"onibus-rodoviario.webp":"caminhao-rodovia.webp")} alt={t(fleet+"Alt")} fill sizes="(max-width: 800px) 100vw, 90vw" quality={80}/>
 <div className="fleet-panel-shade"/><div className="fleet-panel-copy"><p className="eyebrow">{t(fleet+"Label")}</p><h3>{t(fleet+"Headline")}</h3><p>{t(fleet+"Text")}</p><a href="#contato" className="action action-white">{t("fleetCta")}<span><Arrow diagonal/></span></a></div><span className="fleet-caption">{t(fleet+"Caption")}</span>
 </div>
</div></section>
<section id="operacao" className="operation-section section-space"><div className="shell">
<div className="section-heading"><p className="eyebrow">{t("operationLabel")}</p><h2>{t("operationTitle1")}<br/><span>{t("operationTitle2")}</span></h2><p>{t("operationIntro")}</p></div>
<div className="journey-tabs" role="tablist" aria-label={t("journeyLabel")}>{[0,1,2].map(i=><button key={i} type="button" role="tab" id={`journey-tab-${i}`} aria-selected={stage===i} aria-controls="journey-panel" tabIndex={stage===i ? 0 : -1} onClick={()=>setStage(i)} onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();const next=e.key==="Home"?0:e.key==="End"?2:(stage+(e.key==="ArrowRight"?1:2))%3;setStage(next);document.getElementById("journey-tab-"+next)?.focus();}}}><span>0{i+1}</span>{t("stageTitle"+i)}<Arrow/></button>)}</div>
<div className="journey-panel" id="journey-panel" role="tabpanel" aria-labelledby={`journey-tab-${stage}`} tabIndex={0}>
 <div className="journey-visual">{stage<2 ? <Image src={media+(stage===0?"motorista-rodoviario.webp":"onibus-rodoviario.webp")} alt={t(stage===0?"driverAlt":"busAlt")} fill sizes="(max-width: 800px) 100vw, 50vw"/> : <><Image src={media+"chegada-garagem.webp"} alt={t("arrivalAlt")} fill sizes="(max-width: 800px) 100vw, 50vw"/><div className="report-sheet"><div className="report-brand">rotaguard<span>↗</span></div><span className="eyebrow">{t("reportLabel")}</span><h4>{t("reportTitle")}</h4><p>{t("reportExample")}</p><div className="report-line"/>{[0,1,2].map(i=><div className="report-row" key={i}><time>{["22:40","02:14","06:50"][i]}</time><span>{t("reportEvent"+i)}</span><span className="report-dot"/></div>)}<div className="report-note">{t("reportNote")}</div></div></>}</div>
 <div className="journey-copy"><span className="journey-big-number" aria-hidden="true">0{stage+1}</span><h3>{t("stageHeadline"+stage)}</h3><p>{t("stageText"+stage)}</p><span className="journey-status"><span className="status-dot"/>{t("stageStatus"+stage)}</span></div>
</div><p className="development-note">{t("development")}</p>
</div></section>
<section id="motoristas" className="human-section"><div className="human-photo"><Image src={media+"motorista-rodoviario.webp"} alt={t("driverAlt")} fill sizes="(max-width: 800px) 100vw, 50vw" /></div><div className="human-copy"><p className="eyebrow">{t("humanLabel")}</p><h2>{t("humanTitle1")}<br/><span>{t("humanTitle2")}</span></h2><p>{t("humanIntro")}</p><ul>{["humanPoint0","humanPoint1","humanPoint2"].map(k=><li key={k}><Symbol kind="shield"/>{t(k)}</li>)}</ul></div></section>
<section id="perguntas" className="faq-section section-space shell"><div><p className="eyebrow">{t("faqLabel")}</p><h2>{t("faqTitle")}</h2><p className="faq-intro">{t("faqIntro")}</p></div><div className="faq-list">{[0,1,2,3,4].map(i=><details key={i}><summary><span>{t("question"+i)}</span><span className="faq-plus">+</span></summary><p>{t("answer"+i)}</p></details>)}</div></section>
<section id="contato" className="contact-section"><div className="shell contact-inner"><div><p className="eyebrow">{t("contactLabel")}</p><h2>{t("contactTitle1")}<br/>{t("contactTitle2")}<span>↗</span></h2><p>{t("contactIntro")}</p></div><div className="contact-actions">{contact ? <a href={contact} target="_blank" rel="noopener noreferrer" className="action action-dark">{t("whatsapp")}<span><Arrow diagonal/></span></a> : <div className="contact-unavailable"><Symbol kind="sound"/><strong>{t("contactSoon")}</strong><p>{t("contactMissing")}</p></div>}{phone && <a className="text-link" href={phone}>{t("phone")}<Arrow diagonal/></a>}<Link href="/entrar" className="text-link">{t("clientAccess")}<Arrow diagonal/></Link></div></div></section>
</>;
}
