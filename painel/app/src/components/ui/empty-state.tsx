"use client";

import Link from "next/link";
import { useSession } from "@/components/session-provider";
import type { EstadoVazio } from "@/content/estados-vazios";

// Estado vazio (spec 030, SDF-04): uma frase do que falta e o próximo passo. Vai dentro da tabela ou dos cards (que já
// desenham a borda), ou sozinho numa tela sem lista. Sem ilustração nem ícone: só o texto e o botão.
export function EmptyState({ estado, onAcao, className }: { estado: EstadoVazio; onAcao?: () => void; className?: string }) {
  const { pode } = useSession();
  const acao = estado.acao && (!estado.acao.precisa || pode(estado.acao.precisa)) && (estado.acao.href || onAcao) ? estado.acao : null;
  return (
    <div data-vazio className={className}>
      <p className="text-[15px] font-semibold text-tinta">{estado.titulo}</p>
      <p className="mt-1 max-w-[620px] text-[14px] leading-relaxed text-grafite">{estado.texto}</p>
      {acao &&
        (acao.href ? (
          <Link href={acao.href} className="btn btn-small mt-3.5">
            {acao.rotulo}
          </Link>
        ) : (
          <button type="button" className="btn btn-small btn-primary mt-3.5" onClick={onAcao}>
            {acao.rotulo}
          </button>
        ))}
    </div>
  );
}
