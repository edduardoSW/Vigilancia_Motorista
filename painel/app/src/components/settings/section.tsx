"use client";

import { useEffect, useRef, useState } from "react";
import { bridge, type Configuracoes } from "@/lib/bridge";
import { useToast } from "@/components/ui/toast";

export type SecaoSalvavel = keyof Configuracoes;
export type SaveState = "idle" | "saving" | "saved";

// Casca de cada seção de Configurações: título, frase curta e linhas no desenho da prévia 8.
export function Section({ title, summary, children }: { title: string; summary?: string; children: React.ReactNode }) {
  return (
    <div className="anim-enter">
      <h2 className="font-titulo text-[22px] font-semibold leading-tight">{title}</h2>
      {summary && <p className="mt-1.5 text-[14px] text-grafite">{summary}</p>}
      <div className="mt-5 border-t border-fio">{children}</div>
    </div>
  );
}

export function Row({
  label,
  description,
  htmlFor,
  error,
  children,
}: {
  label: string;
  description?: string;
  htmlFor?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_260px] items-start gap-8 border-b border-fio py-5">
      <div>
        <label htmlFor={htmlFor} className="block text-[15px] font-semibold">
          {label}
        </label>
        {description && <p className="mt-1 text-[13.5px] text-grafite">{description}</p>}
        {error && (
          <p role="alert" className="mt-2 text-[13.5px] font-semibold text-alarme">
            {error}
          </p>
        )}
      </div>
      <div>{children}</div>
    </div>
  );
}

/** Salvar uma seção: "Salvando…", depois "Salvo", aviso curto e erro do Python em frase. */
export function useSaveSection(onSaved: (config: Configuracoes) => void) {
  const { toast } = useToast();
  const [state, setState] = useState<SaveState>("idle");
  const [erro, setErro] = useState<{ texto: string; campo?: string } | null>(null);
  const relogio = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => () => clearTimeout(relogio.current), []);

  async function salvar<S extends SecaoSalvavel>(secao: S, valores: Configuracoes[S], mensagem: string) {
    setState("saving");
    setErro(null);
    const resposta = await bridge.config_salvar(secao, valores);
    if (!resposta.ok) {
      setState("idle");
      setErro({ texto: resposta.erro, campo: resposta.campo });
      return false;
    }
    onSaved(resposta.dados);
    setState("saved");
    toast({ text: mensagem });
    clearTimeout(relogio.current);
    relogio.current = setTimeout(() => setState("idle"), 1800);
    return true;
  }

  return { state, erro, setErro, salvar };
}
