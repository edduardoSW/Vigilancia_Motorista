"use client";
import {useState, type FormEvent} from "react";
import {useTranslations} from "next-intl";
import {useRouter} from "@/i18n/navigation";
import {signIn} from "@/lib/acesso-local";
import {Arrow} from "@/components/icons";
export function PinForm() {
const t=useTranslations("entrar"); const router=useRouter();
const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
async function submit(e:FormEvent<HTMLFormElement>) {
e.preventDefault(); if(busy)return;setBusy(true);setError("");
const form=e.currentTarget;const pin=String(new FormData(form).get("pin")??"");
try {const result=await signIn(pin,window.localStorage);
if(result==="ok"){form.reset();window.dispatchEvent(new Event("rotaguard-acesso"));router.replace("/app");}
else setError(t(result==="blocked"?"erroBloqueio":result==="storage"?"erroStorage":"erroPin"));
}catch{setError(t("erroStorage"));}finally{setBusy(false);}
}
return <form onSubmit={submit} className="pin-form"><label htmlFor="pin">{t("pin")}</label><input id="pin" name="pin" type="password" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{4,12}" minLength={4} maxLength={12} required aria-invalid={!!error} aria-describedby="pin-error pin-note"/><p id="pin-error" className="pin-error" role="status">{error}</p><button type="submit" className="action action-dark" disabled={busy}>{t(busy?"enviando":"botao")}<span><Arrow diagonal/></span></button><p id="pin-note" className="pin-note">{t("nota")}</p></form>;
}
