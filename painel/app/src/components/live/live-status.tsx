import type { ScriptEstado } from "@/lib/bridge";
import tiposDeEvento from "@/content/tipos-de-evento.json";
import { cn } from "@/lib/utils";
import type { TiposDeEvento } from "./summary";

export const TIPOS = tiposDeEvento as TiposDeEvento;

export const FECHADO = "O script não está aberto. Abra o RotaGuard Teste neste computador e ele aparece aqui sozinho.";

export function horaCurta(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

/** "14:22:05" hoje; "10/09 16:39" em outro dia. */
export function quando(iso: string): string {
  const data = new Date(iso);
  const hoje = new Date();
  if (data.toDateString() === hoje.toDateString()) {
    return data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  const dia = data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  return `${dia} ${horaCurta(iso)}`;
}

export function fraseDeSituacao(estado: ScriptEstado | null, erro: string | null): string {
  if (erro) return erro;
  if (!estado) return "Procurando o script neste computador…";
  if (!estado.aberto) return FECHADO;
  const desde = estado.desde ? ` desde ${horaCurta(estado.desde)}` : "";
  const detalhe = estado.camera ?? estado.programa;
  return `Aberto${desde}${detalhe ? ` · ${detalhe}` : ""}`;
}

export function StatusLine({ estado, erro, className }: { estado: ScriptEstado | null; erro: string | null; className?: string }) {
  const aberto = Boolean(estado?.aberto) && !erro;
  return (
    <p role="status" aria-live="polite" className={cn("flex items-center gap-2.5", className)}>
      {aberto && <span aria-hidden="true" className="pulse-dot size-2 shrink-0 rounded-full bg-verde" />}
      <span className={aberto ? "font-semibold text-tinta" : "text-grafite"}>{fraseDeSituacao(estado, erro)}</span>
    </p>
  );
}
