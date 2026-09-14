"use client";

import Link from "next/link";
import { useSession } from "@/components/session-provider";
import { Row, Section } from "./section";

// Sobre o RotaGuard: só o que o painel sabe de verdade. Textos legais entram quando existirem (spec 016, CFG-08).
export function AboutSection() {
  const { estado } = useSession();

  return (
    <Section title="Sobre o RotaGuard">
      <Row label="Versão do painel">
        <p className="text-[15px]">{estado?.versao ?? "—"}</p>
      </Row>
      <Row label="Empresa">
        <p className="text-[15px]">{estado?.empresa?.nome ?? "—"}</p>
        {estado?.modo === "demonstracao" && <p className="text-[13.5px] text-grafite">Demonstração, com dados fictícios</p>}
      </Row>
      <Row label="Onde ficam os dados" description="Nada vai para a internet nesta versão.">
        <p className="text-[15px]">Os dados ficam guardados neste computador</p>
      </Row>
      <Row label="Como usar">
        <Link href="/guia/?capitulo=privacidade" className="text-[14px] font-semibold text-verde hover:underline">
          Privacidade no guia de uso
        </Link>
      </Row>
    </Section>
  );
}
