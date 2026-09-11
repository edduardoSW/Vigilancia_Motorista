import assert from "node:assert/strict";
import {randomBytes} from "node:crypto";
import {test} from "node:test";
import {ACCESS_KEY, ATTEMPT_KEY, ACCESS_TTL, ATTEMPT_TTL, hashPin, signIn, hasAccess, signOut} from "../../src/lib/acesso-local.ts";
const pin = Array.from(randomBytes(8), n => n % 10).join("");
const config = {salt:randomBytes(16).toString("hex"),hash:""};
config.hash = await hashPin(pin,config.salt);
const storage = () => {const values = new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};};
test("PIN local: acesso correto persiste entre leituras e expira após 12 horas",async()=>{
 const s=storage(), now=Date.now();
 assert.equal(await signIn(pin,s,config,now),"ok");
 assert.equal(hasAccess(s,now,config),true);
 assert.equal(hasAccess(s,now+ACCESS_TTL,config),false);
 assert.equal(s.getItem(ACCESS_KEY).includes(pin),false);
 signOut(s);
 assert.equal(hasAccess(s,now,config),false);
});
test("PIN local: erros persistem entre chamadas e bloqueiam cinco tentativas",async()=>{
 const s=storage(), now=Date.now(),wrong=pin.slice(0,-1)+((Number(pin.at(-1))+1)%10);
 for(let i=0;i<4;i++)assert.equal(await signIn(wrong,s,config,now),"pin");
 assert.equal(await signIn(wrong,s,config,now),"blocked");
 assert.equal(await signIn(pin,s,config,now+1),"blocked");
 assert.equal(hasAccess(s,now,config),false);
 assert.equal(await signIn(pin,s,config,now+ATTEMPT_TTL),"ok");
 assert.equal(s.getItem(ATTEMPT_KEY),null);
});
test("PIN local: sessão inválida, credencial diferente e datas adulteradas são recusadas",async()=>{
 const s=storage(),now=Date.now();
 for(const bad of ["true","{","null",JSON.stringify({version:1,credential:config.hash,expiresAt:now+ACCESS_TTL})]){
 s.setItem(ACCESS_KEY,bad);assert.equal(hasAccess(s,now,config),false);
 }
 await signIn(pin,s,config,now);
 assert.equal(hasAccess(s,now,{...config,hash:"other"}),false);
 const session=JSON.parse(s.getItem(ACCESS_KEY));session.expiresAt+=1000;
 s.setItem(ACCESS_KEY,JSON.stringify(session));assert.equal(hasAccess(s,now,config),false);
});
test("PIN local: armazenamento indisponível não concede acesso",async()=>{
 const s={getItem:()=>{throw new Error("blocked")},setItem:()=>{throw new Error("blocked")},removeItem:()=>{}};
 assert.equal(await signIn(pin,s,config),"storage");
 assert.equal(hasAccess(s),false);
});
