// Estados vazios das telas (spec 030, SDF-04): o que ainda não existe e o próximo passo, sem nenhum dado inventado.
// Só importa tipos: o teste lê este arquivo direto no Node (scripts/testes/sem-dados-ficticios.test.mjs).
import type { Acao } from "@/lib/bridge";

export interface EstadoVazio {
  titulo: string;
  texto: string;
  /** Próximo passo. Com `href` vira link; sem ele, a tela liga o botão. Some para quem não tem a ação `precisa`. */
  acao?: { rotulo: string; href?: string; precisa?: Acao };
}

export const VAZIO = {
  viagens: {
    titulo: "Nenhuma viagem ainda.",
    texto:
      "As viagens aparecem quando uma caixa for conectada a este computador. Enquanto isso, os testes feitos com o RotaGuard Script aparecem em Testes à distância e em Teste neste computador.",
    acao: { rotulo: "Ver os testes à distância", href: "/remotos/" },
  },
  relatorio: {
    titulo: "Viagem não encontrada.",
    texto: "Esta viagem não está neste computador. As viagens aparecem quando a caixa for lida aqui.",
    acao: { rotulo: "Voltar para Viagens", href: "/viagens/" },
  },
  motoristas: {
    titulo: "Nenhum motorista cadastrado ainda.",
    texto: "Cadastre cada motorista com a CNH e registre o termo de ciência. Sem o termo, os vídeos dele ficam trancados.",
    acao: { rotulo: "Cadastrar motorista", precisa: "cadastrar" },
  },
  veiculos: {
    titulo: "Nenhum veículo cadastrado ainda.",
    texto: "Cadastre os veículos da frota com o número e a placa. Depois, escolha a caixa instalada em cada um.",
    acao: { rotulo: "Cadastrar veículo", precisa: "cadastrar" },
  },
  caixas: {
    titulo: "Nenhuma caixa neste painel.",
    texto: "As caixas chegam no arquivo da empresa que a RotaGuard entrega. Com o arquivo, cada caixa aparece aqui para ser ligada a um veículo.",
  },
} satisfies Record<string, EstadoVazio>;
