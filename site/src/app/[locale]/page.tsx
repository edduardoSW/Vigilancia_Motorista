import { Alarme } from "@/components/sections/alarme";
import { Cabine } from "@/components/sections/cabine";
import { Chegada } from "@/components/sections/chegada";
import { Contato } from "@/components/sections/contato";
import { FichaTecnica } from "@/components/sections/ficha-tecnica";
import { Hero } from "@/components/sections/hero";
import { Malha } from "@/components/sections/malha";
import { Motoristas } from "@/components/sections/motoristas";
import { Perguntas } from "@/components/sections/perguntas";
import { Piloto } from "@/components/sections/piloto";
import { Registro } from "@/components/sections/registro";
import { Relatorio } from "@/components/sections/relatorio";
import { Rodovia } from "@/components/sections/rodovia";
import { Rota } from "@/components/sections/rota";

// Direção "Escalas": Ato I (mundo → Brasil → rota → rodovia), Ato II (cabine → alarme → olho e registro),
// Ato III (garagem → relatório). Depois, o que o comprador e o motorista precisam para decidir.
export default function HomePage() {
  return (
    <>
      <Hero />
      <Malha />
      <Rota />
      <Rodovia />
      <Cabine />
      <Alarme />
      <Registro />
      <Chegada />
      <Relatorio />
      <div data-fim-escalas aria-hidden="true" />
      <Motoristas />
      <Piloto />
      <Perguntas />
      <FichaTecnica />
      <Contato />
    </>
  );
}
