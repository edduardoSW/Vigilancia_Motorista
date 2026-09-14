import { hora, isoLocal, minutosEntre, posicao, type Viagem } from "@/content";
import type { Momento } from "@/content/moments";

// Barra única da viagem (prévia 2): direção e pausas em proporção do tempo, com os momentos numerados em cima.
const pct = (value: number) => `${(value * 100).toFixed(2)}%`;

function hourLabels(trip: Viagem) {
  const labels: { iso: string; text: string }[] = [];
  const first = new Date(trip.saida);
  first.setMinutes(0, 0, 0);
  first.setHours(first.getHours() + (first.getHours() % 2 === 0 ? 2 : 1));
  for (let d = first; d.getTime() < Date.parse(trip.chegada); d = new Date(d.getTime() + 2 * 3600000)) {
    const iso = isoLocal(d);
    const place = posicao(trip, iso);
    // Longe o bastante de "saída" e "chegada" para os rótulos não encostarem.
    if (place > 0.15 && place < 0.85) labels.push({ iso, text: iso.slice(11, 16) });
  }
  return labels;
}

export function TripBar({ trip, moments }: { trip: Viagem; moments: Momento[] }) {
  return (
    <figure className="mt-[22px]" aria-label="Linha da viagem com direção, pausas e os momentos numerados">
      <div className="relative mb-1 h-[30px]">
        {moments.map((moment) => (
          <a
            key={moment.id}
            href={`#momento-${moment.numero}`}
            title={`${moment.numero}. ${hora(moment.inicio)} · ${moment.titulo}`}
            className="absolute bottom-1 grid size-6 -translate-x-1/2 place-items-center rounded-full bg-tinta text-[12px] font-bold text-white"
            style={{ left: pct(posicao(trip, moment.inicio)) }}
          >
            {moment.numero}
          </a>
        ))}
      </div>
      <div className="flex h-3 gap-[3px]">
        {trip.jornada.map((part) => (
          <div
            key={part.inicio}
            title={`${part.tipo === "direcao" ? "Dirigindo" : "Pausa"} das ${hora(part.inicio)} às ${hora(part.fim)}`}
            className={part.tipo === "direcao" ? "rounded-[6px] bg-verde" : "rounded-[6px] bg-[#d9e0d5]"}
            style={{ flexGrow: minutosEntre(part.inicio, part.fim), flexBasis: 0 }}
          />
        ))}
      </div>
      <div className="relative mt-2 h-4 text-[12.5px] text-grafite">
        <span className="absolute left-0">{hora(trip.saida)} saída</span>
        {hourLabels(trip).map((label) => (
          <span key={label.iso} className="absolute -translate-x-1/2" style={{ left: pct(posicao(trip, label.iso)) }}>
            {label.text}
          </span>
        ))}
        <span className="absolute right-0">{hora(trip.chegada)} chegada</span>
      </div>
    </figure>
  );
}
