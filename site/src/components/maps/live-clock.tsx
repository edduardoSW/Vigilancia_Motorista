"use client";

import { useLocale } from "next-intl";
import { useMinuto } from "@/lib/use-minuto";

/** Hora de Brasília, atualizada a cada minuto. No servidor mostra "--:--" para não congelar a hora do build. */
export function LiveClock() {
  const locale = useLocale();
  const minuto = useMinuto();
  const texto =
    minuto === null
      ? "--:--"
      : new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" }).format(
          new Date(minuto * 60_000)
        );

  return <time className="numero">{texto}</time>;
}
