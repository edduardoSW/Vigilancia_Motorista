"use server";

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { routing } from "@/i18n/routing";
import {
  COOKIE_SESSAO,
  VALIDADE_SESSAO_S,
  bloqueado,
  criarSessao,
  limparErros,
  registrarErro,
  verificarPin,
} from "@/lib/sessao";

export type EstadoEntrar = { erro: null | "pin" | "bloqueio" | "config" };

function localeValido(valor: FormDataEntryValue | null): string {
  const texto = String(valor ?? "");
  return (routing.locales as readonly string[]).includes(texto) ? texto : routing.defaultLocale;
}

// Em Server Actions o next/root-params não funciona: o idioma chega por campo oculto.
export async function entrar(_anterior: EstadoEntrar, formulario: FormData): Promise<EstadoEntrar> {
  const locale = localeValido(formulario.get("locale"));
  const pin = String(formulario.get("pin") ?? "").trim();
  const cabecalhos = await headers();
  const ip = (cabecalhos.get("x-forwarded-for") ?? "").split(",")[0].trim() || "local";

  if (bloqueado(ip)) return { erro: "bloqueio" };
  if (!/^\d{4,12}$/.test(pin)) {
    registrarErro(ip);
    return { erro: "pin" };
  }

  const resultado = verificarPin(pin);
  if (resultado === "sem-configuracao") return { erro: "config" };
  if (resultado === "incorreto") {
    registrarErro(ip);
    return { erro: bloqueado(ip) ? "bloqueio" : "pin" };
  }

  const sessao = criarSessao();
  if (!sessao) return { erro: "config" };
  limparErros(ip);
  (await cookies()).set(COOKIE_SESSAO, sessao, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: VALIDADE_SESSAO_S,
  });
  redirect(`/${locale}/app`);
}

export async function sair(formulario: FormData): Promise<void> {
  const locale = localeValido(formulario.get("locale"));
  (await cookies()).delete(COOKIE_SESSAO);
  redirect(`/${locale}/entrar`);
}
