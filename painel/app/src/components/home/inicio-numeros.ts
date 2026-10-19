// Números e tarefas do Início (spec 030, SDF-05): só o que a ponte devolveu de verdade, zero quando não há e nada
// enquanto carrega. Só importa tipos: o teste lê este arquivo direto no Node (scripts/testes/sem-dados-ficticios.test.mjs).
import type { ResumoDeHoje } from "@/lib/bridge";

export interface EntradaDoInicio {
  /** null enquanto a ponte não respondeu. */
  hoje: ResumoDeHoje | null;
  motoristasAtivos: number | null;
  veiculosEmUso: number | null;
  /** CNH vencida ou que vence em até 30 dias, de motorista ativo. */
  cnhPedemAtencao: number | null;
  /** "2 de sono e 1 de celular", montado pela tela com os tipos de evento. */
  detalheDosAlertas?: string;
}

export interface NumeroDoInicio {
  id: "testes" | "alertas" | "testando" | "motoristas" | "veiculos" | "cnh";
  rotulo: string;
  /** null: ainda carregando (a tela mostra um traço, nunca um número inventado). */
  valor: number | null;
  detalhe: string;
  href: string;
  alarme: boolean;
}

export interface TarefaDoInicio {
  id: string;
  titulo: string;
  detalhe: string;
  href: string;
  acao: string;
  principal?: boolean;
  alarme?: boolean;
}

const plural = (quantidade: number, um: string, varios: string) => `${quantidade} ${quantidade === 1 ? um : varios}`;

/** Onde ver os testes de hoje: na central (outros computadores) ou neste computador. */
const telaDosTestes = (hoje: ResumoDeHoje) => (hoje.testes_central > 0 || (hoje.testando_agora > Number(hoje.script_aberto)) ? "/remotos/" : "/ao-vivo/");

export function numerosDoInicio({ hoje, motoristasAtivos, veiculosEmUso, cnhPedemAtencao, detalheDosAlertas }: EntradaDoInicio): NumeroDoInicio[] {
  const testando = hoje?.testando_agora ?? null;
  return [
    {
      id: "testes",
      rotulo: "Testes hoje",
      valor: hoje?.testes ?? null,
      detalhe: hoje ? `${hoje.testes_central} à distância e ${hoje.testes_locais} neste computador` : "",
      href: hoje ? telaDosTestes(hoje) : "/remotos/",
      alarme: false,
    },
    {
      id: "alertas",
      rotulo: "Alertas hoje",
      valor: hoje?.alertas ?? null,
      detalhe: !hoje ? "" : hoje.alertas ? (detalheDosAlertas ?? "risco médio ou alto") : "nenhum de risco médio ou alto",
      href: hoje ? telaDosTestes(hoje) : "/remotos/",
      alarme: Boolean(hoje?.alertas),
    },
    {
      id: "testando",
      rotulo: "Testando agora",
      valor: testando,
      detalhe: !hoje
        ? ""
        : hoje.script_aberto
          ? hoje.testando_agora > 1
            ? "este computador e outros pela central"
            : "este computador"
          : `${plural(hoje.computadores, "computador ligado", "computadores ligados")} à central`,
      href: hoje && hoje.script_aberto && hoje.testando_agora === 1 ? "/ao-vivo/" : "/remotos/",
      alarme: false,
    },
    { id: "motoristas", rotulo: "Motoristas", valor: motoristasAtivos, detalhe: "ativos no cadastro", href: "/motoristas/", alarme: false },
    { id: "veiculos", rotulo: "Veículos", valor: veiculosEmUso, detalhe: "em uso no cadastro", href: "/veiculos/", alarme: false },
    {
      id: "cnh",
      rotulo: "CNH vencendo",
      valor: cnhPedemAtencao,
      detalhe: cnhPedemAtencao ? "vencida ou vence em até 30 dias" : "nenhuma nos próximos 30 dias",
      href: "/motoristas/",
      alarme: Boolean(cnhPedemAtencao),
    },
  ];
}

/** Linha de baixo do título do Início: "3 testes hoje · 5 alertas · 1 computador testando agora". */
export function resumoDoInicio(hoje: ResumoDeHoje | null): string {
  if (!hoje) return "Carregando…";
  if (!hoje.testes && !hoje.testando_agora && !hoje.alertas) return "Nenhum teste hoje";
  const partes = [hoje.testes ? `${plural(hoje.testes, "teste", "testes")} hoje` : "Nenhum teste hoje"];
  if (hoje.alertas) partes.push(plural(hoje.alertas, "alerta", "alertas"));
  if (hoje.testando_agora) partes.push(`${plural(hoje.testando_agora, "computador", "computadores")} testando agora`);
  return partes.join(" · ");
}

/** "O que fazer agora" com os testes de hoje e a empresa sem nome; os avisos de cadastro a tela junta depois. */
export function tarefasDoInicio({ hoje, administra, empresaSemNome }: { hoje: ResumoDeHoje; administra: boolean; empresaSemNome: boolean }): TarefaDoInicio[] {
  const tarefas: TarefaDoInicio[] = [];
  const tela = telaDosTestes(hoje);
  if (hoje.testando_agora) {
    tarefas.push({
      id: "testando",
      principal: true,
      titulo: `${plural(hoje.testando_agora, "computador testando", "computadores testando")} agora`,
      detalhe: hoje.script_aberto && hoje.testando_agora === 1 ? "O RotaGuard Script está aberto neste computador." : "Os eventos chegam da central a cada 30 segundos.",
      href: hoje.script_aberto && hoje.testando_agora === 1 ? "/ao-vivo/" : "/remotos/",
      acao: "Acompanhar",
    });
  }
  if (hoje.alertas) {
    tarefas.push({
      id: "alertas",
      alarme: true,
      titulo: `${plural(hoje.alertas, "alerta", "alertas")} nos testes de hoje`,
      detalhe: "Abra a sessão para ver quando aconteceu e o trecho gravado.",
      href: tela,
      acao: "Ver os testes",
    });
  }
  if (administra && empresaSemNome) {
    tarefas.push({
      id: "empresa",
      titulo: "Escreva o nome da empresa",
      detalhe: "Ele aparece no menu, na tela de entrar e nos relatórios.",
      href: "/configuracoes/?secao=empresa",
      acao: "Abrir Configurações",
    });
  }
  if (!hoje.testes && !hoje.testando_agora) {
    tarefas.push({
      id: "testar",
      principal: tarefas.length === 0,
      titulo: "Nenhum teste hoje",
      detalhe: "Abra o RotaGuard Script neste computador: o teste aparece no painel sozinho.",
      href: "/ao-vivo/",
      acao: "Ver Teste neste computador",
    });
    if (administra && !hoje.central_conectada) {
      tarefas.push({
        id: "central",
        titulo: "Receba os testes de outros computadores",
        detalhe: "Conecte o painel à central e gere um código para cada computador com o RotaGuard Script.",
        href: "/configuracoes/?secao=central",
        acao: "Conectar à central",
      });
    }
  }
  return tarefas;
}
