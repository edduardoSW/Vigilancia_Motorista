"use client";

import { useState, useSyncExternalStore } from "react";

type Frota = "caminhao" | "onibus";

function assinarUrl(avisar: () => void) {
  window.addEventListener("popstate", avisar);
  return () => window.removeEventListener("popstate", avisar);
}

function frotaDaUrl(): Frota | null {
  const pedida = new URLSearchParams(window.location.search).get("frota");
  return pedida === "onibus" || pedida === "caminhao" ? pedida : null;
}

/** Troca a cena da cabine entre caminhão e ônibus. As portas da primeira tela chegam com ?frota=. */
export function VehicleToggle({
  rotulo,
  rotuloCaminhao,
  rotuloOnibus,
  caminhao,
  onibus,
}: {
  rotulo: string;
  rotuloCaminhao: string;
  rotuloOnibus: string;
  caminhao: React.ReactNode;
  onibus: React.ReactNode;
}) {
  const pedidaNaUrl = useSyncExternalStore(assinarUrl, frotaDaUrl, () => null);
  const [escolhida, setEscolhida] = useState<Frota | null>(null);
  const frota: Frota = escolhida ?? pedidaNaUrl ?? "caminhao";

  const opcoes: [Frota, string][] = [
    ["caminhao", rotuloCaminhao],
    ["onibus", rotuloOnibus],
  ];

  return (
    <div>
      <div role="group" aria-label={rotulo} className="inline-flex border border-noite-texto">
        {opcoes.map(([valor, texto]) => (
          <button
            key={valor}
            type="button"
            aria-pressed={frota === valor}
            onClick={() => setEscolhida(valor)}
            className="min-h-11 px-5 text-[0.95rem] font-semibold transition-colors aria-pressed:bg-noite-texto aria-pressed:text-noite"
          >
            {texto}
          </button>
        ))}
      </div>
      <div className="mt-5">
        <div hidden={frota !== "caminhao"}>{caminhao}</div>
        <div hidden={frota !== "onibus"}>{onibus}</div>
      </div>
    </div>
  );
}
