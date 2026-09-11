// End-to-end verification using the local Edge already installed on Windows.
// The optional real PIN is supplied only through the process environment.
import {spawn} from "node:child_process";
import {mkdtempSync,writeFileSync,mkdirSync} from "node:fs";
import {tmpdir} from "node:os";
import path from "node:path";
import assert from "node:assert/strict";
const base=process.env.SITE_URL||"http://localhost:3000";
const output=path.resolve("../docs/site/prints/reformulacao-2026-09-11");
mkdirSync(output,{recursive:true});
const port=9600+Math.floor(Math.random()*300);
const child=spawn("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",["--headless=new","--no-first-run","--remote-debugging-port="+port,"--user-data-dir="+mkdtempSync(path.join(tmpdir(),"rg-check-")),"about:blank"],{stdio:"ignore",windowsHide:true});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
let ws,seq=0;const pending=new Map(),errors=[];
async function command(method,params={}){
 return new Promise((resolve,reject)=>{const id=++seq;const timeout=setTimeout(()=>{pending.delete(id);reject(new Error("CDP timeout: "+method));},20000);pending.set(id,{resolve,reject,timeout});ws.send(JSON.stringify({id,method,params}));});
}
async function evaluate(expression){
 const r=await command("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});
 if(r.exceptionDetails)throw new Error(r.exceptionDetails.text);
 return r.result.value;
}
async function until(expression){
 for(let i=0;i<100;i++){if(await evaluate(expression))return;await delay(100);}
 throw new Error("Condition not reached: "+expression);
}
async function go(route){
 await command("Page.navigate",{url:base+route});
 await until("location.pathname === "+JSON.stringify(route)+" && document.readyState === 'complete'");
 await delay(250);
}
const checks=[];
function check(name,condition){assert.ok(condition,name);checks.push(name);console.log("PASS "+name);}
try{
 let endpoint;
 for(let i=0;i<50;i++){try{endpoint=(await(await fetch("http://127.0.0.1:"+port+"/json/list")).json()).find(t=>t.type==="page")?.webSocketDebuggerUrl;if(endpoint)break;}catch{}await delay(150);}
 ws=new WebSocket(endpoint);await new Promise(r=>ws.onopen=r);
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);clearTimeout(p.timeout);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);}else if(m.method==="Runtime.exceptionThrown")errors.push(m.params.exceptionDetails.text);};
 await command("Page.enable");await command("Runtime.enable");
 await command("Emulation.setDeviceMetricsOverride",{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await go("/pt-BR");
 await evaluate("document.getElementById('tab-truck').click()");
 check("segmento de carga troca texto e imagem",await evaluate("document.getElementById('tab-truck').getAttribute('aria-selected')==='true' && document.getElementById('fleet-panel').textContent.includes('Sua carga') && document.querySelector('#fleet-panel img').src.includes('caminhao')"));
 await evaluate("document.getElementById('tab-truck').focus()");
 await command("Input.dispatchKeyEvent",{type:"keyDown",key:"ArrowLeft",code:"ArrowLeft"});
 check("abas de frota funcionam por teclado",await evaluate("document.activeElement.id==='tab-bus' && document.getElementById('tab-bus').getAttribute('aria-selected')==='true'"));
 await evaluate("document.querySelector('.hotspot-2').click()");
 check("ponto da caixa abre a explicação correspondente",await evaluate("!document.getElementById('feature-2').hidden && document.getElementById('feature-0').hidden"));
 await evaluate("document.getElementById('journey-tab-2').click()");
 check("etapa de chegada apresenta coleta e relatório",await evaluate("document.querySelector('.journey-copy').textContent.includes('Conecte a caixa') && !!document.querySelector('.report-sheet')"));
 await evaluate("document.querySelector('.faq-list summary').click()");
 check("pergunta abre a resposta",await evaluate("document.querySelector('.faq-list details').open"));
 await evaluate("document.querySelector('.engineering summary').click();document.querySelector('.engineering video').load()");
 await until("document.querySelector('.engineering video').readyState>=1");
 check("vídeo 3D local disponível sem autoplay",await evaluate("document.querySelector('.engineering video').duration>=9.5 && !document.querySelector('.engineering video').autoplay"));
 await evaluate("document.querySelector('.header-actions button[aria-expanded]').click()");
 check("seletor abre os cinco idiomas",await evaluate("document.querySelectorAll('.header-actions ul:not([hidden]) a').length===5"));
 await evaluate("document.querySelector('.header-actions a[hreflang=en]').click()");
 await until("location.pathname==='/en' && document.documentElement.lang==='en'");
 check("seletor muda o conteúdo para inglês",await evaluate("document.querySelector('h1').innerText.includes('Every journey')"));
 for(const locale of ["pt-BR","en","es","fr","zh-CN"]){
   await go("/"+locale);
   for(const width of [320,390,768,1440]){
     await command("Emulation.setDeviceMetricsOverride",{width,height:900,deviceScaleFactor:1,mobile:width<640});
     await delay(80);
     check(locale+" sem overflow em "+width+"px",await evaluate("document.documentElement.scrollWidth<=window.innerWidth"));
   }
   check(locale+" sem mensagens de tradução ausentes",await evaluate("!document.body.innerText.includes('MISSING_MESSAGE')"));
 }
 await command("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await go("/pt-BR");
 await evaluate("document.querySelector('.menu-toggle').click()");
 check("menu móvel abre",await evaluate("!!document.querySelector('#mobile-nav')"));
 await evaluate("document.querySelector('#mobile-nav a[href$=\"#produto\"]').click()");
 check("menu móvel fecha após navegação",await evaluate("!document.querySelector('#mobile-nav')"));
 await go("/pt-BR/entrar");
 await evaluate("localStorage.removeItem('rotaguard.acesso');localStorage.removeItem('rotaguard.tentativas')");
 await command("Page.navigate",{url:base+"/pt-BR/app"});
 await until("location.pathname==='/pt-BR/entrar' && !!document.getElementById('pin')");
 check("download sem sessão redireciona para o PIN",true);
 await evaluate("document.getElementById('pin').value='000000';document.querySelector('.pin-form').requestSubmit()");
 await until("document.getElementById('pin-error').textContent.length>0");
 check("PIN errado mostra erro",await evaluate("document.getElementById('pin-error').textContent.includes('incorreto')"));
 const pin=process.env.ROTAGUARD_TEST_PIN;
 if(pin){
   await evaluate("document.getElementById('pin').value="+JSON.stringify(pin)+";document.querySelector('.pin-form').requestSubmit()");
   await until("location.pathname==='/pt-BR/app' && !!document.querySelector('.download-list')");
   check("PIN correto abre as cinco plataformas",await evaluate("document.querySelectorAll('.download-list>li').length===5"));
   check("PIN não é salvo no localStorage",await evaluate("!localStorage.getItem('rotaguard.acesso').includes("+JSON.stringify(pin)+")"));
   await command("Page.reload");await until("!!document.querySelector('.download-list')");
   check("sessão persiste após recarregar",true);
   const capture=await command("Page.captureScreenshot",{format:"png"});writeFileSync(path.join(output,"acesso-aplicativo.png"),Buffer.from(capture.data,"base64"));
   await evaluate("document.querySelector('.download-header button').click()");
   await until("location.pathname==='/pt-BR/entrar'");
   check("sair encerra a sessão",await evaluate("!localStorage.getItem('rotaguard.acesso')"));
 }
 check("nenhuma exceção JavaScript não tratada",errors.length===0);
 writeFileSync(path.join(output,"verificacao-navegador.json"),JSON.stringify({date:new Date().toISOString(),checks,errors},null,2));
 console.log(checks.length+" verificações de navegador concluídas");
}finally{ws?.close();child.kill();}
