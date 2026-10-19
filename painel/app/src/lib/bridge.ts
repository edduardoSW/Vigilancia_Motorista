// Ponte entre as telas e o Python (contrato do painel, parte 2). Na janela do app usa window.pywebview.api; sem ela
// (build, navegador comum) usa o transporte vazio: nenhum dado, e toda chamada diz que o painel abre pelo app.
// Spec 030: o app não leva dado de exemplo nem a versão em memória da ponte; ela mora só nos testes da tela
// (scripts/testes/fixtures). As capturas de tela usam a Ponte de verdade (scripts/servir-com-ponte.py).
// A tela só conversa com `bridge`: trocar o transporte (ponte local → servidor) não muda as telas.
// Spec 024: o build web (NEXT_PUBLIC_PAINEL_TRANSPORTE=servidor) usa um terceiro transporte, o servidor do painel na
// VPS (painel/web/servidor_web.py). O build do app instalado não tem a variável e continua janela → transporte vazio.
// Nada daqui grava sessão, senha ou código no navegador (ENT-07): a sessão vive só no processo do app (na web, num
// cookie HttpOnly que o JavaScript não lê).
import type { ResultadoMomento } from "@/content/moments";

export type { ResultadoMomento };

/** Painel no navegador (spec 024). Lido no build; o app instalado é construído sem a variável. */
export const PAINEL_NA_WEB = process.env.NEXT_PUBLIC_PAINEL_TRANSPORTE === "servidor";
/** basePath do build web (next.config.ts), ex.: "/painel". Vazio no app instalado. */
const BASE_DO_BUILD = process.env.NEXT_PUBLIC_PAINEL_BASE_PATH ?? "";

export type Funcao = "administrador" | "supervisor" | "consulta";
export type Acao = "ver_viagens" | "ver_video" | "importar" | "decidir" | "cadastrar" | "equipe" | "configuracoes" | "atividades";
export type CodigoErro = "invalido" | "sem_permissao" | "sem_sessao" | "bloqueado" | "espera" | "nao_encontrado" | "conflito";

/** Spec 019: tema e visão (lista ou cards) guardados por pessoa, pela ponte (nada no navegador). */
export type Tema = "claro" | "escuro" | "sistema";
export type Visao = "lista" | "cards";
export const TELAS_COM_VISAO = ["viagens", "momentos", "motoristas", "veiculos", "caixas", "equipe"] as const;
export type TelaComVisao = (typeof TELAS_COM_VISAO)[number];

export interface Preferencias {
  tema: Tema;
  visao: Record<TelaComVisao, Visao>;
}

export interface PreferenciasEntrada {
  tema?: Tema;
  visao?: Partial<Record<TelaComVisao, Visao>>;
}

export const PREFERENCIAS_PADRAO: Preferencias = {
  tema: "claro",
  visao: { viagens: "cards", momentos: "cards", motoristas: "cards", veiculos: "cards", caixas: "cards", equipe: "cards" },
};

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
  /** "local": ativado sem o arquivo da empresa (spec 030); "empresa": com o arquivo entregue pela RotaGuard. */
  modo: "local" | "empresa" | null;
  empresa: { nome: string } | null;
  sessao: Usuario | null;
  bloqueado: boolean;
  versao: string;
  bloqueio_min: number;
  /** Aparência de Configurações: vale para todas as pessoas deste computador, inclusive na tela de entrar. */
  texto_maior: boolean;
  /** Tema da pessoa que entrou; sem sessão, o último usado neste computador (spec 019). */
  tema: Tema;
  preferencias: Preferencias | null;
  /** Prazo de guarda dos vídeos, para "fica guardado até" no momento (spec 019, VID-02). */
  videos_dias: number;
}

/** Arquivo do termo assinado importado para o painel (spec 019, decisão 5). */
export interface ArquivoTermo {
  nome: string;
  tipo: "pdf" | "imagem";
  bytes: number;
  importado_em: string;
  importado_por: string;
}

/** Um registro do histórico de termos do motorista (nunca apagado). */
export interface TermoRegistro {
  id: number;
  assinado: boolean;
  data: string | null;
  versao: string | null;
  registrado_por: string | null;
  registrado_em: string;
  arquivo: ArquivoTermo | null;
}

/** Arquivo escolhido na tela, enviado pela ponte. */
export interface ArquivoEnviado {
  nome: string;
  conteudo_base64: string;
}

export type TermoVisto = { tipo: "imagem"; nome: string; conteudo: string } | { tipo: "pdf"; nome: string; aberto: true };

/** Números de hoje no Início (spec 030, SDF-05): tudo lido do que existe; zero quando não há. Dia = dia local. */
export interface ResumoDeHoje {
  /** Sessões de teste começadas hoje: as da central (outros computadores) + as deste computador (script local). */
  testes: number;
  testes_central: number;
  testes_locais: number;
  /** Eventos registrados hoje, de qualquer risco. */
  eventos: number;
  /** Eventos de risco 2 ou mais (médio ou alto) hoje, e quantos de cada tipo. */
  alertas: number;
  alertas_por_tipo: Record<string, number>;
  /** Computadores da central testando agora + este computador, se o script está aberto. */
  testando_agora: number;
  /** Computadores ligados à empresa na central (sem os desligados). */
  computadores: number;
  script_aberto: boolean;
  central_conectada: boolean;
}

/** Início: aviso da cópia de segurança (BKP-03), Primeiros passos (spec 017) e os números de hoje (spec 030). */
export interface InicioResumo {
  ultima_copia_em: string | null;
  dias_desde_copia: number | null;
  primeiros_passos_escondidos: boolean;
  hoje: ResumoDeHoje;
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
  termo: { assinado: boolean; data: string | null; versao: string | null; arquivo: ArquivoTermo | null };
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
  /** Só no painel pela web (spec 024): o script do computador não existe no servidor; frase para a tela. */
  indisponivel?: string;
}

export interface EventoScript {
  id: number;
  em: string;
  tipo: string;
  risco: number;
  duracao_s: number | null;
  sessao: string | null;
}

// Spec 026 · central na VPS: o script de outro computador envia, o painel executável busca e guarda tudo aqui. ---------

/** Conexão do painel com a central. Só o token fica guardado no computador, nunca a senha. */
export interface CentralEstado {
  conectado: boolean;
  /** Endereço salvo (ou o padrão, antes da primeira conexão). */
  endereco: string;
  endereco_padrao: string;
  host: string;
  usuario: { nome: string; funcao: string | null } | null;
  /** Empresa da central; continua depois de desconectar, para os testes já baixados. */
  empresa: { nome: string } | null;
  ultima_busca: string | null;
  ultima_tentativa: string | null;
  /** Conectado, mas a última busca não alcançou a central (sem internet ou central fora do ar). */
  sem_conexao: boolean;
  ultimo_erro: string | null;
  buscando: boolean;
  /** Token protegido pelo Windows (DPAPI); null quando desconectado. */
  token_protegido: boolean | null;
  intervalo_s: number;
  trechos_pendentes: number;
}

export interface CodigoPareamento {
  /** "ABCD-2345": digitado no RotaGuard Teste do outro computador (Conectar à empresa). */
  codigo: string;
  expira_em: string;
  validade_min: number;
  nome: string | null;
  aparelho_uid: string | null;
}

export interface ResumoSessaoRemota {
  duracao_s?: number | null;
  eventos_por_tipo?: Record<string, number>;
  perclos_medio?: number | null;
  piscadas_por_minuto?: number | null;
  trechos?: number | null;
  fps_medio?: number | null;
}

export interface AparelhoRemoto {
  uid: string;
  nome: string;
  computador: string | null;
  programa: string | null;
  pareado_em: string | null;
  ultimo_sinal: string | null;
  testando_agora: boolean;
  /** 0 a 3, só enquanto testa. */
  risco_atual: number | null;
  sessao_atual_uid: string | null;
  /** Desligado da empresa na central (o token dele deixou de valer). */
  revogado_em: string | null;
  sessoes: number;
}

export interface SessaoRemota {
  uid: string;
  aparelho_uid: string | null;
  aparelho_nome: string;
  iniciada_em: string | null;
  encerrada_em: string | null;
  em_andamento: boolean;
  /** Sem fim registrado e o computador já não está testando (fechou de repente ou perdeu a internet). */
  sem_fim: boolean;
  programa: string | null;
  camera: string | null;
  resumo: ResumoSessaoRemota;
  eventos?: number;
  trechos?: number;
  trechos_baixados?: number;
}

export interface EventoRemoto {
  uid: string;
  tipo: string | null;
  nivel_risco: number | null;
  duracao_s: number | null;
  ocorrido_em: string | null;
  detalhes: Record<string, unknown>;
  trecho_uid: string | null;
}

export interface TrechoRemoto {
  uid: string;
  sessao_uid: string | null;
  evento_uid: string | null;
  tipo: string | null;
  inicio: string | null;
  fim: string | null;
  duracao_s: number | null;
  formato: string | null;
  tamanho: number | null;
  baixado: boolean;
  erro: string | null;
}

export interface RemotosLista {
  central: CentralEstado;
  aparelhos: AparelhoRemoto[];
  sessoes: SessaoRemota[];
}

export interface SessaoRemotaDetalhe {
  sessao: SessaoRemota;
  aparelho: AparelhoRemoto | null;
  eventos: EventoRemoto[];
  /** Vazio para quem não tem `ver_video` (Consulta). */
  trechos: TrechoRemoto[];
  pode_ver_trechos: boolean;
}

/** Como tocar: MP4/WebM por `url` num <video>; .rgclip por `quadros` num canvas; ou o motivo de ainda não dar. */
export type TrechoParaTocar = TrechoRemoto & {
  aparelho_nome: string;
  disponivel: boolean;
  motivo?: string;
  url?: string;
  mime?: string;
  fps?: number;
  largura?: number | null;
  altura?: number | null;
  quadros?: { t: number; url: string }[];
};

export interface NovoAdministrador {
  nome: string;
  usuario: string;
  senha: string;
}

/** Painel pela web (spec 024): ativar exige o código entregue pela RotaGuard. No app instalado é ignorado. */
export interface OpcoesAtivacao {
  codigo_ativacao?: string;
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
export type MotoristaDados = Partial<Omit<Motorista, "viagens_30d" | "confirmados_30d" | "termo">> & {
  /** O arquivo do termo entra só por `termo_importar`. */
  termo?: { assinado: boolean; data: string | null; versao: string | null };
};
export type VeiculoDados = Partial<Veiculo>;

export interface Api {
  estado(): Promise<Resposta<Estado>>;
  /** Spec 030: sem o arquivo da empresa, cria a empresa com o nome digitado e o administrador, sem nenhum registro. */
  ativar_local(empresa: string, admin: NovoAdministrador, opcoes?: OpcoesAtivacao): Promise<Resposta<{ codigo_recuperacao: string }>>;
  ativar_com_arquivo(conteudo: string, admin: NovoAdministrador, opcoes?: OpcoesAtivacao): Promise<Resposta<{ codigo_recuperacao: string }>>;
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
  inicio_resumo(): Promise<Resposta<InicioResumo>>;
  primeiros_passos_esconder(esconder: boolean): Promise<Resposta<{ primeiros_passos_escondidos: boolean }>>;
  preferencias_salvar(valores: PreferenciasEntrada): Promise<Resposta<Preferencias>>;
  termo_importar(motorista_id: number, arquivo: ArquivoEnviado, dados: { data: string; versao?: string | null }): Promise<Resposta<Motorista>>;
  termo_ver(motorista_id: number): Promise<Resposta<TermoVisto>>;
  motorista_termos(motorista_id: number): Promise<Resposta<TermoRegistro[]>>;
  script_estado(): Promise<Resposta<ScriptEstado>>;
  script_eventos(desde_id: number): Promise<Resposta<EventoScript[]>>;
  /** Spec 026: qualquer sessão vê o estado; conectar, desconectar e gerar código são de Configurações. */
  central_estado(): Promise<Resposta<CentralEstado>>;
  central_conectar(endereco: string, usuario: string, senha: string): Promise<Resposta<CentralEstado>>;
  central_desconectar(): Promise<Resposta<CentralEstado>>;
  central_gerar_codigo(nome: string | null): Promise<Resposta<CodigoPareamento>>;
  remotos_listar(): Promise<Resposta<RemotosLista>>;
  remotos_sessao(sessao_uid: string): Promise<Resposta<SessaoRemotaDetalhe>>;
  /** Exige `ver_video`; registra "abriu trecho". */
  remotos_trecho(trecho_uid: string): Promise<Resposta<TrechoParaTocar>>;
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
  "ativar_local",
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
  "inicio_resumo",
  "primeiros_passos_esconder",
  "preferencias_salvar",
  "termo_importar",
  "termo_ver",
  "motorista_termos",
  "script_estado",
  "script_eventos",
  "central_estado",
  "central_conectar",
  "central_desconectar",
  "central_gerar_codigo",
  "remotos_listar",
  "remotos_sessao",
  "remotos_trecho",
] as const satisfies readonly (keyof Api)[];

// Falha na compilação se algum método do contrato ficar de fora da lista acima.
type Faltando = Exclude<keyof Api, (typeof NOMES)[number]>;
export const CONTRATO_COMPLETO: [Faltando] extends [never] ? true : never = true;

type Metodo = (...args: unknown[]) => Promise<unknown>;
type Transporte = Record<string, Metodo | undefined>;

/** De onde vêm as respostas: a janela do app (Python), o transporte vazio (fora do app) ou o servidor (painel na web). */
export type OrigemPonte = "janela" | "vazio" | "servidor";

/** Resposta de toda chamada fora da janela do app (spec 030): nada fictício, só o caminho certo. */
export const FORA_DO_APP = "O painel abre pelo app RotaGuard Painel instalado neste computador.";

/** Tempo máximo esperando a janela do app avisar que a ponte está pronta. */
const ESPERA_JANELA_MS = 4000;

let transporte: Promise<Transporte> | null = null;
let origem: OrigemPonte | null = null;

// Transporte "servidor" (spec 024) ------------------------------------------------------------------------------------

/** Arquivo que o servidor devolve junto da resposta (exportações, cópia de segurança, PDF do termo). */
export interface ArquivoBaixado {
  nome: string;
  /** Tipo MIME, ex.: application/json. */
  tipo: string;
  base64: string;
}

export interface OpcoesServidor {
  /** basePath do build web, ex.: "/painel". */
  base: string;
  /** Troca o fetch (testes). */
  buscar?: (url: string, init: RequestInit) => Promise<Response>;
  /** Troca o download no navegador (testes). */
  baixar?: (arquivo: ArquivoBaixado) => void;
  /** Troca a abertura em outra aba (testes). */
  abrir?: (arquivo: ArquivoBaixado) => void;
}

/** Posição das opções de ativação nos argumentos; elas não vão para a ponte. */
const OPCOES_DE_ATIVACAO: Partial<Record<keyof Api, number>> = { ativar_local: 2, ativar_com_arquivo: 2 };

function separarAtivacao(nome: keyof Api, args: unknown[]): { args: unknown[]; ativacao?: string } {
  const posicao = OPCOES_DE_ATIVACAO[nome];
  if (posicao === undefined || args.length <= posicao) return { args };
  const opcoes = args[posicao] as OpcoesAtivacao | undefined;
  const codigo = typeof opcoes?.codigo_ativacao === "string" ? opcoes.codigo_ativacao.trim() : "";
  return codigo ? { args: args.slice(0, posicao), ativacao: codigo } : { args: args.slice(0, posicao) };
}

function blobDoArquivo(arquivo: ArquivoBaixado): Blob {
  const binario = atob(arquivo.base64);
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i += 1) bytes[i] = binario.charCodeAt(i);
  return new Blob([bytes], { type: arquivo.tipo || "application/octet-stream" });
}

function baixarNoNavegador(arquivo: ArquivoBaixado): void {
  const url = URL.createObjectURL(blobDoArquivo(arquivo));
  const link = document.createElement("a");
  link.href = url;
  link.download = arquivo.nome;
  link.rel = "noopener";
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** PDF do termo: abre em outra aba; se o navegador bloquear a aba, baixa. */
function abrirNoNavegador(arquivo: ArquivoBaixado): void {
  const url = URL.createObjectURL(blobDoArquivo(arquivo));
  const aba = window.open(url, "_blank");
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  if (aba) aba.opener = null;
  else baixarNoNavegador(arquivo);
}

function arquivoValido(arquivo: unknown): arquivo is ArquivoBaixado {
  if (!arquivo || typeof arquivo !== "object") return false;
  const { nome, tipo, base64 } = arquivo as Record<string, unknown>;
  return typeof nome === "string" && typeof tipo === "string" && typeof base64 === "string";
}

/** POST {base}/api/ponte/{metodo} com {args}; cookie HttpOnly da sessão (mesma origem) e cabeçalho contra CSRF. */
export function transporteDoServidor({ base, buscar, baixar, abrir }: OpcoesServidor): Transporte {
  const pedir = async (nome: keyof Api, todos: unknown[]): Promise<Resposta<unknown>> => {
    const { args, ativacao } = separarAtivacao(nome, todos);
    let resposta: Response;
    try {
      const init: RequestInit = {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json", "X-RotaGuard": "1" },
        body: JSON.stringify(ativacao === undefined ? { args } : { args, ativacao }),
      };
      const url = `${base}/api/ponte/${nome}`;
      resposta = buscar ? await buscar(url, init) : await globalThis.fetch(url, init);
    } catch {
      return { ok: false, erro: "Sem conexão com o servidor do painel. Confira a internet e tente de novo." };
    }
    let corpo: unknown = null;
    try {
      corpo = await resposta.json();
    } catch {
      corpo = null;
    }
    if (!corpo || typeof corpo !== "object" || !("ok" in corpo)) {
      if (resposta.status === 413) return { ok: false, erro: "O envio passou de 16 MB. Escolha um arquivo menor.", codigo: "invalido" };
      return { ok: false, erro: "O servidor do painel respondeu de um jeito inesperado. Tente de novo." };
    }
    const { arquivo, ...semArquivo } = corpo as Resposta<unknown> & { arquivo?: unknown };
    if (semArquivo.ok && arquivoValido(arquivo)) {
      if (nome === "termo_ver") {
        (abrir ?? abrirNoNavegador)(arquivo);
      } else {
        (baixar ?? baixarNoNavegador)(arquivo);
        if (semArquivo.dados && typeof semArquivo.dados === "object" && "caminho" in semArquivo.dados) {
          semArquivo.dados = { ...semArquivo.dados, caminho: `${arquivo.nome} (pasta de downloads do navegador)` };
        }
      }
    }
    return semArquivo;
  };
  return Object.fromEntries(NOMES.map((nome) => [nome, (...args: unknown[]) => pedir(nome, args)]));
}

function apiDaJanela(): Transporte | undefined {
  if (typeof window === "undefined") return undefined;
  const api = (window as unknown as { pywebview?: { api?: Transporte } }).pywebview?.api;
  return api && typeof api.estado === "function" ? api : undefined;
}

/** Fora da janela do app: nenhuma tela recebe dado; todas recebem a frase de abrir pelo app. */
export function transporteVazio(): Transporte {
  return Object.fromEntries(NOMES.map((nome) => [nome, async () => ({ ok: false, erro: FORA_DO_APP })]));
}

function vazio(): Transporte {
  origem = "vazio";
  return transporteVazio();
}

function escolherTransporte(): Promise<Transporte> {
  if (transporte) return transporte;
  // Build web: sempre o servidor (nem janela, nem transporte vazio). No app instalado PAINEL_NA_WEB é false.
  if (PAINEL_NA_WEB) {
    origem = "servidor";
    transporte = Promise.resolve(transporteDoServidor({ base: BASE_DO_BUILD }));
    return transporte;
  }
  transporte = new Promise<Transporte>((resolve) => {
    const pronta = apiDaJanela();
    if (pronta) {
      origem = "janela";
      resolve(pronta);
      return;
    }
    // Fora do navegador (build): não espera a janela.
    if (typeof window === "undefined") {
      resolve(vazio());
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
        resolve(vazio());
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
    // O código de ativação só existe no servidor; a janela recebe os argumentos de sempre.
    const resposta = await metodo.apply(alvo, origem === "servidor" ? args : separarAtivacao(nome, args).args);
    if (resposta && typeof resposta === "object" && "ok" in resposta) return resposta as Resposta<unknown>;
    return { ok: false, erro: "O painel respondeu de um jeito inesperado. Tente de novo." };
  } catch {
    return { ok: false, erro: "Não foi possível falar com o painel. Tente de novo." };
  }
}

export const bridge = Object.fromEntries(NOMES.map((nome) => [nome, (...args: unknown[]) => chamar(nome, args)])) as unknown as Api;

/** De onde vêm as respostas: a janela do app (Python), o transporte vazio ou o servidor (painel na web). */
export async function origemDaPonte(): Promise<OrigemPonte> {
  await escolherTransporte();
  return origem ?? "vazio";
}
