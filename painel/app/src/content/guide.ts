// Guia de uso do painel (spec 017): passos curtos em linguagem de garagem e "Se der errado" em cada capítulo.
// O capítulo de alertas sai de tipos-de-evento.json (mesmos nomes do servidor). Sem "@/": o teste importa este arquivo
// direto no Node (node --test apaga os tipos sozinho).
import tiposDeEvento from "./tipos-de-evento.json" with { type: "json" };

export type CapituloId =
  | "primeiros-passos"
  | "veiculo-chega"
  | "verificar-momentos"
  | "alertas"
  | "motoristas"
  | "veiculos"
  | "equipe"
  | "copia"
  | "problemas"
  | "privacidade";

export interface Topico {
  id: string;
  titulo: string;
  passos: string[];
}

export interface Alerta {
  tipo: string;
  rotulo: string;
  explicacao: string;
}

export interface Capitulo {
  id: CapituloId;
  numero: number;
  titulo: string;
  resumo: string;
  topicos: Topico[];
  alertas?: Alerta[];
  seDerErrado: { problema: string; solucao: string };
}

export const AVISO_ALERTAS = "Todo alerta ajuda a avaliação e não é diagnóstico. Quem decide é a pessoa que vê o vídeo.";

/** Uma frase simples por tipo de alerta. Tipo novo no JSON sem frase aqui faz o teste GUI-03 falhar. */
export const EXPLICACAO_ALERTA: Record<string, string> = {
  calibracao_concluida: "A caixa terminou de se ajustar ao rosto do motorista no começo da viagem. É aviso da caixa e não pede verificação.",
  rosto_nao_detectado: "A câmera ficou sem ver o rosto. Pode ser boné, mão na frente, sol forte ou câmera fora do lugar.",
  atencao: "Os olhos começaram a fechar mais devagar que o normal daquele motorista. É o primeiro sinal, antes da sonolência.",
  sonolencia: "Os olhos ficaram pesados ou fecharam várias vezes em pouco tempo.",
  microssono: "Os olhos ficaram fechados por cerca de 1 segundo com o veículo andando.",
  sono: "Os olhos ficaram fechados por cerca de 3 segundos com o veículo andando.",
  nao_responsivo: "Os olhos ficaram fechados por cerca de 6 segundos. Veja este vídeo primeiro.",
  olhos_esfregados: "O motorista esfregou ou coçou os olhos. Sozinho, é um sinal leve de sono.",
  mao_no_rosto: "A mão ficou no rosto por mais de 1 segundo. Sozinho, é um sinal leve de sono.",
  celular_na_mao: "A câmera viu o celular na mão do motorista com o veículo andando.",
  celular_no_ouvido: "O motorista levou o celular ao ouvido, como numa ligação.",
  olhando_celular: "O motorista olhou para o celular por mais de 2 segundos.",
  direcao_continua: "O motorista dirigiu sem pausa por mais tempo que o limite. A lei permite até 5 h 30 seguidas.",
  ativacao_atipica: "A caixa notou sinais fora do jeito normal daquele motorista. Não diz a causa: converse com ele antes de concluir.",
};

const tipos = tiposDeEvento as Record<string, { rotulo: string; categoria: string }>;

export const CAPITULOS: Capitulo[] = [
  {
    id: "primeiros-passos",
    numero: 1,
    titulo: "Primeiros passos",
    resumo: "O que fazer uma vez só, quando o painel chega na empresa.",
    topicos: [
      {
        id: "ativar",
        titulo: "Ativar o painel",
        passos: [
          "Abra o RotaGuard Painel neste computador.",
          "Escolha o arquivo da empresa que a RotaGuard entregou.",
          "Crie o seu acesso de administrador: nome, usuário e uma senha com pelo menos 10 letras ou números.",
          "Anote ou imprima o código de recuperação. Ele aparece uma vez só.",
        ],
      },
      {
        id: "deixar-pronto",
        titulo: "Deixar tudo pronto para a primeira viagem",
        passos: [
          "Em Veículos e caixas, cadastre os veículos da empresa.",
          "Em cada veículo, escolha a caixa que foi instalada nele.",
          "Em Motoristas, cadastre os motoristas com a CNH.",
          "Registre o termo de ciência de cada motorista.",
          "Em Equipe, adicione quem vai usar o painel.",
          "Em Configurações, faça a primeira cópia de segurança.",
        ],
      },
    ],
    seDerErrado: {
      problema: "O arquivo da empresa não foi aceito?",
      solucao: "Confira se é o arquivo mais novo que a RotaGuard mandou. Se continuar, peça outro. Enquanto isso, dá para abrir a demonstração.",
    },
  },
  {
    id: "veiculo-chega",
    numero: 2,
    titulo: "Quando o veículo chega",
    resumo: "Da garagem até a viagem aberta na tela.",
    topicos: [
      {
        id: "ler-caixa",
        titulo: "Ler a caixa",
        passos: [
          "Recolha a caixa do veículo e ligue o cabo dela neste computador.",
          "Espere o painel reconhecer a caixa. O andamento aparece no topo do menu.",
          "Confirme quem dirigiu. O painel sugere o último motorista daquele veículo.",
          "Quando a leitura terminar, clique em Abrir viagem.",
        ],
      },
    ],
    seDerErrado: {
      problema: "A caixa não apareceu depois de 2 minutos?",
      solucao: "Ligue o cabo em outra porta do computador e confira se a luz da caixa acendeu. Se continuar, veja Caixa não reconhecida no capítulo 9.",
    },
  },
  {
    id: "verificar-momentos",
    numero: 3,
    titulo: "Verificar os momentos",
    resumo: "Olhar o que a caixa marcou e dizer o que aconteceu de verdade.",
    topicos: [
      {
        id: "o-que-e",
        titulo: "O que é um momento",
        passos: [
          "Um momento é um trecho da viagem em que a caixa viu algo que merece uma olhada.",
          "Alertas parecidos e seguidos viram um momento só, para você ver uma vez.",
        ],
      },
      {
        id: "verificar",
        titulo: "Verificar um momento",
        passos: [
          "Em Viagens, abra a viagem.",
          "Clique no primeiro momento da lista.",
          "Veja o vídeo curto do momento.",
          "Clique em Confirmar se aconteceu mesmo, ou em Alarme falso se não aconteceu.",
          "Se já conversou com o motorista, marque Motorista orientado.",
        ],
      },
      {
        id: "desfazer",
        titulo: "Desfazer uma decisão",
        passos: [
          "Logo depois de decidir, clique em Desfazer no aviso do canto da tela.",
          "Se o aviso já sumiu, abra o momento de novo e clique em Desfazer.",
        ],
      },
    ],
    seDerErrado: {
      problema: "O botão do vídeo não aparece?",
      solucao: "A função Consulta não vê vídeo. Se você é Supervisor ou Administrador, veja se o motorista tem o termo de ciência registrado: sem termo, o vídeo fica trancado.",
    },
  },
  {
    id: "alertas",
    numero: 4,
    titulo: "O que cada alerta quer dizer",
    resumo: AVISO_ALERTAS,
    topicos: [
      {
        id: "como-ler",
        titulo: "Como ler um alerta",
        passos: [
          "Leia o nome do alerta e a hora em que aconteceu.",
          "Veja o vídeo antes de decidir.",
          "Pense no que estava em volta: estrada, horário e o jeito daquele motorista.",
          "Decida: confirmar, alarme falso ou motorista orientado.",
        ],
      },
    ],
    alertas: Object.entries(tipos).map(([tipo, { rotulo }]) => ({ tipo, rotulo, explicacao: EXPLICACAO_ALERTA[tipo] ?? "" })),
    seDerErrado: {
      problema: "O mesmo alerta aparece o tempo todo com um motorista?",
      solucao: "Pode ser a câmera fora do lugar, óculos escuros ou boné. Confira a câmera no veículo antes de conversar com o motorista.",
    },
  },
  {
    id: "motoristas",
    numero: 5,
    titulo: "Motoristas e termo de ciência",
    resumo: "Cadastro, CNH e o termo que libera os vídeos de cada motorista.",
    topicos: [
      {
        id: "cadastrar-motorista",
        titulo: "Cadastrar motorista",
        passos: [
          "Em Motoristas, clique em Cadastrar motorista.",
          "Preencha nome, matrícula e os dados da CNH.",
          "CPF e telefone não são obrigatórios.",
          "Clique em Salvar.",
        ],
      },
      {
        id: "termo",
        titulo: "Registrar o termo de ciência",
        passos: [
          "Abra o motorista e imprima o modelo do termo.",
          "Leia o termo com o motorista e peça a assinatura.",
          "Marque que o termo foi assinado e escreva a data.",
          "Guarde o papel assinado na pasta do motorista.",
        ],
      },
      {
        id: "por-que-termo",
        titulo: "Por que o termo existe",
        passos: [
          "O termo mostra que o motorista sabe que a câmera grava o rosto dele durante a viagem.",
          "Sem termo registrado, os vídeos daquele motorista ficam trancados no painel.",
        ],
      },
      {
        id: "cnh-vencendo",
        titulo: "CNH vencendo",
        passos: ["O Início avisa quando uma CNH está perto de vencer.", "Peça a CNH nova ao motorista e atualize a validade no cadastro."],
      },
    ],
    seDerErrado: {
      problema: "O motorista saiu da empresa?",
      solucao: "Não apague o cadastro. Mude a situação para Desligado: as viagens antigas continuam com o nome dele até o fim do prazo de guarda.",
    },
  },
  {
    id: "veiculos",
    numero: 6,
    titulo: "Veículos e caixas",
    resumo: "Cada veículo com a caixa que está instalada nele.",
    topicos: [
      {
        id: "cadastrar-veiculo",
        titulo: "Cadastrar veículo",
        passos: ["Em Veículos e caixas, clique em Cadastrar veículo.", "Preencha número, placa, tipo e o que ele transporta.", "Clique em Salvar."],
      },
      {
        id: "trocar-caixa",
        titulo: "Trocar a caixa de veículo",
        passos: ["Abra o veículo na lista.", "Em Caixa, escolha a caixa nova ou deixe sem caixa.", "Salve. A caixa antiga fica livre para outro veículo."],
      },
      {
        id: "caixa-atencao",
        titulo: "Caixa que precisa de atenção",
        passos: [
          "Leia o que está escrito ao lado da caixa na lista.",
          "Resolva no veículo o que foi apontado.",
          "Ligue a caixa neste computador de novo para conferir.",
        ],
      },
      {
        id: "caixa-bloqueada",
        titulo: "Caixa bloqueada",
        passos: ["Não instale a caixa bloqueada em nenhum veículo.", "Fale com a RotaGuard e informe o código escrito na caixa."],
      },
    ],
    seDerErrado: {
      problema: "A caixa não aparece para escolher?",
      solucao: "Ela pode estar ligada a outro veículo. Tire a caixa do outro veículo primeiro e escolha de novo.",
    },
  },
  {
    id: "equipe",
    numero: 7,
    titulo: "Equipe e acessos",
    resumo: "Quem usa o painel e o que cada pessoa pode fazer.",
    topicos: [
      {
        id: "funcoes",
        titulo: "As três funções",
        passos: [
          "Administrador faz tudo, inclusive equipe, configurações e cópia de segurança.",
          "Supervisor lê a caixa, vê os vídeos, verifica os momentos e cadastra motoristas e veículos.",
          "Consulta só vê as viagens e imprime relatórios.",
        ],
      },
      {
        id: "adicionar-pessoa",
        titulo: "Adicionar pessoa",
        passos: [
          "Em Equipe, clique em Adicionar pessoa.",
          "Escreva o nome. O painel sugere o usuário.",
          "Escolha a função.",
          "Passe a senha temporária para a pessoa. Ela troca a senha no primeiro acesso.",
        ],
      },
      {
        id: "senha-da-equipe",
        titulo: "Alguém da equipe esqueceu a senha",
        passos: ["Em Equipe, clique na pessoa.", "Clique em Criar senha nova.", "Passe a senha nova para a pessoa."],
      },
      {
        id: "desativar",
        titulo: "Pessoa que saiu da empresa",
        passos: ["Em Equipe, clique na pessoa.", "Clique em Desativar e confirme.", "O nome continua nas verificações que ela fez."],
      },
      {
        id: "registro",
        titulo: "Registro de atividades",
        passos: [
          "Em Equipe, abra Registro de atividades.",
          "Escolha a pessoa para ver só o que ela fez.",
          "Clique em Exportar CSV para abrir numa planilha.",
        ],
      },
    ],
    seDerErrado: {
      problema: "O painel não deixa desativar ou mudar a função?",
      solucao: "O último administrador ativo não pode sair nem virar Supervisor. Passe outra pessoa para Administrador antes.",
    },
  },
  {
    id: "copia",
    numero: 8,
    titulo: "Cópia de segurança",
    resumo: "Um arquivo com tudo o que está no painel, para não perder nada se o computador quebrar.",
    topicos: [
      {
        id: "fazer-copia",
        titulo: "Fazer uma cópia",
        passos: [
          "Em Configurações, abra Cópia de segurança.",
          "Escolha uma senha para a cópia e repita.",
          "Clique em Fazer cópia agora.",
          "Anote a senha junto com o código de recuperação.",
        ],
      },
      {
        id: "guardar-copia",
        titulo: "Guardar a cópia",
        passos: ["Copie o arquivo para um pen drive ou uma pasta de rede.", "Guarde o pen drive longe deste computador.", "Faça uma cópia nova toda semana."],
      },
      {
        id: "voltar-copia",
        titulo: "Voltar uma cópia",
        passos: ["Nesta versão, o painel ainda não volta a cópia sozinho.", "Guarde o arquivo e a senha: eles vão servir quando essa opção chegar."],
      },
    ],
    seDerErrado: {
      problema: "Esqueceu a senha da cópia?",
      solucao: "Sem a senha, a cópia não abre. Faça uma cópia nova agora, com uma senha anotada.",
    },
  },
  {
    id: "problemas",
    numero: 9,
    titulo: "Quando algo dá errado",
    resumo: "Os problemas mais comuns e o que fazer em cada um.",
    topicos: [
      {
        id: "caixa-nao-reconhecida",
        titulo: "Caixa não reconhecida",
        passos: [
          "Tire o cabo e ligue de novo.",
          "Tente outra porta do computador.",
          "Confira se a luz da caixa acendeu.",
          "Se continuar, anote o código escrito na caixa e fale com a RotaGuard.",
        ],
      },
      {
        id: "registro-alterado",
        titulo: "Registro alterado",
        passos: [
          "Se o painel avisar que o registro foi alterado, não apague nada.",
          "Anote o dia e a hora do aviso.",
          "Faça uma cópia de segurança.",
          "Fale com a RotaGuard.",
        ],
      },
      {
        id: "video-apagado",
        titulo: "Vídeo apagado pelo prazo",
        passos: [
          "Depois do prazo escolhido em Configurações, o painel apaga o vídeo sozinho.",
          "O relatório da viagem continua e mostra quando o vídeo foi apagado.",
          "Para guardar por mais tempo, aumente o prazo antes de o vídeo vencer.",
        ],
      },
      {
        id: "tela-bloqueada",
        titulo: "Tela bloqueada",
        passos: [
          "O painel bloqueia a tela depois de um tempo sem uso.",
          "Digite a sua senha para voltar.",
          "Você continua na mesma tela em que estava.",
        ],
      },
      {
        id: "esqueci-a-senha",
        titulo: "Esqueci a senha",
        passos: [
          "Peça ao administrador para criar uma senha nova para você.",
          "Se você é o único administrador, clique em Esqueci a senha na tela de entrar.",
          "Digite o código de recuperação anotado quando o painel foi ativado.",
          "Crie a senha nova.",
        ],
      },
    ],
    seDerErrado: {
      problema: "Nada disso resolveu?",
      solucao: "Anote o que apareceu na tela, com dia e hora, e fale com a RotaGuard.",
    },
  },
  {
    id: "privacidade",
    numero: 10,
    titulo: "Privacidade e LGPD",
    resumo: "O que o painel guarda, por quanto tempo e quem pode ver.",
    topicos: [
      {
        id: "o-que-guarda",
        titulo: "O que o painel guarda",
        passos: [
          "As viagens lidas das caixas e as decisões da equipe.",
          "Vídeos curtos só dos momentos, não da viagem inteira.",
          "O cadastro de motoristas, veículos e equipe.",
          "O registro de atividades de quem usou o painel.",
        ],
      },
      {
        id: "quanto-tempo",
        titulo: "Por quanto tempo",
        passos: [
          "Vídeos: 30 dias, se ninguém mudar em Configurações.",
          "Viagens e decisões: 5 anos.",
          "Dados de motorista desligado: 5 anos depois de sair.",
        ],
      },
      {
        id: "quem-ve",
        titulo: "Quem vê",
        passos: [
          "Administrador e Supervisor veem os vídeos.",
          "Consulta vê as viagens, sem vídeo.",
          "Os dados ficam guardados neste computador. Nada vai para a internet nesta versão.",
        ],
      },
      {
        id: "pedido-do-motorista",
        titulo: "Pedido do motorista",
        passos: [
          "Se o motorista pedir os dados dele, abra o cadastro e clique em Exportar.",
          "Entregue o arquivo só para o próprio motorista.",
          "A exportação fica no registro de atividades.",
        ],
      },
      {
        id: "proteger-computador",
        titulo: "Proteger o computador",
        passos: [
          "Cada pessoa usa uma conta do Windows com senha.",
          "Ligue o BitLocker do Windows: ele tranca o disco e só abre com a senha do computador.",
          "Ao sair de perto, clique em Sair. A tela bloqueia sozinha, mas sair é mais seguro.",
        ],
      },
    ],
    seDerErrado: {
      problema: "O computador sumiu ou foi roubado?",
      solucao: "Avise no mesmo dia o responsável pelos dados na empresa e a RotaGuard. É por isso que a cópia de segurança fica longe do computador.",
    },
  },
];

export const capituloDe = (id: string | null | undefined) => CAPITULOS.find((capitulo) => capitulo.id === id);

/** Minúsculas e sem acento, letra por letra (mantém a posição para destacar o trecho achado). */
export const normalizar = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export interface Resultado {
  capituloId: CapituloId;
  capituloNumero: number;
  capituloTitulo: string;
  topicoId: string | null;
  titulo: string;
  trecho: { antes: string; achado: string; depois: string };
}

interface Unidade {
  capitulo: Capitulo;
  topicoId: string | null;
  titulo: string;
  textos: string[];
}

function unidades(capitulos: Capitulo[]): Unidade[] {
  return capitulos.flatMap((capitulo) => [
    { capitulo, topicoId: null, titulo: capitulo.titulo, textos: [capitulo.resumo] },
    ...capitulo.topicos.map((topico) => ({ capitulo, topicoId: topico.id, titulo: topico.titulo, textos: topico.passos })),
    ...(capitulo.alertas ?? []).map((alerta) => ({ capitulo, topicoId: `alerta-${alerta.tipo}`, titulo: alerta.rotulo, textos: [alerta.explicacao] })),
    {
      capitulo,
      topicoId: "se-der-errado",
      titulo: "Se der errado",
      textos: [`${capitulo.seDerErrado.problema} ${capitulo.seDerErrado.solucao}`],
    },
  ]);
}

/** Acha a palavra no texto original, sem olhar acento nem maiúscula, e devolve a posição no texto original. */
function posicaoEm(texto: string, palavra: string) {
  const letras = Array.from(texto);
  let normalizado = "";
  const origem: number[] = [];
  let indice = 0;
  for (const letra of letras) {
    const convertida = normalizar(letra);
    for (let i = 0; i < convertida.length; i += 1) origem.push(indice);
    normalizado += convertida;
    indice += letra.length;
  }
  const achou = normalizado.indexOf(palavra);
  if (achou < 0) return null;
  const inicio = origem[achou];
  const fimNormalizado = achou + palavra.length - 1;
  const ultimaLetra = origem[fimNormalizado];
  const fim = ultimaLetra + (Array.from(texto.slice(ultimaLetra))[0]?.length ?? 1);
  return { inicio, fim };
}

function trechoDe(texto: string, inicio: number, fim: number) {
  const corteAntes = Math.max(0, inicio - 48);
  const corteDepois = Math.min(texto.length, fim + 72);
  return {
    antes: `${corteAntes > 0 ? "…" : ""}${texto.slice(corteAntes, inicio)}`,
    achado: texto.slice(inicio, fim),
    depois: `${texto.slice(fim, corteDepois)}${corteDepois < texto.length ? "…" : ""}`,
  };
}

/** Busca do guia (spec 017, decisão 4): títulos e texto, sem diferenciar acento e maiúscula, sem biblioteca. */
export function buscarNoGuia(consulta: string, capitulos: Capitulo[] = CAPITULOS): Resultado[] {
  const palavras = normalizar(consulta).split(/\s+/).filter(Boolean);
  if (palavras.length === 0) return [];

  const achados: (Resultado & { peso: number })[] = [];
  for (const unidade of unidades(capitulos)) {
    const tudo = normalizar([unidade.titulo, ...unidade.textos].join(" "));
    if (!palavras.every((palavra) => tudo.includes(palavra))) continue;

    const primeira = palavras[0];
    const noTitulo = posicaoEm(unidade.titulo, primeira);
    // Trecho do texto onde a palavra aparece; se ela só está no título, o trecho é o próprio título.
    const fonte = unidade.textos.find((texto) => posicaoEm(texto, primeira)) ?? unidade.titulo;
    const posicao = posicaoEm(fonte, primeira);
    achados.push({
      capituloId: unidade.capitulo.id,
      capituloNumero: unidade.capitulo.numero,
      capituloTitulo: unidade.capitulo.titulo,
      topicoId: unidade.topicoId,
      titulo: unidade.titulo,
      trecho: posicao ? trechoDe(fonte, posicao.inicio, posicao.fim) : { antes: fonte, achado: "", depois: "" },
      peso: noTitulo ? 0 : 1,
    });
  }

  return achados
    .sort((a, b) => a.peso - b.peso || a.capituloNumero - b.capituloNumero)
    .map((achado) => ({
      capituloId: achado.capituloId,
      capituloNumero: achado.capituloNumero,
      capituloTitulo: achado.capituloTitulo,
      topicoId: achado.topicoId,
      titulo: achado.titulo,
      trecho: achado.trecho,
    }));
}
