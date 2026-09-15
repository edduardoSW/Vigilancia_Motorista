"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useDecisions } from "@/components/decisions-provider";
import { plural } from "@/components/drivers/use-list-shortcuts";
import { mostrarPrimeirosPassos, primeirosPassos } from "@/components/home/first-steps";
import { LiveScriptCard } from "@/components/live/live-script-card";
import { useSession } from "@/components/session-provider";
import { Glyph } from "@/components/ui/glyph";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { nomeDoVeiculo as nomeNaFrota } from "@/components/vehicles/vehicle-labels";
import { dados, dia, hora, motoristaDe, nomeDoVeiculo, veiculoDe } from "@/content";
import { momentosDaViagem } from "@/content/moments";
import { bridge, type Caixa, type InicioResumo, type Motorista, type Usuario, type Veiculo } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { diasAte, formatarData, hojeIso, situacaoCnh } from "@/lib/validators";

// Início (spec 014; spec 019, INT-02): começa por "O que fazer agora", um card por tarefa, cada um com o seu botão.
// Depois vêm os Primeiros passos numa barra (a lista abre em "Ver todos"), as viagens que faltam verificar, a caixa
// conectada, os avisos (CNH, caixa, cópia) e o teste neste computador. Viagens e caixa vêm do demo até a leitura real existir.

interface Cadastros {
  motoristas: Motorista[];
  veiculos: Veiculo[];
  caixas: Caixa[];
  pessoas: Usuario[] | null;
  resumo: InicioResumo | null;
}

interface Aviso {
  id: string;
  tipo: "cnh" | "caixa" | "copia";
  titulo: string;
  detalhe: string;
  href: string;
  acao: string;
}

interface Tarefa {
  id: string;
  titulo: string;
  detalhe: React.ReactNode;
  href: string;
  acao: string;
  principal?: boolean;
  alarme?: boolean;
}

const VIAGENS = [...dados.viagens]
  .sort((a, b) => Date.parse(b.chegada) - Date.parse(a.chegada))
  .map((viagem) => ({ viagem, momentos: momentosDaViagem(viagem).map((momento) => momento.id) }));

const COLETA = dados.coletas[0];
const VEICULO_DA_COLETA = COLETA ? veiculoDe(COLETA.veiculo) : undefined;
const NOME_DA_COLETA = COLETA ? (VEICULO_DA_COLETA ? nomeDoVeiculo(VEICULO_DA_COLETA.tipo, VEICULO_DA_COLETA.prefixo) : COLETA.caixa) : "";

function avisosDe(cadastros: Cadastros, administra: boolean, hoje: string): Aviso[] {
  const avisos: Aviso[] = [];
  for (const motorista of cadastros.motoristas) {
    if (motorista.situacao !== "ativo") continue;
    const situacao = situacaoCnh(motorista.cnh_validade, hoje);
    if (situacao === "ok") continue;
    const dias = diasAte(motorista.cnh_validade, hoje);
    avisos.push({
      id: `cnh-${motorista.id}`,
      tipo: "cnh",
      titulo:
        situacao === "vencida"
          ? `CNH de ${motorista.nome} vencida em ${formatarData(motorista.cnh_validade)}`
          : dias === 0
            ? `CNH de ${motorista.nome} vence hoje`
            : `CNH de ${motorista.nome} vence em ${plural(dias, "dia", "dias")}`,
      detalhe:
        situacao === "vencida"
          ? "As viagens dele continuam chegando. Peça a CNH nova e atualize o cadastro."
          : `Vale até ${formatarData(motorista.cnh_validade)}. Peça a CNH nova ao motorista.`,
      href: `/motoristas/?abrir=${motorista.id}`,
      acao: "Abrir cadastro",
    });
  }
  for (const caixa of cadastros.caixas) {
    if (caixa.situacao === "ok") continue;
    const veiculo = cadastros.veiculos.find((item) => item.id === caixa.veiculo_id);
    const bloqueada = caixa.situacao === "bloqueada";
    avisos.push({
      id: `caixa-${caixa.id}`,
      tipo: "caixa",
      titulo: bloqueada ? `Caixa ${caixa.codigo} bloqueada pela RotaGuard` : `Caixa ${caixa.codigo} precisa de atenção`,
      detalhe: [veiculo ? `${nomeNaFrota(veiculo)}.` : "", bloqueada ? "Não instale em nenhum veículo e fale com a RotaGuard." : (caixa.detalhe ?? "")]
        .filter(Boolean)
        .join(" "),
      href: "/veiculos/",
      acao: "Ver caixas",
    });
  }
  const dias = cadastros.resumo?.dias_desde_copia;
  if (administra && typeof dias === "number" && dias > 7) {
    avisos.push({
      id: "copia",
      tipo: "copia",
      titulo: `A última cópia de segurança foi há ${dias} dias`,
      detalhe: "Faça uma cópia nova e guarde fora deste computador.",
      href: "/configuracoes/",
      acao: "Fazer cópia agora",
    });
  }
  return avisos;
}

/** "6 momentos para verificar · 1 CNH pede atenção · 1 caixa precisa de atenção". */
function resumo(pendentes: number, avisos: Aviso[]) {
  const partes = [pendentes ? plural(pendentes, "momento para verificar", "momentos para verificar") : "Nenhum momento para verificar"];
  const cnh = avisos.filter((aviso) => aviso.tipo === "cnh").length;
  const caixas = avisos.filter((aviso) => aviso.tipo === "caixa").length;
  if (cnh) partes.push(cnh === 1 ? "1 CNH pede atenção" : `${cnh} CNHs pedem atenção`);
  if (caixas) partes.push(caixas === 1 ? "1 caixa precisa de atenção" : `${caixas} caixas precisam de atenção`);
  return partes.join(" · ");
}

function BarraDeProgresso({ valor, rotulo, className }: { valor: number; rotulo: string; className?: string }) {
  return (
    <div role="progressbar" aria-label={rotulo} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(valor)} className={cn("h-1.5 overflow-hidden rounded-[3px] bg-trilho", className)}>
      <div className="h-full rounded-[3px] bg-verde" style={{ width: `${valor}%` }} />
    </div>
  );
}

function OQueFazerAgora({ tarefas }: { tarefas: Tarefa[] }) {
  return (
    <section aria-labelledby="fazer-agora">
      <h2 id="fazer-agora" className="font-titulo text-[20px] font-semibold">
        O que fazer agora
      </h2>
      <ul className="mt-3 grid grid-cols-2 gap-3">
        {tarefas.map((tarefa) => (
          <li key={tarefa.id} data-tarefa={tarefa.id} className="anim-row flex min-w-0 flex-col rounded-[12px] border border-fio bg-superficie p-4">
            <b className={cn("text-[15.5px] font-semibold leading-snug", tarefa.alarme && "text-alarme")}>{tarefa.titulo}</b>
            <span className="mt-1 flex-1 text-[13.5px] text-grafite">{tarefa.detalhe}</span>
            <Link href={tarefa.href} className={cn("btn btn-small mt-3.5 self-start", tarefa.principal && "btn-primary")}>
              {tarefa.acao}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function CaixaConectada() {
  if (!COLETA) return null;
  const motorista = motoristaDe(COLETA.motorista);
  const feitas = COLETA.etapas.filter((etapa) => etapa.feita).length;

  return (
    <section id="caixa-conectada" aria-labelledby="caixa-titulo" className="scroll-mt-6 rounded-[12px] border border-fio bg-superficie p-4">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="caixa-titulo" className="flex items-center gap-2.5 font-titulo text-[17px] font-semibold">
          <span aria-hidden="true" className="pulse-dot" />
          Caixa do {NOME_DA_COLETA} conectada
        </h2>
        <span className="text-[13.5px] tabular-nums text-grafite">{COLETA.progresso}% lido</span>
      </div>
      <p className="mt-1 text-[13.5px] text-grafite">
        Viagem de {dia(COLETA.saida)} às {hora(COLETA.saida)} até {dia(COLETA.chegada)} às {hora(COLETA.chegada)} · motorista{" "}
        <b className="font-semibold text-tinta">{motorista?.nome ?? "não confirmado"}</b>
      </p>
      <BarraDeProgresso valor={COLETA.progresso} rotulo="Lendo o registro da caixa" className="mt-3" />
      <ol className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[13px]">
        {COLETA.etapas.map((etapa, indice) => (
          <li key={etapa.nome} className={cn("flex items-center gap-1.5", indice === feitas ? "font-semibold text-tinta" : "text-grafite")}>
            {etapa.feita ? <Glyph name="check" size={14} className="text-verde" /> : <span className="tabular-nums">{indice + 1}.</span>}
            {etapa.nome}
          </li>
        ))}
      </ol>
      <p className="mt-3 text-[13px] text-grafite">Fica pronto em cerca de 1 minuto. Enquanto isso, dá para verificar as outras viagens.</p>
    </section>
  );
}

export function HomeScreen() {
  const { usuario, pode } = useSession();
  const { decisions } = useDecisions();
  const { toast } = useToast();
  const [cadastros, setCadastros] = useState<Cadastros | null>(null);
  const [escondidos, setEscondidos] = useState<boolean | null>(null);
  const [verTodos, setVerTodos] = useState(false);
  const usuarioId = usuario?.id ?? null;
  const administra = pode("equipe");

  useEffect(() => {
    if (usuarioId === null) return;
    let vivo = true;
    Promise.all([
      bridge.motoristas_listar(),
      bridge.veiculos_listar(),
      bridge.caixas_listar(),
      bridge.inicio_resumo(),
      administra ? bridge.equipe_listar() : Promise.resolve(null),
    ]).then(([motoristas, veiculos, caixas, inicio, equipe]) => {
      if (!vivo) return;
      setCadastros({
        motoristas: motoristas.ok ? motoristas.dados : [],
        veiculos: veiculos.ok ? veiculos.dados : [],
        caixas: caixas.ok ? caixas.dados : [],
        resumo: inicio.ok ? inicio.dados : null,
        pessoas: equipe && equipe.ok ? equipe.dados : null,
      });
    });
    return () => {
      vivo = false;
    };
  }, [usuarioId, administra]);

  const paraVerificar = VIAGENS.map(({ viagem, momentos }) => ({ viagem, pendentes: momentos.filter((id) => !decisions[id]).length })).filter(
    (item) => item.pendentes > 0,
  );
  const pendentes = paraVerificar.reduce((soma, item) => soma + item.pendentes, 0);
  const avisos = cadastros ? avisosDe(cadastros, administra, hojeIso()) : [];
  const ativos = cadastros?.motoristas.filter((motorista) => motorista.situacao === "ativo") ?? [];
  const passos = cadastros
    ? primeirosPassos({
        veiculos: cadastros.veiculos.length,
        caixasVinculadas: cadastros.caixas.filter((caixa) => caixa.veiculo_id !== null).length,
        motoristasAtivos: ativos.length,
        motoristasSemTermo: ativos.filter((motorista) => !motorista.termo.assinado).length,
        pessoas: cadastros.pessoas?.length ?? 1,
        ultimaCopiaEm: cadastros.resumo?.ultima_copia_em ?? null,
      })
    : [];
  const verPassos = administra && cadastros !== null && mostrarPrimeirosPassos(passos, escondidos ?? cadastros.resumo?.primeiros_passos_escondidos ?? false);
  const proximo = passos.find((passo) => !passo.feito);
  const feitos = passos.filter((passo) => passo.feito).length;

  const tarefas: Tarefa[] = [];
  const primeira = paraVerificar[0];
  tarefas.push(
    primeira
      ? {
          id: "verificar",
          principal: true,
          titulo: plural(pendentes, "momento para verificar", "momentos para verificar"),
          detalhe: (
            <>
              Comece pelo <b className="font-semibold text-tinta">{nomeDoVeiculo(primeira.viagem.tipo, primeira.viagem.veiculo)}</b>, motorista{" "}
              {motoristaDe(primeira.viagem.motorista)?.nome ?? "não confirmado"}, que chegou {dia(primeira.viagem.chegada)} às {hora(primeira.viagem.chegada)}.
            </>
          ),
          href: `/viagens/${primeira.viagem.id}/`,
          acao: "Verificar agora",
        }
      : { id: "verificar", titulo: "Tudo verificado", detalhe: "As viagens novas aparecem aqui quando a caixa for lida.", href: "/viagens/", acao: "Ver viagens" },
  );
  if (verPassos && proximo) {
    tarefas.push({
      id: "instalacao",
      titulo: proximo.titulo,
      detalhe: `Próximo passo para a instalação ficar pronta: ${feitos} de ${passos.length} feitos.`,
      href: proximo.href,
      acao: proximo.acao,
    });
  }
  if (avisos[0]) {
    tarefas.push({
      id: "aviso",
      alarme: true,
      titulo: avisos[0].titulo,
      detalhe: avisos.length > 1 ? `${avisos[0].detalhe} Mais ${plural(avisos.length - 1, "aviso", "avisos")} logo abaixo.` : avisos[0].detalhe,
      href: avisos[0].href,
      acao: avisos[0].acao,
    });
  }
  if (COLETA) {
    tarefas.push({
      id: "caixa",
      titulo: `Caixa do ${NOME_DA_COLETA} conectada`,
      detalhe: `Lendo o registro: ${COLETA.progresso}%. Fica pronto em cerca de 1 minuto.`,
      href: "#caixa-conectada",
      acao: "Acompanhar a leitura",
    });
  }

  async function esconderPassos(esconder: boolean) {
    const resposta = await bridge.primeiros_passos_esconder(esconder);
    if (!resposta.ok) return toast({ text: resposta.erro });
    setEscondidos(resposta.dados.primeiros_passos_escondidos);
    if (esconder) toast({ text: "Primeiros passos escondidos", action: { label: "Desfazer", onClick: () => void esconderPassos(false) } });
  }

  return (
    <section className="max-w-[900px] px-14 pb-16 pt-[34px]">
      <PageHeader title="Início" summary={resumo(pendentes, avisos)} guide={{ capitulo: "primeiros-passos" }} />

      <div className="flex flex-col gap-8">
        <OQueFazerAgora tarefas={tarefas} />

        {verPassos && (
          <section aria-labelledby="primeiros-passos" className="rounded-[12px] border border-fio bg-superficie px-4 py-3">
            <div className="flex items-center gap-4">
              <h2 id="primeiros-passos" className="shrink-0 text-[14.5px] font-semibold">
                Primeiros passos
              </h2>
              <span className="shrink-0 text-[13.5px] tabular-nums text-grafite">
                {feitos} de {passos.length} feitos
              </span>
              <BarraDeProgresso valor={(feitos / passos.length) * 100} rotulo="Primeiros passos feitos" className="min-w-[60px] flex-1" />
              <button type="button" aria-expanded={verTodos} onClick={() => setVerTodos(!verTodos)} className="shrink-0 text-[13px] font-semibold text-verde hover:underline">
                {verTodos ? "Fechar a lista" : "Ver todos"}
              </button>
              <button type="button" onClick={() => void esconderPassos(true)} className="shrink-0 text-[13px] font-semibold text-grafite hover:text-tinta">
                Esconder
              </button>
            </div>
            {verTodos && (
              <ol className="mt-3 border-t border-fio">
                {passos.map((passo, indice) => {
                  const agora = passo.id === proximo?.id;
                  return (
                    <li key={passo.id} className="flex h-12 items-center gap-3.5 border-b border-fio last:border-b-0">
                      <span
                        className={cn(
                          "grid size-6 shrink-0 place-items-center rounded-full border text-[12px] font-bold",
                          passo.feito ? "border-verde-cheio bg-verde-cheio text-sobre-verde" : agora ? "border-verde text-verde" : "border-fio text-grafite",
                        )}
                      >
                        {passo.feito ? <Glyph name="check" size={14} stroke={2.2} /> : indice + 1}
                      </span>
                      <span className={cn("min-w-0 flex-1 truncate text-[14.5px]", passo.feito ? "text-grafite" : agora && "font-semibold")}>{passo.titulo}</span>
                      {agora && (
                        <Link href={passo.href} className="btn btn-small btn-primary shrink-0">
                          {passo.acao}
                        </Link>
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
          </section>
        )}

        <section aria-labelledby="para-verificar">
          <div className="flex items-baseline justify-between gap-4">
            <h2 id="para-verificar" className="font-titulo text-[20px] font-semibold">
              Para verificar
            </h2>
            <Link href="/viagens/" className="text-[13px] font-semibold text-verde hover:underline">
              Ver todas as viagens
            </Link>
          </div>
          {paraVerificar.length === 0 ? (
            <p className="mt-2 text-[14.5px] text-grafite">Tudo verificado. As viagens novas aparecem aqui quando a caixa for lida.</p>
          ) : (
            <ul className="mt-3 border-t border-fio">
              {paraVerificar.map(({ viagem, pendentes: faltam }) => (
                <li key={viagem.id}>
                  <Link
                    href={`/viagens/${viagem.id}/`}
                    className="grid h-14 grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-5 border-b border-fio px-2 transition-colors hover:bg-lateral"
                  >
                    <span className="min-w-0">
                      <b className="block truncate text-[15px] font-semibold">{nomeDoVeiculo(viagem.tipo, viagem.veiculo)}</b>
                      <span className="block truncate text-[13px] text-grafite">
                        Motorista <b className="font-semibold text-tinta">{motoristaDe(viagem.motorista)?.nome ?? "não confirmado"}</b> · {viagem.linha}
                      </span>
                    </span>
                    <span className="text-[13px] tabular-nums text-grafite">
                      Chegou {dia(viagem.chegada)} às {hora(viagem.chegada)}
                    </span>
                    <span className="rounded-[7px] bg-lima px-2 py-[3px] text-[12.5px] font-bold tabular-nums text-sobre-lima">{faltam} para ver</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <CaixaConectada />

        {avisos.length > 0 && (
          <section aria-labelledby="avisos">
            <h2 id="avisos" className="font-titulo text-[20px] font-semibold">
              Avisos
            </h2>
            <ul className="mt-3 border-t border-fio">
              {avisos.map((aviso) => (
                <li key={aviso.id} className="anim-row flex items-center gap-5 border-b border-fio px-2 py-3">
                  <span className="min-w-0 flex-1">
                    <b className="block text-[14.5px] font-semibold text-alarme">{aviso.titulo}</b>
                    {aviso.detalhe && <span className="block text-[13px] text-grafite">{aviso.detalhe}</span>}
                  </span>
                  <Link href={aviso.href} className="btn btn-small shrink-0">
                    {aviso.acao}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        <LiveScriptCard />
      </div>
    </section>
  );
}
