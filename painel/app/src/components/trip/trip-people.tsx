"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession } from "@/components/session-provider";
import { Glyph } from "@/components/ui/glyph";
import { motoristaDe, nomeDoVeiculo, veiculoDe, viagemDe } from "@/content";
import { bridge, type Motorista, type Veiculo } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { diasAte, formatarData, hojeIso, mesAno, situacaoCnh } from "@/lib/validators";

// Veículo e motorista em destaque no relatório (spec 019, VIA-01): quem dirigiu fica claro logo no topo da viagem.
function textoDaCnh(motorista: Motorista) {
  const hoje = hojeIso();
  const situacao = situacaoCnh(motorista.cnh_validade, hoje);
  if (situacao === "vencida") return { texto: `Categoria ${motorista.cnh_categoria} · vencida em ${formatarData(motorista.cnh_validade)}`, alarme: true };
  if (situacao === "vence_em_breve") {
    const dias = diasAte(motorista.cnh_validade, hoje);
    return { texto: `Categoria ${motorista.cnh_categoria} · ${dias === 0 ? "vence hoje" : `vence em ${dias} ${dias === 1 ? "dia" : "dias"}`}`, alarme: true };
  }
  return { texto: `Categoria ${motorista.cnh_categoria} · vale até ${mesAno(motorista.cnh_validade)}`, alarme: false };
}

function textoDoTermo(termo: Motorista["termo"]) {
  if (!termo.assinado) return { texto: "Falta registrar: os vídeos ficam trancados", alarme: true };
  const data = termo.data ? `Assinado em ${formatarData(termo.data)}` : "Assinado";
  return { texto: `${data} · ${termo.arquivo ? "com o arquivo do termo" : "sem o arquivo do termo"}`, alarme: false };
}

export function TripPeople({ viagemId }: { viagemId: string }) {
  const viagem = viagemDe(viagemId);
  const { usuario } = useSession();
  const [motorista, setMotorista] = useState<Motorista | null | undefined>(undefined);
  const [veiculo, setVeiculo] = useState<Veiculo | null>(null);
  const usuarioId = usuario?.id ?? null;

  useEffect(() => {
    if (usuarioId === null || !viagem) return;
    let vivo = true;
    Promise.all([bridge.motoristas_listar(), bridge.veiculos_listar()]).then(([motoristas, veiculos]) => {
      if (!vivo) return;
      setMotorista(motoristas.ok ? (motoristas.dados.find((item) => item.ref === viagem.motorista) ?? null) : null);
      if (veiculos.ok) setVeiculo(veiculos.dados.find((item) => item.numero === viagem.veiculo) ?? null);
    });
    return () => {
      vivo = false;
    };
  }, [usuarioId, viagem]);

  if (!viagem) return null;
  const doDemo = veiculoDe(viagem.veiculo);
  const cnh = motorista ? textoDaCnh(motorista) : null;
  const termo = motorista ? textoDoTermo(motorista.termo) : null;

  return (
    <section aria-label="Veículo e motorista" className="mt-6 grid grid-cols-2 gap-3">
      <div className="rounded-[12px] border border-fio bg-superficie p-4">
        <span className="flex items-center gap-2 text-[13px] text-grafite">
          <Glyph name="vehicle" size={16} />
          Veículo
        </span>
        <b className="mt-1.5 block font-titulo text-[20px] font-semibold leading-tight">{nomeDoVeiculo(viagem.tipo, viagem.veiculo)}</b>
        <span className="block text-[13.5px] text-grafite">{[veiculo?.placa, doDemo?.descricao].filter(Boolean).join(" · ") || "Sem cadastro"}</span>
        <dl className="mt-3 grid grid-cols-[88px_minmax(0,1fr)] gap-y-1 text-[13.5px]">
          <dt className="text-grafite">Transporta</dt>
          <dd>{viagem.tipo === "caminhao" ? "Carga" : "Passageiros"}</dd>
          <dt className="text-grafite">Caixa</dt>
          <dd>{viagem.caixa}</dd>
        </dl>
      </div>

      <div className="rounded-[12px] border border-fio bg-superficie p-4">
        <span className="flex items-center gap-2 text-[13px] text-grafite">
          <Glyph name="driver" size={16} />
          Motorista
        </span>
        <b className="mt-1.5 block font-titulo text-[20px] font-semibold leading-tight">{motorista?.nome ?? motoristaDe(viagem.motorista)?.nome ?? "Não confirmado"}</b>
        <span className="block text-[13.5px] text-grafite">
          {motorista ? `Matrícula ${motorista.matricula}` : motorista === null ? "Motorista sem cadastro neste painel" : "Carregando o cadastro…"}
        </span>
        {motorista && cnh && termo && (
          <>
            <dl className="mt-3 grid grid-cols-[88px_minmax(0,1fr)] gap-y-1 text-[13.5px]">
              <dt className="text-grafite">CNH</dt>
              <dd className={cn("min-w-0", cnh.alarme && "font-semibold text-alarme")}>{cnh.texto}</dd>
              <dt className="text-grafite">Termo</dt>
              <dd className={cn("min-w-0", termo.alarme && "font-semibold text-alarme")}>{termo.texto}</dd>
            </dl>
            <Link href={`/motoristas/?abrir=${motorista.id}`} className="no-print btn btn-small mt-3">
              Ver cadastro
            </Link>
          </>
        )}
      </div>
    </section>
  );
}
