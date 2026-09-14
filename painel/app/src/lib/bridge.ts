// Ponte entre as telas e o Python (contrato do painel, parte 2). Na janela do app usa window.pywebview.api; sem ela
// (build, testes, captura de tela) usa a demonstração em memória, com os mesmos nomes, respostas e permissões.
// A tela só conversa com `bridge`: trocar o transporte (ponte local → servidor) não muda as telas.
// Nada daqui grava sessão, senha ou código no navegador (ENT-07): a sessão vive só no processo do app.
import type { ResultadoMomento } from "@/content/moments";

export type { ResultadoMomento };

export type Funcao = "administrador" | "supervisor" | "consulta";
export type Acao = "ver_viagens" | "ver_video" | "importar" | "decidir" | "cadastrar" | "equipe" | "configuracoes" | "atividades";
export type CodigoErro = "invalido" | "sem_permissao" | "sem_sessao" | "bloqueado" | "espera" | "nao_encontrado" | "conflito";

export type Resposta<T> =
  | { ok: true; dados: T }
  | { ok: false; erro: string; codigo?: CodigoErro; campo?: string; esperar_s?: number };

export type Vazio = Record<string, never>;

export interface Usuario {
  id: number;
  nome: string;
  usuario: string;
  funcao: Funcao;
  ativo: boolean;
  ultimo_acesso: string | null;
  trocar_senha: boolean;
}

export interface Estado {
  ativado: boolean;
  modo: "demonstracao" | "empresa" | null;
  empresa: { nome: string } | null;
  sessao: Usuario | null;
  bloqueado: boolean;
  versao: string;
  bloqueio_min: number;
}

export interface Motorista {
  id: number;
  ref: string | null;
  nome: string;
  nome_curto: string;
  matricula: string;
  cpf: string | null;
  telefone: string | null;
  cnh_numero: string;
  cnh_categoria: "C" | "D" | "E";
  /** AAAA-MM-DD */
  cnh_validade: string;
  situacao: "ativo" | "afastado" | "desligado";
  termo: { assinado: boolean; data: string | null; versao: string | null };
  observacoes: string | null;
  viagens_30d: number;
  confirmados_30d: number;
}

export interface Veiculo {
  id: number;
  numero: string;
  placa: string;
  tipo: "onibus" | "micro_onibus" | "caminhao" | "van";
  transporta: "passageiros" | "carga";
  modelo: string | null;
  ano: number | null;
  situacao: "em_uso" | "oficina" | "fora_de_uso";
  caixa_id: number | null;
}

export interface Caixa {
  id: number;
  codigo: string;
  veiculo_id: number | null;
  situacao: "ok" | "atencao" | "bloqueada";
  detalhe: string | null;
  ultima_coleta: string | null;
  versao: string | null;
}

export interface Atividade {
  id: number;
  em: string;
  usuario: string | null;
  acao: string;
  alvo: string | null;
  detalhe: string | null;
}

export interface Configuracoes {
  empresa: { nome: string; razao_social: string; cnpj: string; telefone: string; endereco: string };
  /** direcao_continua_min de 60 a 330 */
  regras: { direcao_continua_min: number };
  guarda: { videos_dias: 7 | 15 | 30 | 60 | 90; registros_anos: 1 | 2 | 5; desligados_anos: 1 | 2 | 5 };
  /** bloqueio_min de 5 a 60 */
  acesso: { bloqueio_min: number };
  aparencia: { texto_maior: boolean };
}

export interface Decisao {
  momento_id: string;
  resultado: ResultadoMomento;
  orientado: boolean;
  por: string;
  funcao: Funcao;
  em: string;
}

export interface ScriptEstado {
  aberto: boolean;
  programa: string | null;
  desde: string | null;
  pid: number | null;
  camera: string | null;
  ultimo_sinal: string | null;
  eventos: number;
  pasta: string | null;
}

export interface EventoScript {
  id: number;
  em: string;
  tipo: string;
  risco: number;
  duracao_s: number | null;
  sessao: string | null;
}

export interface NovoAdministrador {
  nome: string;
  usuario: string;
  senha: string;
}

export interface NovaPessoa {
  nome: string;
  usuario: string;
  funcao: Funcao;
}

export interface FiltroAtividades {
  usuario_id?: number;
  de?: string;
  ate?: string;
  limite?: number;
}

/** Sem `id` cria; com `id` altera. O Python confere cada campo e devolve `campo` quando algo não confere. */
export type MotoristaDados = Partial<Omit<Motorista, "viagens_30d" | "confirmados_30d">>;
export type VeiculoDados = Partial<Veiculo>;

export interface Api {
  estado(): Promise<Resposta<Estado>>;
  ativar_demonstracao(admin: NovoAdministrador): Promise<Resposta<{ codigo_recuperacao: string }>>;
  ativar_com_arquivo(conteudo: string, admin: NovoAdministrador): Promise<Resposta<{ codigo_recuperacao: string }>>;
  entrar(usuario: string, senha: string): Promise<Resposta<Usuario>>;
  sair(): Promise<Resposta<Vazio>>;
  bloquear(): Promise<Resposta<Vazio>>;
  tocar(): Promise<Resposta<{ bloqueado: boolean }>>;
  desbloquear(senha: string): Promise<Resposta<Usuario>>;
  trocar_senha(atual: string, nova: string): Promise<Resposta<Vazio>>;
  recuperar_acesso(usuario: string, codigo: string, nova_senha: string): Promise<Resposta<Vazio>>;
  equipe_listar(): Promise<Resposta<Usuario[]>>;
  equipe_adicionar(pessoa: NovaPessoa): Promise<Resposta<{ usuario: Usuario; senha_temporaria: string }>>;
  equipe_alterar(id: number, mudancas: { funcao?: Funcao; ativo?: boolean }): Promise<Resposta<Usuario>>;
  equipe_nova_senha(id: number): Promise<Resposta<{ senha_temporaria: string }>>;
  atividades_listar(filtro?: FiltroAtividades): Promise<Resposta<{ itens: Atividade[]; integro: boolean }>>;
  atividades_exportar(): Promise<Resposta<{ caminho: string }>>;
  motoristas_listar(): Promise<Resposta<Motorista[]>>;
  motorista_salvar(dados: MotoristaDados): Promise<Resposta<Motorista>>;
  motorista_exportar(id: number): Promise<Resposta<{ caminho: string }>>;
  veiculos_listar(): Promise<Resposta<Veiculo[]>>;
  caixas_listar(): Promise<Resposta<Caixa[]>>;
  veiculo_salvar(dados: VeiculoDados): Promise<Resposta<Veiculo>>;
  caixa_vincular(caixa_id: number, veiculo_id: number | null): Promise<Resposta<Caixa>>;
  config_ler(): Promise<Resposta<Configuracoes>>;
  config_salvar<S extends keyof Configuracoes>(secao: S, valores: Partial<Configuracoes[S]>): Promise<Resposta<Configuracoes>>;
  decisoes_listar(): Promise<Resposta<Decisao[]>>;
  decisao_registrar(momento_id: string, resultado: ResultadoMomento): Promise<Resposta<Decisao>>;
  decisao_desfazer(momento_id: string): Promise<Resposta<Vazio>>;
  decisao_orientado(momento_id: string, orientado: boolean): Promise<Resposta<Decisao>>;
  video_abrir(momento_id: string, motorista_ref: string): Promise<Resposta<{ liberado: boolean; motivo?: string }>>;
  copia_fazer(senha: string): Promise<Resposta<{ caminho: string; bytes: number }>>;
  script_estado(): Promise<Resposta<ScriptEstado>>;
  script_eventos(desde_id: number): Promise<Resposta<EventoScript[]>>;
}

// Permissões da spec 014, decisão 3. O Python confere de novo em cada chamada; aqui serve só para esconder o que não cabe.
export const PERMISSOES: Record<Funcao, readonly Acao[]> = {
  administrador: ["ver_viagens", "ver_video", "importar", "decidir", "cadastrar", "equipe", "configuracoes", "atividades"],
  supervisor: ["ver_viagens", "ver_video", "importar", "decidir", "cadastrar"],
  consulta: ["ver_viagens"],
};

export const podeFazer = (funcao: Funcao | null | undefined, acao: Acao) => Boolean(funcao && PERMISSOES[funcao].includes(acao));

export const NOME_FUNCAO: Record<Funcao, string> = { administrador: "Administrador", supervisor: "Supervisor", consulta: "Consulta" };

/** Regra de senha da spec 014 (decisão 4). */
export const SENHA_MINIMA = 10;

const NOMES = [
  "estado",
  "ativar_demonstracao",
  "ativar_com_arquivo",
  "entrar",
  "sair",
  "bloquear",
  "tocar",
  "desbloquear",
  "trocar_senha",
  "recuperar_acesso",
  "equipe_listar",
  "equipe_adicionar",
  "equipe_alterar",
  "equipe_nova_senha",
  "atividades_listar",
  "atividades_exportar",
  "motoristas_listar",
  "motorista_salvar",
  "motorista_exportar",
  "veiculos_listar",
  "caixas_listar",
  "veiculo_salvar",
  "caixa_vincular",
  "config_ler",
  "config_salvar",
  "decisoes_listar",
  "decisao_registrar",
  "decisao_desfazer",
  "decisao_orientado",
  "video_abrir",
  "copia_fazer",
  "script_estado",
  "script_eventos",
] as const satisfies readonly (keyof Api)[];

// Falha na compilação se algum método do contrato ficar de fora da lista acima.
type Faltando = Exclude<keyof Api, (typeof NOMES)[number]>;
export const CONTRATO_COMPLETO: [Faltando] extends [never] ? true : never = true;

type Metodo = (...args: unknown[]) => Promise<unknown>;
type Transporte = Record<string, Metodo | undefined>;

/** Tempo máximo esperando a janela do app avisar que a ponte está pronta. */
const ESPERA_JANELA_MS = 4000;

let transporte: Promise<Transporte> | null = null;
let origem: "janela" | "demonstracao" | null = null;

function apiDaJanela(): Transporte | undefined {
  if (typeof window === "undefined") return undefined;
  const api = (window as unknown as { pywebview?: { api?: Transporte } }).pywebview?.api;
  return api && typeof api.estado === "function" ? api : undefined;
}

async function demonstracao(): Promise<Transporte> {
  const { demoBackend } = await import("./demo-backend");
  origem = "demonstracao";
  return demoBackend as unknown as Transporte;
}

function escolherTransporte(): Promise<Transporte> {
  if (transporte) return transporte;
  transporte = new Promise<Transporte>((resolve) => {
    const pronta = apiDaJanela();
    if (pronta) {
      origem = "janela";
      resolve(pronta);
      return;
    }
    // Fora do navegador (build) ou pedindo a demonstração direto (captura de tela): não espera a janela.
    if (typeof window === "undefined" || /[?&](demo|sessao)=/.test(window.location.search)) {
      resolve(demonstracao());
      return;
    }
    let decidido = false;
    const decidir = () => {
      if (decidido) return;
      decidido = true;
      window.removeEventListener("pywebviewready", decidir);
      const api = apiDaJanela();
      if (api) {
        origem = "janela";
        resolve(api);
      } else {
        resolve(demonstracao());
      }
    };
    window.addEventListener("pywebviewready", decidir);
    window.setTimeout(decidir, ESPERA_JANELA_MS);
  });
  return transporte;
}

async function chamar(nome: keyof Api, args: unknown[]): Promise<Resposta<unknown>> {
  try {
    const alvo = await escolherTransporte();
    const metodo = alvo[nome];
    if (typeof metodo !== "function") return { ok: false, erro: "Esta função ainda não existe nesta versão do painel." };
    const resposta = await metodo.apply(alvo, args);
    if (resposta && typeof resposta === "object" && "ok" in resposta) return resposta as Resposta<unknown>;
    return { ok: false, erro: "O painel respondeu de um jeito inesperado. Tente de novo." };
  } catch {
    return { ok: false, erro: "Não foi possível falar com o painel. Tente de novo." };
  }
}

export const bridge = Object.fromEntries(NOMES.map((nome) => [nome, (...args: unknown[]) => chamar(nome, args)])) as unknown as Api;

/** De onde vêm as respostas: a janela do app (Python) ou a demonstração em memória. */
export async function origemDaPonte(): Promise<"janela" | "demonstracao"> {
  await escolherTransporte();
  return origem ?? "demonstracao";
}
