"use client";

import { geoCircle, geoEqualEarth, geoPath } from "d3-geo";
import { antipodaSolar } from "@/lib/solar";
import { useMinuto } from "@/lib/use-minuto";

/**
 * A noite neste instante sobre o mapa-múndi: círculo de 90° em volta do ponto oposto ao Sol,
 * mais uma faixa de crepúsculo civil (até 96°). Calculado no navegador e refeito a cada minuto;
 * no servidor não desenha nada (a hora do build seria mentira).
 */
export function NightShade({ escala, translacao }: { escala: number; translacao: [number, number] }) {
  const minuto = useMinuto();
  if (minuto === null) return null;

  const projecao = geoEqualEarth().scale(escala).translate(translacao);
  const caminho = geoPath(projecao);
  const centro = antipodaSolar(new Date(minuto * 60_000));
  const noite = caminho(geoCircle().center(centro).radius(90)());
  const crepusculo = caminho(geoCircle().center(centro).radius(96)());

  return (
    <g aria-hidden="true">
      <path d={crepusculo ?? undefined} fill="var(--c-veu-noite)" opacity="0.45" />
      <path d={noite ?? undefined} fill="var(--c-veu-noite)" />
    </g>
  );
}
