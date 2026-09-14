"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDecisions } from "@/components/decisions-provider";
import { Icon, Wordmark } from "@/components/icons";
import { dados, nomeDoVeiculo, veiculoDe } from "@/content";
import { momentosDaViagem } from "@/content/moments";
import { cn } from "@/lib/utils";

// Coluna das viagens (prévia 2): caixa conectada no topo, viagens que chegaram e o acesso a veículos e caixas.
const TRIPS = [...dados.viagens].sort((a, b) => Date.parse(b.chegada) - Date.parse(a.chegada));
const MOMENTS = Object.fromEntries(TRIPS.map((trip) => [trip.id, momentosDaViagem(trip)]));

export function Sidebar() {
  const route = usePathname() || "/";
  const { decisions } = useDecisions();
  const box = dados.coletas[0];
  const boxVehicle = box ? veiculoDe(box.veiculo) : undefined;
  const onVehicles = route.startsWith("/veiculos");

  return (
    <aside className="no-print flex h-screen flex-col gap-[18px] border-r border-fio bg-lateral px-4 pb-[18px] pt-[22px]">
      <div className="flex items-center gap-2.5 px-2">
        <Wordmark />
        <span className="ml-auto text-[12px] font-medium text-grafite">{dados.empresa.nome}</span>
      </div>

      {box && (
        <Link
          href="/"
          aria-current={route === "/" ? "page" : undefined}
          className={cn(
            "block rounded-[14px] border bg-white px-4 pb-4 pt-3.5 transition-colors",
            route === "/" ? "border-verde/35" : "border-fio hover:border-verde/25",
          )}
        >
          <span className="flex items-center gap-2 text-[12.5px] text-grafite">
            <span aria-hidden="true" className="size-2 rounded-full bg-verde shadow-[0_0_0_4px_rgb(16_62_49/0.12)]" />
            Caixa conectada agora
          </span>
          <strong className="mt-1.5 block text-[16px]">{boxVehicle ? nomeDoVeiculo(boxVehicle.tipo, boxVehicle.prefixo) : box.caixa}</strong>
          <span className="mt-0.5 block text-[13px] text-grafite">Lendo a viagem de ontem</span>
          <span aria-hidden="true" className="mt-3 block h-1.5 overflow-hidden rounded-[3px] bg-[#e5ebe1]">
            <span className="block h-full rounded-[3px] bg-verde" style={{ width: `${box.progresso}%` }} />
          </span>
          <span className="mt-2 flex justify-between text-[12.5px] text-grafite">
            <span>Lendo o registro</span>
            <span>{box.progresso}%</span>
          </span>
        </Link>
      )}

      <nav aria-label="Viagens" className="flex min-h-0 flex-col">
        <p className="px-2 text-[13px] font-bold">Viagens</p>
        <p className="mb-2 mt-3 px-2 text-[12px] text-grafite">Chegaram hoje</p>
        <ul className="flex min-h-0 flex-col gap-1 overflow-y-auto">
          {TRIPS.map((trip) => {
            const pending = MOMENTS[trip.id].filter((moment) => !decisions[moment.id]).length;
            const active = route.startsWith(`/viagens/${trip.id}`);
            return (
              <li key={trip.id}>
                <Link
                  href={`/viagens/${trip.id}/`}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2.5 rounded-[10px] px-3 py-[11px] transition-colors",
                    active ? "bg-white shadow-[0_1px_2px_rgb(23_59_48/0.08),0_0_0_1px_var(--color-fio)]" : "hover:bg-white/60",
                  )}
                >
                  <span className="min-w-0">
                    <b className="block text-[14.5px] font-bold">{nomeDoVeiculo(trip.tipo, trip.veiculo)}</b>
                    <span className="block truncate text-[12.5px] text-grafite">{trip.linha}</span>
                  </span>
                  {pending > 0 ? (
                    <span className="rounded-[7px] bg-lima px-2 py-[3px] text-[12.5px] font-bold text-verde">{pending} para ver</span>
                  ) : (
                    <span className="text-[12.5px] font-semibold text-grafite">Revisada</span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="mt-auto border-t border-fio pt-3">
        <Link
          href="/veiculos/"
          aria-current={onVehicles ? "page" : undefined}
          className={cn("flex items-center gap-2.5 rounded-[8px] p-2 text-[13.5px] transition-colors", onVehicles ? "bg-white font-semibold" : "hover:bg-white/60")}
        >
          <Icon name="bus" size={18} />
          Veículos e caixas
        </Link>
      </div>
    </aside>
  );
}
