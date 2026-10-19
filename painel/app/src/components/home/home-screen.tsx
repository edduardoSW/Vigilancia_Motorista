"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { plural } from "@/components/drivers/use-list-shortcuts";
import { mostrarPrimeirosPassos, primeirosPassos } from "@/components/home/first-steps";
import { numerosDoInicio, resumoDoInicio, tarefasDoInicio, type NumeroDoInicio, type TarefaDoInicio } from "@/components/home/inicio-numeros";
import { LiveScriptCard } from "@/components/live/live-script-card";
import { resumoDosEventos, type TiposDeEvento } from "@/components/live/summary";
import { useSession } from "@/components/session-provider";
import { Glyph } from "@/components/ui/glyph";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { nomeDoVeiculo as nomeNaFrota } from "@/components/vehicles/vehicle-labels";
import tiposDeEvento from "@/content/tipos-de-evento.json";
import { bridge, type Caixa, type InicioResumo, type Motorista, type Usuario, type Veiculo } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { diasAte, formatarData, hojeIso, situacaoCnh } from "@/lib/validators";

// Início (spec 014; spec 019, INT-02; spec 030): começa por "O que fazer agora", um card por tarefa, cada um com o seu
// botão. Depois os números de hoje (testes, alertas, quem está testando e os cadastros), os Primeiros passos numa barra,
// os avisos (CNH, caixa, cópia) e o teste neste computador. Tudo vem da ponte: zero quando não há, nada inventado.

const TIPOS = tiposDeEvento as TiposDeEvento;
/** Relê os números enquanto o Início está aberto (a central chega a cada 30 s; o script local a cada 2 s). */
const ATUALIZAR_MS = 15_000;

interface Cadastros {
  motoristas: Motorista[];
  veiculos: Veiculo[];
  caixas: Caixa[];
  pessoas: Usuario[] | null;
}

interface Aviso {
  id: string;
  tipo: "cnh" | "caixa" | "copia";
  titulo: string;
  detalhe: string;
  href: string;
  acao: string;
}

function avisosDe(cadastros: Cadastros, resumo: InicioResumo | null, administra: boolean, hoje: string): Aviso[] {
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
  const dias = resumo?.dias_desde_copia;
  if (administra && typeof dias === "number" && dias > 7) {
    avisos.push({
      id: "copia",
      tipo: "copia",
      titulo: `A última cópia de segurança foi há ${dias} dias`,
      detalhe: "Faça uma cópia nova e guarde fora deste computador.",
      href: "/configuracoes/?secao=copia",
      acao: "Fazer cópia agora",
    });
  }
  return avisos;
}

/** "2 de sono e 1 de celular", a partir da contagem de alertas por tipo. */
function detalheDosAlertas(porTipo: Record<string, number>) {
  const eventos = Object.entries(porTipo).flatMap(([tipo, quantidade]) => Array.from({ length: quantidade }, () => ({ tipo })));
  return eventos.length ? resumoDosEventos(eventos, TIPOS) : undefined;
}

function BarraDeProgresso({ valor, rotulo, className }: { valor: number; rotulo: string; className?: string }) {
  return (
    <div role="progressbar" aria-label={rotulo} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(valor)} className={cn("h-1.5 overflow-hidden rounded-[3px] bg-trilho", className)}>
      <div className="h-full rounded-[3px] bg-verde" style={{ width: `${valor}%` }} />
    </div>
  );
}

function OQueFazerAgora({ tarefas }: { tarefas: TarefaDoInicio[] }) {
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

// Números de hoje (spec 030, SDF-05): rótulo, valor e uma linha de detalhe; cada um leva à tela de onde veio.
function NumerosDeHoje({ numeros }: { numeros: NumeroDoInicio[] }) {
  return (
    <section aria-labelledby="numeros-de-hoje">
      <h2 id="numeros-de-hoje" className="font-titulo text-[20px] font-semibold">
        Hoje
      </h2>
      <ul className="mt-3 grid grid-cols-3 gap-px overflow-hidden rounded-[12px] border border-fio bg-fio">
        {numeros.map((numero) => (
          <li key={numero.id} data-numero={numero.id} className="min-w-0 bg-superficie">
            <Link href={numero.href} className="flex h-full flex-col px-4 py-3.5 transition-colors hover:bg-lateral">
              <span className="text-[13px] text-grafite">{numero.rotulo}</span>
              <span className={cn("mt-0.5 text-[28px] font-semibold leading-tight", numero.alarme ? "text-alarme" : "text-tinta")}>
                {numero.valor === null ? <span className="text-apagado">…</span> : numero.valor.toLocaleString("pt-BR")}
              </span>
              <span className="mt-0.5 truncate text-[12.5px] text-grafite">{numero.detalhe}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function HomeScreen() {
  const { estado, usuario, pode } = useSession();
  const { toast } = useToast();
  const [cadastros, setCadastros] = useState<Cadastros | null>(null);
  const [resumo, setResumo] = useState<InicioResumo | null>(null);
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
      administra ? bridge.equipe_listar() : Promise.resolve(null),
    ]).then(([motoristas, veiculos, caixas, equipe]) => {
      if (!vivo) return;
      setCadastros({
        motoristas: motoristas.ok ? motoristas.dados : [],
        veiculos: veiculos.ok ? veiculos.dados : [],
        caixas: caixas.ok ? caixas.dados : [],
        pessoas: equipe && equipe.ok ? equipe.dados : null,
      });
    });
    const lerResumo = () =>
      bridge.inicio_resumo().then((resposta) => {
        if (vivo && resposta.ok) setResumo(resposta.dados);
      });
    void lerResumo();
    const vigia = window.setInterval(() => void lerResumo(), ATUALIZAR_MS);
    return () => {
      vivo = false;
      window.clearInterval(vigia);
    };
  }, [usuarioId, administra]);

  const hoje = hojeIso();
  const avisos = cadastros ? avisosDe(cadastros, resumo, administra, hoje) : [];
  const ativos = cadastros?.motoristas.filter((motorista) => motorista.situacao === "ativo") ?? [];
  const numeros = numerosDoInicio({
    hoje: resumo?.hoje ?? null,
    motoristasAtivos: cadastros ? ativos.length : null,
    veiculosEmUso: cadastros ? cadastros.veiculos.filter((veiculo) => veiculo.situacao === "em_uso").length : null,
    cnhPedemAtencao: cadastros ? ativos.filter((motorista) => situacaoCnh(motorista.cnh_validade, hoje) !== "ok").length : null,
    detalheDosAlertas: resumo ? detalheDosAlertas(resumo.hoje.alertas_por_tipo) : undefined,
  });
  const passos = cadastros
    ? primeirosPassos({
        veiculos: cadastros.veiculos.length,
        caixasVinculadas: cadastros.caixas.filter((caixa) => caixa.veiculo_id !== null).length,
        motoristasAtivos: ativos.length,
        motoristasSemTermo: ativos.filter((motorista) => !motorista.termo.assinado).length,
        pessoas: cadastros.pessoas?.length ?? 1,
        ultimaCopiaEm: resumo?.ultima_copia_em ?? null,
      })
    : [];
  const verPassos = administra && cadastros !== null && resumo !== null && mostrarPrimeirosPassos(passos, escondidos ?? resumo.primeiros_passos_escondidos);
  const proximo = passos.find((passo) => !passo.feito);
  const feitos = passos.filter((passo) => passo.feito).length;

  const tarefas: TarefaDoInicio[] = resumo ? tarefasDoInicio({ hoje: resumo.hoje, administra, empresaSemNome: !estado?.empresa?.nome }) : [];
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

  async function esconderPassos(esconder: boolean) {
    const resposta = await bridge.primeiros_passos_esconder(esconder);
    if (!resposta.ok) return toast({ text: resposta.erro });
    setEscondidos(resposta.dados.primeiros_passos_escondidos);
    if (esconder) toast({ text: "Primeiros passos escondidos", action: { label: "Desfazer", onClick: () => void esconderPassos(false) } });
  }

  return (
    <section className="max-w-[900px] px-14 pb-16 pt-[34px]">
      <PageHeader title="Início" summary={resumoDoInicio(resumo?.hoje ?? null)} guide={{ capitulo: "primeiros-passos" }} />

      <div className="flex flex-col gap-8">
        {tarefas.length > 0 && <OQueFazerAgora tarefas={tarefas} />}

        <NumerosDeHoje numeros={numeros} />

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
