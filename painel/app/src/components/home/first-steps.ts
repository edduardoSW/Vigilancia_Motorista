// Primeiros passos do Início (spec 017, decisão 6): o que falta para a instalação ficar pronta, marcado pelo estado real.
// Sem importação: o teste lê este arquivo direto no Node (GUI-07 em scripts/testes/shell.test.mjs).

export interface EstadoInstalacao {
  veiculos: number;
  caixasVinculadas: number;
  motoristasAtivos: number;
  motoristasSemTermo: number;
  /** Pessoas com acesso ao painel, contando quem administra. */
  pessoas: number;
  ultimaCopiaEm: string | null;
}

export interface PassoInicial {
  id: "veiculos" | "caixas" | "motoristas" | "termos" | "equipe" | "copia";
  titulo: string;
  feito: boolean;
  href: string;
  acao: string;
}

export function primeirosPassos(estado: EstadoInstalacao): PassoInicial[] {
  return [
    { id: "veiculos", titulo: "Cadastre os veículos da empresa", feito: estado.veiculos > 0, href: "/veiculos/", acao: "Cadastrar veículos" },
    { id: "caixas", titulo: "Escolha a caixa instalada em cada veículo", feito: estado.caixasVinculadas > 0, href: "/veiculos/", acao: "Escolher caixas" },
    { id: "motoristas", titulo: "Cadastre os motoristas com a CNH", feito: estado.motoristasAtivos > 0, href: "/motoristas/", acao: "Cadastrar motoristas" },
    {
      id: "termos",
      titulo: "Registre o termo de ciência de cada motorista",
      feito: estado.motoristasAtivos > 0 && estado.motoristasSemTermo === 0,
      href: "/motoristas/",
      acao: "Registrar termos",
    },
    { id: "equipe", titulo: "Adicione quem vai usar o painel", feito: estado.pessoas > 1, href: "/equipe/", acao: "Adicionar pessoa" },
    { id: "copia", titulo: "Faça a primeira cópia de segurança", feito: Boolean(estado.ultimaCopiaEm), href: "/configuracoes/", acao: "Fazer cópia" },
  ];
}

/** Some quando tudo estiver feito ou quando o administrador escolhe "Esconder". */
export const mostrarPrimeirosPassos = (passos: PassoInicial[], escondidos: boolean) => !escondidos && passos.some((passo) => !passo.feito);
