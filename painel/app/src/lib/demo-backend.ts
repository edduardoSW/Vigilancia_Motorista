// Demonstração em memória do contrato da ponte (painel parte 2): mesmos nomes, respostas e permissões do Python, com os
// dados fictícios. Nada vai para disco nem para o navegador; recarregar a janela começa do zero (ENT-07).
// A assinatura do arquivo da empresa só é conferida no Python; aqui ele é aceito se tiver o formato certo.
// Captura de tela sem janela: `?sessao=administrador|supervisor|consulta` abre já ativado e com alguém dentro.
import { dados } from "@/content";
import { momentosDaViagem } from "@/content/moments";
import type {
  Acao,
  Api,
  Atividade,
  Caixa,
  Configuracoes,
  Decisao,
  Estado,
  Funcao,
  Motorista,
  NovoAdministrador,
  Resposta,
  Usuario,
  Veiculo,
} from "./bridge";
import { podeFazer, SENHA_MINIMA } from "./bridge";

const VERSAO = "0.1.0";
const FUNCOES: Funcao[] = ["administrador", "supervisor", "consulta"];
const LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const COMUNS = new Set([
  "1234567890",
  "12345678910",
  "0123456789",
  "0987654321",
  "senha12345",
  "senhasenha",
  "senha123456",
  "qwertyuiop",
  "abcdefghij",
  "password123",
  "rotaguard123",
  "administrador",
  "mudar123456",
  "abc1234567",
]);

type Erro = { ok: false; erro: string; codigo?: Extract<Resposta<unknown>, { ok: false }>["codigo"]; campo?: string; esperar_s?: number };
type Conta = Usuario & { senha: string };

const ok = <T>(valor: T): Resposta<T> => ({ ok: true, dados: valor });
const falha = (erro: string, extra: Omit<Erro, "ok" | "erro"> = {}): Erro => ({ ok: false, erro, ...extra });
const agora = () => new Date().toISOString();
const pausa = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const ehErro = (valor: unknown): valor is Erro => typeof valor === "object" && valor !== null && (valor as Erro).ok === false;

function sortear(tamanho: number) {
  const bytes = new Uint8Array(tamanho);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => LETRAS[byte % LETRAS.length]).join("");
}

// CNH: 9 dígitos de base e 2 verificadores (regra do Denatran usada pelos validadores brasileiros).
function cnhComDigitos(base: string) {
  let soma = 0;
  for (let i = 0; i < 9; i++) soma += Number(base[i]) * (9 - i);
  let primeiro = soma % 11;
  let desconto = 0;
  if (primeiro >= 10) {
    primeiro = 0;
    desconto = 2;
  }
  soma = 0;
  for (let i = 0; i < 9; i++) soma += Number(base[i]) * (i + 1);
  const resto = soma % 11;
  const segundo = resto >= 10 ? 0 : resto - desconto;
  return segundo < 0 ? null : `${base}${primeiro}${segundo}`;
}

export function cnhValida(numero: string) {
  return /^\d{11}$/.test(numero) && !/^(\d)\1{10}$/.test(numero) && cnhComDigitos(numero.slice(0, 9)) === numero;
}

function cnhDemo(semente: number) {
  for (let base = semente; ; base++) {
    const numero = cnhComDigitos(String(base).padStart(9, "0"));
    if (numero && !/^(\d)\1{10}$/.test(numero)) return numero;
  }
}

function cpfValido(valor: string) {
  if (!/^\d{11}$/.test(valor) || /^(\d)\1{10}$/.test(valor)) return false;
  const digito = (tamanho: number) => {
    let soma = 0;
    for (let i = 0; i < tamanho; i++) soma += Number(valor[i]) * (tamanho + 1 - i);
    const resto = (soma * 10) % 11;
    return resto === 10 ? 0 : resto;
  };
  return digito(9) === Number(valor[9]) && digito(10) === Number(valor[10]);
}

function problemaDaSenha(senha: string) {
  if (senha.length < SENHA_MINIMA) return `A senha precisa ter pelo menos ${SENHA_MINIMA} caracteres.`;
  if (COMUNS.has(senha.toLowerCase()) || /^(.)\1+$/.test(senha)) return "Essa senha é muito comum. Escolha outra; pode ser uma frase.";
  return null;
}

function problemaDoAdmin(admin: NovoAdministrador): Erro | null {
  if (!admin || typeof admin !== "object") return falha("Preencha nome, usuário e senha.", { codigo: "invalido" });
  if ((admin.nome ?? "").trim().length < 2) return falha("Escreva o nome de quem vai administrar o painel.", { codigo: "invalido", campo: "nome" });
  const usuario = (admin.usuario ?? "").trim().toLowerCase();
  if (!/^[a-z0-9][a-z0-9._-]{2,31}$/.test(usuario)) {
    return falha("O usuário deve ter de 3 a 32 letras minúsculas, números, ponto ou traço, sem espaço.", { codigo: "invalido", campo: "usuario" });
  }
  const senha = problemaDaSenha(admin.senha ?? "");
  return senha ? falha(senha, { codigo: "invalido", campo: "senha" }) : null;
}

const nomeCurto = (nome: string) => {
  const partes = nome.trim().split(/\s+/);
  return partes.length > 1 ? `${partes[0]} ${partes.at(-1)![0]}.` : partes[0];
};

function motoristasDemo(): Motorista[] {
  const base = [
    ["m-01", "Carlos Menezes", "0412", "D", "2028-03-31", "2026-09-02", 12, 3, 48213576],
    ["m-02", "Juliana Prado", "0388", "D", "2027-11-30", "2026-09-02", 9, 0, 31947265],
    ["m-03", "Rogério Lima", "0291", "E", "2026-09-26", "2026-09-03", 14, 1, 52618394],
    ["m-04", "Aline Costa", "0455", "D", "2029-06-30", "2026-09-02", 10, 0, 67305182],
    ["m-05", "Marcos Teixeira", "0467", "D", "2030-01-15", null, 2, 0, 74129653],
  ] as const;
  return base.map(([ref, nome, matricula, categoria, validade, termo, viagens, confirmados, semente], indice) => ({
    id: indice + 1,
    ref,
    nome,
    nome_curto: nomeCurto(nome),
    matricula,
    cpf: null,
    telefone: null,
    cnh_numero: cnhDemo(semente),
    cnh_categoria: categoria,
    cnh_validade: validade,
    situacao: "ativo",
    termo: { assinado: Boolean(termo), data: termo, versao: termo ? "1" : null },
    observacoes: null,
    viagens_30d: viagens,
    confirmados_30d: confirmados,
  }));
}

const PLACAS: Record<string, string> = {
  "3302": "BRA2E19",
  "2258": "BRA3F27",
  "2240": "BRA1C84",
  "3310": "BRA5H02",
  "2251": "BRA4D66",
  "2263": "BRA7B31",
  "1187": "BRA8A12",
};
const ANOS: Record<string, number> = { "3302": 2021, "2258": 2022, "2240": 2020, "3310": 2023, "2251": 2019, "2263": 2022, "1187": 2018 };

function frotaDemo(): { veiculos: Veiculo[]; caixas: Caixa[] } {
  const coleta = dados.coletas[0];
  const veiculos: Veiculo[] = [];
  const caixas: Caixa[] = [];
  dados.veiculos.forEach((veiculo, indice) => {
    const id = indice + 1;
    const viagem = dados.viagens.find((item) => item.veiculo === veiculo.prefixo);
    caixas.push({
      id,
      codigo: veiculo.caixa,
      veiculo_id: id,
      situacao: veiculo.situacao === "atencao" ? "atencao" : "ok",
      detalhe: veiculo.situacao === "atencao" ? veiculo.detalhe : null,
      ultima_coleta: viagem?.chegada ?? (coleta?.veiculo === veiculo.prefixo ? coleta.conectadaEm : null),
      versao: "1.0.0",
    });
    veiculos.push({
      id,
      numero: veiculo.prefixo,
      placa: PLACAS[veiculo.prefixo] ?? "",
      tipo: veiculo.tipo,
      transporta: veiculo.tipo === "caminhao" ? "carga" : "passageiros",
      modelo: veiculo.descricao,
      ano: ANOS[veiculo.prefixo] ?? null,
      situacao: "em_uso",
      caixa_id: id,
    });
  });
  caixas.push({ id: caixas.length + 1, codigo: "RG-0155", veiculo_id: null, situacao: "ok", detalhe: null, ultima_coleta: null, versao: "1.0.0" });
  return { veiculos, caixas };
}

function decisoesDemo(): Map<string, Decisao> {
  const registro = new Map<string, Decisao>();
  for (const viagem of dados.viagens) {
    for (const momento of momentosDaViagem(viagem)) {
      if (momento.decisaoInicial) registro.set(momento.id, { momento_id: momento.id, ...momento.decisaoInicial, funcao: "administrador" });
    }
  }
  return registro;
}

const MOMENTOS = new Map(dados.viagens.flatMap((viagem) => momentosDaViagem(viagem).map((momento) => [momento.id, viagem] as const)));

const configPadrao = (nome: string): Configuracoes => ({
  empresa: { nome, razao_social: "", cnpj: "", telefone: "", endereco: "" },
  regras: { direcao_continua_min: 330 },
  guarda: { videos_dias: 30, registros_anos: 5, desligados_anos: 5 },
  acesso: { bloqueio_min: 15 },
  aparencia: { texto_maior: false },
});

export function criarDemonstracao(): Api {
  let ativado = false;
  let modo: Estado["modo"] = null;
  let contas: Conta[] = [];
  let sessaoId: number | null = null;
  let bloqueado = false;
  let ultimoUso = Date.now();
  let codigoRecuperacao: string | null = null;
  let motoristas: Motorista[] = [];
  let veiculos: Veiculo[] = [];
  let caixas: Caixa[] = [];
  let decisoes = new Map<string, Decisao>();
  const atividades: Atividade[] = [];
  let config = configPadrao("Viação Demonstração");
  const tentativas = new Map<string, { erros: number; esperaAte: number }>();

  const publico = ({ senha: _senha, ...usuario }: Conta): Usuario => ({ ...usuario });
  const sessao = () => contas.find((conta) => conta.id === sessaoId && conta.ativo) ?? null;

  function registrar(quem: string | null, acao: string, alvo: string | null = null, detalhe: string | null = null) {
    atividades.push({ id: atividades.length + 1, em: agora(), usuario: quem, acao, alvo, detalhe });
  }

  function conferirTempo() {
    if (sessaoId !== null && !bloqueado && Date.now() - ultimoUso > config.acesso.bloqueio_min * 60_000) {
      bloqueado = true;
      registrar(sessao()?.nome ?? null, "bloqueou", null, "tempo sem uso");
    }
  }

  function exigir(acao?: Acao, { mesmoBloqueado = false } = {}): Conta | Erro {
    const conta = sessao();
    if (!conta) return falha("Entre de novo para continuar.", { codigo: "sem_sessao" });
    conferirTempo();
    if (bloqueado && !mesmoBloqueado) return falha("A tela está bloqueada. Digite a senha para continuar.", { codigo: "bloqueado" });
    if (acao && !podeFazer(conta.funcao, acao)) {
      registrar(conta.nome, "tentou sem permissão", acao);
      return falha("Sua função não permite fazer isso.", { codigo: "sem_permissao" });
    }
    if (!bloqueado) ultimoUso = Date.now();
    return conta;
  }

  function novaConta(nome: string, usuario: string, funcao: Funcao, senha: string, trocar: boolean): Conta {
    const conta: Conta = {
      id: contas.reduce((maior, item) => Math.max(maior, item.id), 0) + 1,
      nome: nome.trim(),
      usuario: usuario.trim().toLowerCase(),
      funcao,
      ativo: true,
      ultimo_acesso: null,
      trocar_senha: trocar,
      senha,
    };
    contas.push(conta);
    return conta;
  }

  function ativar(modoNovo: "demonstracao" | "empresa", nomeEmpresa: string, admin: NovoAdministrador, comDados: boolean) {
    ativado = true;
    modo = modoNovo;
    config = configPadrao(nomeEmpresa);
    if (comDados) {
      motoristas = motoristasDemo();
      ({ veiculos, caixas } = frotaDemo());
      decisoes = decisoesDemo();
    }
    contas = [];
    const conta = novaConta(admin.nome, admin.usuario, "administrador", admin.senha, false);
    conta.ultimo_acesso = agora();
    sessaoId = conta.id;
    bloqueado = false;
    ultimoUso = Date.now();
    codigoRecuperacao = [sortear(4), sortear(4), sortear(4), sortear(4)].join("-");
    registrar(conta.nome, "ativou o painel", nomeEmpresa, modoNovo === "demonstracao" ? "demonstração" : "arquivo da empresa");
    registrar(conta.nome, "entrou");
    return codigoRecuperacao;
  }

  // Captura de tela sem janela: começa ativado e com a função pedida dentro.
  if (typeof window !== "undefined") {
    const pedida = new URLSearchParams(window.location.search).get("sessao") as Funcao | null;
    if (pedida && FUNCOES.includes(pedida)) {
      ativar("demonstracao", "Viação Demonstração", { nome: "Marina Lopes", usuario: "marina.lopes", senha: sortear(16) }, true);
      codigoRecuperacao = null;
      novaConta("Paulo Reis", "paulo.reis", "supervisor", sortear(16), false).ultimo_acesso = agora();
      novaConta("Ana Souza", "ana.souza", "consulta", sortear(16), false);
      sessaoId = contas.find((conta) => conta.funcao === pedida)!.id;
    }
  }

  const api: Api = {
    async estado() {
      conferirTempo();
      return ok<Estado>({
        ativado,
        modo,
        empresa: ativado ? { nome: config.empresa.nome } : null,
        sessao: sessao() ? publico(sessao()!) : null,
        bloqueado: Boolean(sessao()) && bloqueado,
        versao: VERSAO,
        bloqueio_min: config.acesso.bloqueio_min,
      });
    },

    async ativar_demonstracao(admin) {
      await pausa(150);
      if (ativado) return falha("O painel já está ativado.", { codigo: "conflito" });
      const problema = problemaDoAdmin(admin);
      if (problema) return problema;
      return ok({ codigo_recuperacao: ativar("demonstracao", "Viação Demonstração", admin, true) });
    },

    async ativar_com_arquivo(conteudo, admin) {
      await pausa(150);
      if (ativado) return falha("O painel já está ativado.", { codigo: "conflito" });
      let arquivo: { formato?: unknown; empresa_id?: unknown; empresa_nome?: unknown; caixas?: unknown } | null = null;
      try {
        arquivo = JSON.parse(conteudo);
      } catch {
        arquivo = null;
      }
      if (!arquivo || arquivo.formato !== "rotaguard-chaveiro-coleta/1" || !Array.isArray(arquivo.caixas)) {
        return falha("Este arquivo não é válido. Peça um novo à RotaGuard.", { codigo: "invalido", campo: "arquivo" });
      }
      const problema = problemaDoAdmin(admin);
      if (problema) return problema;
      const nome = typeof arquivo.empresa_nome === "string" && arquivo.empresa_nome.trim() ? arquivo.empresa_nome.trim() : "Sua empresa";
      const codigo = ativar("empresa", nome, admin, false);
      caixas = (arquivo.caixas as { id_caixa?: unknown }[]).map((caixa, indice) => ({
        id: indice + 1,
        codigo: String(caixa.id_caixa ?? `caixa-${indice + 1}`),
        veiculo_id: null,
        situacao: "ok",
        detalhe: null,
        ultima_coleta: null,
        versao: null,
      }));
      return ok({ codigo_recuperacao: codigo });
    },

    async entrar(usuario, senha) {
      await pausa(200);
      if (!ativado) return falha("Ative o painel primeiro.", { codigo: "invalido" });
      const chave = String(usuario ?? "").trim().toLowerCase();
      const tentativa = tentativas.get(chave) ?? { erros: 0, esperaAte: 0 };
      const restante = Math.ceil((tentativa.esperaAte - Date.now()) / 1000);
      if (restante > 0) return falha(`Espere ${restante} segundos para tentar de novo.`, { codigo: "espera", esperar_s: restante });
      const conta = contas.find((item) => item.usuario === chave);
      if (conta && !conta.ativo) return falha("Este acesso foi desativado. Fale com o administrador.", { codigo: "invalido" });
      if (!conta || conta.senha !== senha) {
        tentativa.erros += 1;
        registrar(null, "errou a senha", chave || null);
        if (tentativa.erros >= 5) {
          const espera = Math.min(30 * 2 ** (tentativa.erros - 5), 900);
          tentativa.esperaAte = Date.now() + espera * 1000;
          tentativas.set(chave, tentativa);
          return falha(`Espere ${espera} segundos para tentar de novo.`, { codigo: "espera", esperar_s: espera });
        }
        tentativas.set(chave, tentativa);
        return falha("Usuário ou senha não conferem.", { codigo: "invalido" });
      }
      tentativas.delete(chave);
      conta.ultimo_acesso = agora();
      sessaoId = conta.id;
      bloqueado = false;
      ultimoUso = Date.now();
      registrar(conta.nome, "entrou");
      return ok(publico(conta));
    },

    async sair() {
      const conta = sessao();
      if (conta) registrar(conta.nome, "saiu");
      sessaoId = null;
      bloqueado = false;
      return ok({});
    },

    async bloquear() {
      const conta = exigir(undefined, { mesmoBloqueado: true });
      if (ehErro(conta)) return conta;
      if (!bloqueado) registrar(conta.nome, "bloqueou");
      bloqueado = true;
      return ok({});
    },

    async tocar() {
      const conta = exigir(undefined, { mesmoBloqueado: true });
      if (ehErro(conta)) return conta;
      return ok({ bloqueado });
    },

    async desbloquear(senha) {
      await pausa(150);
      const conta = exigir(undefined, { mesmoBloqueado: true });
      if (ehErro(conta)) return conta;
      if (conta.senha !== senha) return falha("Senha não confere.", { codigo: "invalido", campo: "senha" });
      bloqueado = false;
      ultimoUso = Date.now();
      registrar(conta.nome, "desbloqueou");
      return ok(publico(conta));
    },

    async trocar_senha(atual, nova) {
      await pausa(150);
      const conta = exigir();
      if (ehErro(conta)) return conta;
      if (conta.senha !== atual) return falha("A senha atual não confere.", { codigo: "invalido", campo: "atual" });
      const problema = problemaDaSenha(nova ?? "");
      if (problema) return falha(problema, { codigo: "invalido", campo: "nova" });
      if (nova === atual) return falha("A senha nova precisa ser diferente da atual.", { codigo: "invalido", campo: "nova" });
      conta.senha = nova;
      conta.trocar_senha = false;
      registrar(conta.nome, "trocou a senha");
      return ok({});
    },

    async recuperar_acesso(usuario, codigo, nova_senha) {
      await pausa(200);
      const conta = contas.find((item) => item.usuario === String(usuario ?? "").trim().toLowerCase() && item.funcao === "administrador");
      const limpo = String(codigo ?? "").trim().replace(/\s+/g, "").toLowerCase();
      if (!conta || !codigoRecuperacao || limpo !== codigoRecuperacao.toLowerCase()) {
        return falha("Usuário ou código de recuperação não conferem.", { codigo: "invalido" });
      }
      const problema = problemaDaSenha(nova_senha ?? "");
      if (problema) return falha(problema, { codigo: "invalido", campo: "nova_senha" });
      conta.senha = nova_senha;
      conta.ativo = true;
      conta.trocar_senha = false;
      codigoRecuperacao = null;
      tentativas.delete(conta.usuario);
      registrar(conta.nome, "recuperou o acesso com o código");
      return ok({});
    },

    async equipe_listar() {
      const conta = exigir("equipe");
      if (ehErro(conta)) return conta;
      return ok(contas.map(publico));
    },

    async equipe_adicionar(pessoa) {
      await pausa(150);
      const conta = exigir("equipe");
      if (ehErro(conta)) return conta;
      const nome = (pessoa?.nome ?? "").trim();
      const usuario = (pessoa?.usuario ?? "").trim().toLowerCase();
      if (nome.length < 2) return falha("Escreva o nome da pessoa.", { codigo: "invalido", campo: "nome" });
      if (!/^[a-z0-9][a-z0-9._-]{2,31}$/.test(usuario)) {
        return falha("O usuário deve ter de 3 a 32 letras minúsculas, números, ponto ou traço, sem espaço.", { codigo: "invalido", campo: "usuario" });
      }
      if (contas.some((item) => item.usuario === usuario)) return falha("Já existe alguém com esse usuário.", { codigo: "conflito", campo: "usuario" });
      if (!FUNCOES.includes(pessoa.funcao)) return falha("Escolha a função da pessoa.", { codigo: "invalido", campo: "funcao" });
      const senha = [sortear(4), sortear(4), sortear(4)].join("-").toLowerCase();
      const nova = novaConta(nome, usuario, pessoa.funcao, senha, true);
      registrar(conta.nome, "adicionou pessoa", nova.nome, pessoa.funcao);
      return ok({ usuario: publico(nova), senha_temporaria: senha });
    },

    async equipe_alterar(id, mudancas) {
      await pausa(150);
      const conta = exigir("equipe");
      if (ehErro(conta)) return conta;
      const alvo = contas.find((item) => item.id === id);
      if (!alvo) return falha("Pessoa não encontrada.", { codigo: "nao_encontrado" });
      const funcao = mudancas?.funcao ?? alvo.funcao;
      const ativo = mudancas?.ativo ?? alvo.ativo;
      if (!FUNCOES.includes(funcao)) return falha("Escolha a função da pessoa.", { codigo: "invalido", campo: "funcao" });
      const adminsDepois = contas.filter((item) => (item.id === id ? funcao === "administrador" && ativo : item.funcao === "administrador" && item.ativo));
      if (!adminsDepois.length) {
        return falha("O painel precisa de pelo menos um administrador ativo. Passe a função para outra pessoa antes.", { codigo: "conflito" });
      }
      if (funcao !== alvo.funcao) registrar(conta.nome, "mudou a função", alvo.nome, funcao);
      if (ativo !== alvo.ativo) registrar(conta.nome, ativo ? "reativou" : "desativou", alvo.nome);
      alvo.funcao = funcao;
      alvo.ativo = ativo;
      if (!ativo && alvo.id === sessaoId) sessaoId = null;
      return ok(publico(alvo));
    },

    async equipe_nova_senha(id) {
      await pausa(150);
      const conta = exigir("equipe");
      if (ehErro(conta)) return conta;
      const alvo = contas.find((item) => item.id === id);
      if (!alvo) return falha("Pessoa não encontrada.", { codigo: "nao_encontrado" });
      const senha = [sortear(4), sortear(4), sortear(4)].join("-").toLowerCase();
      alvo.senha = senha;
      alvo.trocar_senha = true;
      tentativas.delete(alvo.usuario);
      registrar(conta.nome, "criou senha temporária", alvo.nome);
      return ok({ senha_temporaria: senha });
    },

    async atividades_listar(filtro = {}) {
      const conta = exigir("atividades");
      if (ehErro(conta)) return conta;
      const nome = filtro.usuario_id ? contas.find((item) => item.id === filtro.usuario_id)?.nome : undefined;
      const itens = atividades
        .filter((item) => (filtro.usuario_id ? item.usuario === nome : true))
        .filter((item) => (filtro.de ? item.em.slice(0, 10) >= filtro.de : true))
        .filter((item) => (filtro.ate ? item.em.slice(0, 10) <= filtro.ate : true))
        .slice()
        .reverse()
        .slice(0, filtro.limite ?? 500);
      return ok({ itens, integro: true });
    },

    async atividades_exportar() {
      const conta = exigir("atividades");
      if (ehErro(conta)) return conta;
      return falha("Na demonstração sem a janela do app, salvar arquivo não está disponível.");
    },

    async motoristas_listar() {
      const conta = exigir();
      if (ehErro(conta)) return conta;
      return ok(motoristas.map((item) => ({ ...item, termo: { ...item.termo } })));
    },

    async motorista_salvar(entrada) {
      await pausa(200);
      const conta = exigir("cadastrar");
      if (ehErro(conta)) return conta;
      const atual = entrada?.id ? motoristas.find((item) => item.id === entrada.id) : undefined;
      if (entrada?.id && !atual) return falha("Motorista não encontrado.", { codigo: "nao_encontrado" });
      const junto = { ...atual, ...entrada };
      const nome = (junto.nome ?? "").trim();
      const matricula = (junto.matricula ?? "").trim();
      const cnh = String(junto.cnh_numero ?? "").replace(/\D/g, "");
      const cpf = junto.cpf ? String(junto.cpf).replace(/\D/g, "") : null;
      if (nome.length < 3) return falha("Escreva o nome completo do motorista.", { codigo: "invalido", campo: "nome" });
      if (!matricula) return falha("Escreva a matrícula.", { codigo: "invalido", campo: "matricula" });
      if (motoristas.some((item) => item.matricula === matricula && item.id !== atual?.id)) {
        return falha(`Já existe motorista com a matrícula ${matricula}.`, { codigo: "conflito", campo: "matricula" });
      }
      if (!cnhValida(cnh)) return falha("O número da CNH não confere. Confira os 11 dígitos.", { codigo: "invalido", campo: "cnh_numero" });
      if (!["C", "D", "E"].includes(junto.cnh_categoria ?? "")) return falha("Escolha a categoria da CNH.", { codigo: "invalido", campo: "cnh_categoria" });
      if (!/^\d{4}-\d{2}-\d{2}$/.test(junto.cnh_validade ?? "")) return falha("Informe a validade da CNH.", { codigo: "invalido", campo: "cnh_validade" });
      if (cpf && !cpfValido(cpf)) return falha("O CPF não confere. Confira os 11 dígitos ou deixe em branco.", { codigo: "invalido", campo: "cpf" });
      const termo = junto.termo ?? { assinado: false, data: null, versao: null };
      if (termo.assinado && !termo.data) return falha("Informe a data em que o termo foi assinado.", { codigo: "invalido", campo: "termo" });
      const salvo: Motorista = {
        id: atual?.id ?? motoristas.reduce((maior, item) => Math.max(maior, item.id), 0) + 1,
        ref: atual?.ref ?? null,
        nome,
        nome_curto: nomeCurto(nome),
        matricula,
        cpf,
        telefone: junto.telefone?.trim() || null,
        cnh_numero: cnh,
        cnh_categoria: junto.cnh_categoria as Motorista["cnh_categoria"],
        cnh_validade: junto.cnh_validade as string,
        situacao: ["ativo", "afastado", "desligado"].includes(junto.situacao ?? "") ? (junto.situacao as Motorista["situacao"]) : "ativo",
        termo: { assinado: Boolean(termo.assinado), data: termo.assinado ? termo.data : null, versao: termo.assinado ? (termo.versao ?? "1") : null },
        observacoes: junto.observacoes?.trim() || null,
        viagens_30d: atual?.viagens_30d ?? 0,
        confirmados_30d: atual?.confirmados_30d ?? 0,
      };
      motoristas = atual ? motoristas.map((item) => (item.id === salvo.id ? salvo : item)) : [...motoristas, salvo];
      registrar(conta.nome, atual ? "editou motorista" : "cadastrou motorista", salvo.nome);
      return ok(salvo);
    },

    async motorista_exportar(id) {
      const conta = exigir("cadastrar");
      if (ehErro(conta)) return conta;
      if (!motoristas.some((item) => item.id === id)) return falha("Motorista não encontrado.", { codigo: "nao_encontrado" });
      return falha("Na demonstração sem a janela do app, salvar arquivo não está disponível.");
    },

    async veiculos_listar() {
      const conta = exigir();
      if (ehErro(conta)) return conta;
      return ok(veiculos.map((item) => ({ ...item })));
    },

    async caixas_listar() {
      const conta = exigir();
      if (ehErro(conta)) return conta;
      return ok(caixas.map((item) => ({ ...item })));
    },

    async veiculo_salvar(entrada) {
      await pausa(200);
      const conta = exigir("cadastrar");
      if (ehErro(conta)) return conta;
      const atual = entrada?.id ? veiculos.find((item) => item.id === entrada.id) : undefined;
      if (entrada?.id && !atual) return falha("Veículo não encontrado.", { codigo: "nao_encontrado" });
      const junto = { ...atual, ...entrada };
      const numero = String(junto.numero ?? "").trim();
      const placa = String(junto.placa ?? "").replace(/[\s-]/g, "").toLocaleUpperCase("pt-BR");
      if (!numero) return falha("Escreva o número do veículo na frota.", { codigo: "invalido", campo: "numero" });
      if (veiculos.some((item) => item.numero === numero && item.id !== atual?.id)) {
        return falha(`Já existe veículo com o número ${numero}.`, { codigo: "conflito", campo: "numero" });
      }
      if (!/^[A-Z]{3}\d[A-Z0-9]\d{2}$/.test(placa)) return falha("A placa não confere. Use o formato ABC1D23 ou ABC-1234.", { codigo: "invalido", campo: "placa" });
      if (veiculos.some((item) => item.placa === placa && item.id !== atual?.id)) {
        return falha(`Já existe veículo com a placa ${placa}.`, { codigo: "conflito", campo: "placa" });
      }
      if (!["onibus", "micro_onibus", "caminhao", "van"].includes(junto.tipo ?? "")) return falha("Escolha o tipo do veículo.", { codigo: "invalido", campo: "tipo" });
      if (!["passageiros", "carga"].includes(junto.transporta ?? "")) return falha("Escolha o que o veículo transporta.", { codigo: "invalido", campo: "transporta" });
      const ano = junto.ano === null || junto.ano === undefined || (junto.ano as unknown) === "" ? null : Number(junto.ano);
      if (ano !== null && (!Number.isInteger(ano) || ano < 1980 || ano > new Date().getFullYear() + 1)) {
        return falha("O ano não confere.", { codigo: "invalido", campo: "ano" });
      }
      const salvo: Veiculo = {
        id: atual?.id ?? veiculos.reduce((maior, item) => Math.max(maior, item.id), 0) + 1,
        numero,
        placa,
        tipo: junto.tipo as Veiculo["tipo"],
        transporta: junto.transporta as Veiculo["transporta"],
        modelo: junto.modelo?.trim() || null,
        ano,
        situacao: ["em_uso", "oficina", "fora_de_uso"].includes(junto.situacao ?? "") ? (junto.situacao as Veiculo["situacao"]) : "em_uso",
        caixa_id: atual?.caixa_id ?? null,
      };
      veiculos = atual ? veiculos.map((item) => (item.id === salvo.id ? salvo : item)) : [...veiculos, salvo];
      registrar(conta.nome, atual ? "editou veículo" : "cadastrou veículo", salvo.numero);
      if (entrada.caixa_id !== undefined && entrada.caixa_id !== salvo.caixa_id) {
        const vinculo = await api.caixa_vincular(entrada.caixa_id ?? salvo.caixa_id ?? 0, entrada.caixa_id === null ? null : salvo.id);
        if (!vinculo.ok) return vinculo;
      }
      return ok({ ...veiculos.find((item) => item.id === salvo.id)! });
    },

    async caixa_vincular(caixa_id, veiculo_id) {
      const conta = exigir("cadastrar");
      if (ehErro(conta)) return conta;
      const caixa = caixas.find((item) => item.id === caixa_id);
      if (!caixa) return falha("Caixa não encontrada.", { codigo: "nao_encontrado" });
      const veiculo = veiculo_id === null ? null : veiculos.find((item) => item.id === veiculo_id);
      if (veiculo_id !== null && !veiculo) return falha("Veículo não encontrado.", { codigo: "nao_encontrado" });
      if (veiculo && caixa.situacao === "bloqueada") return falha("Esta caixa está bloqueada. Fale com a RotaGuard.", { codigo: "conflito" });
      for (const item of veiculos) if (item.caixa_id === caixa.id) item.caixa_id = null;
      if (veiculo) {
        for (const item of caixas) if (item.veiculo_id === veiculo.id) item.veiculo_id = null;
        veiculo.caixa_id = caixa.id;
      }
      caixa.veiculo_id = veiculo?.id ?? null;
      registrar(conta.nome, veiculo ? "vinculou caixa" : "desvinculou caixa", caixa.codigo, veiculo?.numero ?? null);
      return ok({ ...caixa });
    },

    async config_ler() {
      const conta = exigir();
      if (ehErro(conta)) return conta;
      return ok(structuredClone(config));
    },

    async config_salvar(secao, valores) {
      await pausa(200);
      const conta = exigir("configuracoes");
      if (ehErro(conta)) return conta;
      if (!(secao in config)) return falha("Parte das configurações desconhecida.", { codigo: "invalido" });
      const nova = { ...config[secao], ...valores } as Configuracoes[typeof secao];
      if (secao === "empresa") {
        const empresa = nova as Configuracoes["empresa"];
        if (!empresa.nome?.trim()) return falha("Escreva o nome da empresa.", { codigo: "invalido", campo: "nome" });
        if (empresa.cnpj && !/^\d{14}$/.test(empresa.cnpj.replace(/\D/g, ""))) return falha("O CNPJ precisa ter 14 dígitos.", { codigo: "invalido", campo: "cnpj" });
      }
      if (secao === "regras") {
        const minutos = (nova as Configuracoes["regras"]).direcao_continua_min;
        if (!Number.isInteger(minutos) || minutos < 60 || minutos > 330) {
          return falha("Use de 60 a 330 minutos (5 h 30 é o limite do CTB).", { codigo: "invalido", campo: "direcao_continua_min" });
        }
      }
      if (secao === "guarda") {
        const guarda = nova as Configuracoes["guarda"];
        if (![7, 15, 30, 60, 90].includes(guarda.videos_dias)) return falha("Escolha por quantos dias guardar os vídeos.", { codigo: "invalido", campo: "videos_dias" });
        if (![1, 2, 5].includes(guarda.registros_anos)) return falha("Escolha por quantos anos guardar os registros.", { codigo: "invalido", campo: "registros_anos" });
        if (![1, 2, 5].includes(guarda.desligados_anos)) return falha("Escolha por quantos anos guardar os desligados.", { codigo: "invalido", campo: "desligados_anos" });
      }
      if (secao === "acesso") {
        const minutos = (nova as Configuracoes["acesso"]).bloqueio_min;
        if (!Number.isInteger(minutos) || minutos < 5 || minutos > 60) return falha("Use de 5 a 60 minutos.", { codigo: "invalido", campo: "bloqueio_min" });
      }
      if (secao === "aparencia" && typeof (nova as Configuracoes["aparencia"]).texto_maior !== "boolean") {
        return falha("Escolha o tamanho do texto.", { codigo: "invalido", campo: "texto_maior" });
      }
      config = { ...config, [secao]: nova };
      registrar(conta.nome, "mudou configuração", secao);
      return ok(structuredClone(config));
    },

    async decisoes_listar() {
      const conta = exigir();
      if (ehErro(conta)) return conta;
      return ok([...decisoes.values()].map((item) => ({ ...item })));
    },

    async decisao_registrar(momento_id, resultado) {
      await pausa(120);
      const conta = exigir("decidir");
      if (ehErro(conta)) return conta;
      if (!MOMENTOS.has(momento_id)) return falha("Momento não encontrado.", { codigo: "nao_encontrado" });
      if (resultado !== "confirmado" && resultado !== "alarme_falso") return falha("Escolha confirmar ou alarme falso.", { codigo: "invalido" });
      const decisao: Decisao = { momento_id, resultado, orientado: false, por: conta.nome, funcao: conta.funcao, em: agora() };
      decisoes.set(momento_id, decisao);
      registrar(conta.nome, resultado === "confirmado" ? "confirmou momento" : "marcou alarme falso", momento_id);
      return ok({ ...decisao });
    },

    async decisao_desfazer(momento_id) {
      await pausa(120);
      const conta = exigir("decidir");
      if (ehErro(conta)) return conta;
      if (!decisoes.has(momento_id)) return falha("Este momento ainda não foi verificado.", { codigo: "nao_encontrado" });
      decisoes.delete(momento_id);
      registrar(conta.nome, "desfez decisão", momento_id);
      return ok({});
    },

    async decisao_orientado(momento_id, orientado) {
      await pausa(120);
      const conta = exigir("decidir");
      if (ehErro(conta)) return conta;
      const decisao = decisoes.get(momento_id);
      if (!decisao) return falha("Este momento ainda não foi verificado.", { codigo: "nao_encontrado" });
      if (decisao.resultado !== "confirmado") return falha("Só dá para registrar orientação em momento confirmado.", { codigo: "conflito" });
      const nova = { ...decisao, orientado: Boolean(orientado), por: conta.nome, funcao: conta.funcao, em: agora() };
      decisoes.set(momento_id, nova);
      registrar(conta.nome, orientado ? "registrou orientação" : "tirou orientação", momento_id);
      return ok({ ...nova });
    },

    async video_abrir(momento_id, motorista_ref) {
      const conta = exigir("ver_video");
      if (ehErro(conta)) return conta;
      if (!MOMENTOS.has(momento_id)) return falha("Momento não encontrado.", { codigo: "nao_encontrado" });
      const motorista = motoristas.find((item) => item.ref === motorista_ref);
      if (!motorista?.termo.assinado) return ok({ liberado: false, motivo: "Vídeo trancado: falta o termo de ciência" });
      registrar(conta.nome, "abriu vídeo", momento_id);
      return ok({ liberado: true });
    },

    async copia_fazer(senha) {
      await pausa(400);
      const conta = exigir("configuracoes");
      if (ehErro(conta)) return conta;
      if (conta.senha !== senha) return falha("Senha não confere.", { codigo: "invalido", campo: "senha" });
      registrar(conta.nome, "fez cópia de segurança", null, "demonstração: nada foi gravado");
      return ok({ caminho: "Demonstração: nenhuma cópia foi gravada", bytes: 0 });
    },

    async script_estado() {
      const conta = exigir();
      if (ehErro(conta)) return conta;
      return ok({ aberto: false, programa: null, desde: null, pid: null, camera: null, ultimo_sinal: null, eventos: 0, pasta: null });
    },

    async script_eventos() {
      const conta = exigir();
      if (ehErro(conta)) return conta;
      return ok([]);
    },
  };

  return api;
}

export const demoBackend: Api = criarDemonstracao();
