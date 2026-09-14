"use client";

import Link from "next/link";
import { StatusLine, TIPOS } from "./live-status";
import { resumoDosEventos } from "./summary";
import { eventosVisiveis, useScriptLocal } from "./use-script-local";

// Bloco do Início (spec 018): situação do script local e o resumo desta sessão, com acesso à tela completa.
export function LiveScriptCard() {
  const { estado, erro, eventos } = useScriptLocal();
  const visiveis = eventosVisiveis(estado, eventos);
  const aberto = Boolean(estado?.aberto);

  return (
    <section aria-labelledby="teste-local" className="border-y border-fio py-4">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="teste-local" className="font-titulo text-[17px] font-semibold">
          Teste neste computador
        </h2>
        <Link href="/ao-vivo/" className="text-[13px] font-semibold text-verde hover:underline">
          Ver eventos
        </Link>
      </div>
      <StatusLine estado={estado} erro={erro} className="mt-2 text-[14px]" />
      {aberto && (
        <p className="mt-1 text-[13.5px] text-grafite">
          {visiveis.length === 0 ? "Nenhum evento nesta sessão ainda" : `${resumoDosEventos(visiveis, TIPOS)} nesta sessão`}
        </p>
      )}
    </section>
  );
}
