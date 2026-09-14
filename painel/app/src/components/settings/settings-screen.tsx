"use client";

import { useEffect, useState } from "react";
import { bridge, type Configuracoes } from "@/lib/bridge";
import { useSession } from "@/components/session-provider";
import { PageHeader } from "@/components/ui/page-header";
import { AboutSection } from "./about-section";
import { AccessSection } from "./access-section";
import { AppearanceSection } from "./appearance-section";
import { BackupSection } from "./backup-section";
import { CompanySection } from "./company-section";
import { RetentionSection } from "./retention-section";
import { RulesSection } from "./rules-section";
import { SideList } from "./side-list";

const SECOES = [
  { id: "empresa", label: "Empresa" },
  { id: "regras", label: "Regras da viagem" },
  { id: "guarda", label: "Vídeos e guarda dos dados" },
  { id: "copia", label: "Cópia de segurança" },
  { id: "acesso", label: "Acesso" },
  { id: "aparencia", label: "Aparência" },
  { id: "sobre", label: "Sobre o RotaGuard" },
] as const;

type SecaoId = (typeof SECOES)[number]["id"];

// Configurações (spec 016; prévia 8 com a direção "menos cara de IA"): só o administrador.
export function SettingsScreen() {
  const { pode } = useSession();
  const permitido = pode("configuracoes");
  const [secao, setSecao] = useState<SecaoId>("empresa");
  const [config, setConfig] = useState<Configuracoes | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!permitido) return;
    let vivo = true;
    bridge.config_ler().then((resposta) => {
      if (!vivo) return;
      if (resposta.ok) setConfig(resposta.dados);
      else setErro(resposta.erro);
    });
    return () => {
      vivo = false;
    };
  }, [permitido]);

  const resumo = config
    ? `${config.empresa.nome} · direção contínua até ${Math.floor(config.regras.direcao_continua_min / 60)} h ${String(config.regras.direcao_continua_min % 60).padStart(2, "0")} · vídeos por ${config.guarda.videos_dias} dias`
    : "Toda mudança vai para o registro de atividades, com o seu nome.";

  return (
    <section className="anim-enter max-w-[1040px] px-14 pb-16 pt-[34px]">
      <PageHeader title="Configurações" summary={permitido ? resumo : "Só o administrador vê esta área."} guide={{ capitulo: "copia" }} />

      {permitido && (
        <div className="mt-8 grid grid-cols-[230px_minmax(0,1fr)] gap-12">
          <div>
            <SideList label="Seções das configurações" items={[...SECOES]} value={secao} onChange={setSecao} />
          </div>
          <div className="min-w-0">
            {erro && (
              <p role="alert" className="text-[14px] text-alarme">
                {erro}
              </p>
            )}
            {!config && !erro && <p className="text-[14px] text-grafite">Carregando…</p>}
            {config && (
              <div key={secao}>
                {secao === "empresa" && <CompanySection config={config} onSaved={setConfig} />}
                {secao === "regras" && <RulesSection config={config} onSaved={setConfig} />}
                {secao === "guarda" && <RetentionSection config={config} onSaved={setConfig} />}
                {secao === "copia" && <BackupSection />}
                {secao === "acesso" && <AccessSection config={config} onSaved={setConfig} />}
                {secao === "aparencia" && <AppearanceSection config={config} onSaved={setConfig} />}
                {secao === "sobre" && <AboutSection />}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
