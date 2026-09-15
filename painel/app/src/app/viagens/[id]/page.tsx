import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MomentList } from "@/components/moment-list";
import { PrintButton } from "@/components/print-button";
import { TripBar } from "@/components/trip-bar";
import { TripPeople } from "@/components/trip/trip-people";
import { Glyph } from "@/components/ui/glyph";
import { dados, dia, duracao, hora, minutosEntre, nomeDoVeiculo, resumoDaViagem, rotuloDe, segundos, viagemDe } from "@/content";
import { contarPorTipo, momentosDaViagem, naMadrugada } from "@/content/moments";

export const dynamicParams = false;

export function generateStaticParams() {
  return dados.viagens.map((trip) => ({ id: trip.id }));
}

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const trip = viagemDe((await params).id);
  return { title: trip ? `${nomeDoVeiculo(trip.tipo, trip.veiculo)} · RotaGuard` : "RotaGuard" };
}

const NUMBERS = ["nenhum", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"];
const inWords = (value: number) => NUMBERS[value] ?? String(value);

function joinList(parts: string[]) {
  return parts.length > 1 ? `${parts.slice(0, -1).join(", ")} e ${parts.at(-1)}` : (parts[0] ?? "");
}

// Viagem como página de relatório (prévia 2): resumo em frases, barra da viagem e momentos para verificar.
export default async function TripPage({ params }: Props) {
  const trip = viagemDe((await params).id);
  if (!trip) notFound();

  const summary = resumoDaViagem(trip);
  const moments = momentosDaViagem(trip);
  const byType = contarPorTipo(moments);
  const atNight = moments.filter((moment) => naMadrugada(moment.inicio)).length;
  const pauses = trip.jornada.filter((part) => part.tipo === "pausa");
  const pauseMinutes = pauses.reduce((total, part) => total + minutosEntre(part.inicio, part.fim), 0);

  const kinds = joinList(
    [
      byType.sono ? `${byType.sono} de sono` : "",
      byType.celular ? `${byType.celular} de celular` : "",
      byType.jornada ? `${byType.jornada} de direção sem pausa` : "",
      byType.outro ? `${byType.outro} fora do padrão` : "",
    ].filter(Boolean),
  );
  const nightText =
    atNight === 0
      ? ""
      : atNight === moments.length
        ? moments.length === 1 ? ", na madrugada" : ", todos na madrugada"
        : `, ${inWords(atNight)} ${atNight === 1 ? "deles" : "deles"} na madrugada`;

  return (
    <section className="max-w-[900px] px-14 pb-16 pt-[34px]">
      <Link href="/viagens/" className="no-print text-[13px] font-semibold text-grafite transition-colors hover:text-tinta">
        Voltar para Viagens
      </Link>
      <div className="mt-2 flex items-start justify-between gap-6">
        <div>
          <h1 className="font-titulo text-[34px] font-semibold leading-[1.1] tracking-[-0.01em]">{nomeDoVeiculo(trip.tipo, trip.veiculo)}</h1>
          <p className="mt-2 text-[15px] text-grafite">
            {trip.linha} · {dia(trip.saida)} às {hora(trip.saida)} até {dia(trip.chegada)} às {hora(trip.chegada)}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Link
            href="/guia/?capitulo=verificar-momentos&passo=verificar"
            className="no-print mr-1 inline-flex h-9 items-center gap-1.5 rounded-[8px] px-2 text-[13px] font-medium text-grafite transition-colors hover:bg-lateral hover:text-tinta"
          >
            <Glyph name="book" size={16} />
            Guia
          </Link>
          <PrintButton />
        </div>
      </div>

      <TripPeople viagemId={trip.id} />

      <h2 className="mb-2.5 mt-[30px] font-titulo text-[20px] font-semibold">Resumo</h2>
      <p className="max-w-[760px] text-[17px] leading-[1.65]">
        A viagem durou <b>{duracao(summary.duracaoMin)}</b>
        {pauses.length === 0 ? (
          <>
            , <b>sem pausas</b>.
          </>
        ) : (
          <>
            , com <b>{pauses.length === 1 ? `uma pausa de ${duracao(pauseMinutes)}` : `${pauses.length} pausas somando ${duracao(pauseMinutes)}`}</b>.
          </>
        )}{" "}
        {moments.length ? (
          <>
            A caixa separou{" "}
            <b>
              {moments.length} {moments.length === 1 ? "momento" : "momentos"} para você verificar
            </b>
            : {kinds}
            {nightText}.
          </>
        ) : (
          "Nenhum momento precisou de verificação."
        )}{" "}
        {trip.integridade.situacao === "conferida" ? "O registro chegou completo e sem alteração." : "O registro ainda está sendo conferido."}
      </p>

      <TripBar trip={trip} moments={moments} />

      <MomentList viagemId={trip.id} />
      <p className="mt-4 text-[12.5px] text-grafite">
        Os alertas ajudam a sua avaliação e não são diagnóstico. Depois de confirmar, dá para registrar se o motorista foi
        orientado.
      </p>

      <details className="no-print mt-8 text-[14px]">
        <summary className="cursor-pointer font-semibold">Ver tudo o que a caixa registrou ({trip.eventos.length})</summary>
        <table className="mt-3 w-full text-left">
          <tbody className="divide-y divide-fio border-y border-fio">
            {trip.eventos.map((event) => (
              <tr key={event.id}>
                <td className="w-16 py-2.5 tabular-nums text-grafite">{hora(event.hora)}</td>
                <td className="py-2.5">{rotuloDe(event.tipo)}</td>
                <td className="py-2.5 text-right tabular-nums text-grafite">{event.duracaoS ? segundos(event.duracaoS) : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}
