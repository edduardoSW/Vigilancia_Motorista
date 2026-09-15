// Opções de tema (spec 019, ESC-01), iguais no pé do menu e em Configurações › Aparência.
// Sem importação de valor: o teste lê este arquivo direto no Node (scripts/testes/shell.test.mjs).
import type { Tema } from "@/lib/bridge";

export const OPCOES_TEMA: { valor: Tema; rotulo: string; icone: "sun" | "moon" | "monitor"; explicacao: string }[] = [
  { valor: "claro", rotulo: "Claro", icone: "sun", explicacao: "Fundo claro, bom para sala iluminada." },
  { valor: "escuro", rotulo: "Escuro", icone: "moon", explicacao: "Fundo escuro, cansa menos a vista à noite." },
  { valor: "sistema", rotulo: "Igual ao Windows", icone: "monitor", explicacao: "Acompanha o tema claro ou escuro do Windows." },
];
