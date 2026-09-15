// O que cada função vê num momento (spec 014, decisão 3; EQP-02): a Consulta vê o momento, sem vídeo e sem decidir.
// A tela só esconde; o Python confere a permissão de novo em cada chamada da ponte.
import type { Acao } from "@/lib/bridge";

export const acoesDoMomento = (pode: (acao: Acao) => boolean) => ({ video: pode("ver_video"), decidir: pode("decidir") });
