/*
 * RotaGuard Script (specs 023, 029 e 031): a página só conversa com o servidor local que a serviu (127.0.0.1, com token).
 * Consulta /estado várias vezes por segundo durante o teste, mostra o vídeo de /video.mjpg (a malha já vem desenhada
 * pelo Python) e manda as ações para /acao. Textos dinâmicos sempre por textContent, nunca innerHTML.
 * Spec 029: a tela responde perguntas. O servidor manda o painel pronto (estado.py, montar_painel): uma frase do agora
 * e, para cada medida, nome simples, valor com unidade (ou o que falta para medir), situação e "o que é". Esta página
 * só desenha, sempre com a mesma anatomia. Normal sem cor; cor só no que sai do normal; lima é medição, nunca estado.
 */
"use strict";

(() => {
  const TOKEN = document.querySelector('meta[name="rg-token"]').content;
  const ATIVAS = ["abrindo", "calibrando", "rodando"];
  const CONSULTA_RODANDO_MS = 150;
  const CONSULTA_PARADO_MS = 600;
  const NIVEIS = ["Normal", "Atenção", "Alto", "Crítico"];
  const MALHA_PADRAO = { discreta: "Discreta", completa: "Completa", desligada: "Só o rosto" };

  const numero1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const numero0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
  const $ = (id) => document.getElementById(id);

  let estado = null;
  let telaAtual = null;
  let falhas = 0;
  let consultando = false;
  let consultarDeNovo = false;
  let temporizador = null;
  let chaveCameras = "";
  let chaveEventos = "";
  let chaveResumo = "";
  let opcoesCarregadas = false;
  let semRostoDesde = null;
  let ultimoNivel = 0;
  let textosLegais = null;
  let abaLegal = 0;
  let quemAbriuLegal = null;
  let avisoTimer = null;
  let enderecoPreenchido = false;
  let trechoTocando = null;
  let animacaoTrecho = null;
  const cartoesDom = new Map();
  let detalhesAbertos = false;
  let assuntoAtual = "sono";
  let chaveAbas = "";

  const opcoes = { camera: "auto", celular: true, som: true, calibracao_rapida: true, camera_ir: "auto", cardio: true };
  let cameraEscolhida = "auto";
  let caminhoVideo = "";
  let videoManual = false;

  // ------------------------------------------------------------------ comunicação
  async function pedir(caminho, corpo) {
    const init = { headers: { "X-RotaGuard-Token": TOKEN }, cache: "no-store" };
    if (corpo) {
      init.method = "POST";
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(corpo);
    }
    const resposta = await fetch(caminho, init);
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) throw new Error(dados.erro || `Erro ${resposta.status}`);
    return dados;
  }

  async function agir(acao, extra = {}) {
    try {
      return await pedir("/acao", { acao, ...extra });
    } catch (erro) {
      avisar(erro.message);
      return null;
    } finally {
      consultar();
    }
  }

  async function consultar() {
    if (consultando) {
      consultarDeNovo = true;
      return;
    }
    consultando = true;
    clearTimeout(temporizador);
    try {
      const dados = await pedir("/estado");
      falhas = 0;
      $("sem-conexao").hidden = true;
      desenhar(dados);
    } catch (erro) {
      falhas += 1;
      if (falhas >= 4) $("sem-conexao").hidden = false;
    } finally {
      consultando = false;
      const ativo = estado && ATIVAS.includes(estado.fase);
      temporizador = setTimeout(consultar, consultarDeNovo ? 0 : ativo ? CONSULTA_RODANDO_MS : CONSULTA_PARADO_MS);
      consultarDeNovo = false;
    }
  }

  // ------------------------------------------------------------------ utilidades
  function avisar(texto) {
    const caixa = $("aviso");
    caixa.textContent = texto;
    caixa.hidden = false;
    clearTimeout(avisoTimer);
    avisoTimer = setTimeout(() => {
      caixa.hidden = true;
    }, 3200);
  }

  function trocar(elemento, valor) {
    const novo = valor == null ? "" : String(valor);
    if (elemento.textContent !== novo) elemento.textContent = novo;
  }

  function texto(id, valor) {
    trocar($(id), valor == null || valor === "" ? "" : valor);
  }

  function textoLivre(id, valor) {
    trocar($(id), valor);
  }

  function dois(n) {
    return String(n).padStart(2, "0");
  }

  function relogio(segundos) {
    const s = Math.max(0, Math.floor(segundos || 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return h ? `${h}:${dois(m)}:${dois(s % 60)}` : `${dois(m)}:${dois(s % 60)}`;
  }

  function duracaoTexto(segundos) {
    const s = Math.floor(segundos || 0);
    if (s < 60) return `${s} s`;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h) return `${h} h ${dois(m)} min`;
    return `${m} min ${dois(s % 60)} s`;
  }

  function porcento(valor, casas = 0) {
    if (valor == null) return null;
    return `${(casas ? numero1 : numero0).format(valor * 100)}%`;
  }

  function cssVar(nome) {
    return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  }

  function nomeArquivo(caminho) {
    return String(caminho || "").split(/[\\/]/).pop();
  }

  function criar(tag, classe, conteudo) {
    const elemento = document.createElement(tag);
    if (classe) elemento.className = classe;
    if (conteudo != null) elemento.textContent = conteudo;
    return elemento;
  }

  function prepararCanvas(canvas) {
    const largura = canvas.clientWidth;
    const altura = canvas.clientHeight;
    if (!largura || !altura) return null;
    const escala = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(largura * escala);
    const h = Math.round(altura * escala);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(escala, 0, 0, escala, 0, 0);
    ctx.clearRect(0, 0, largura, altura);
    return { ctx, w: largura, h: altura };
  }

  // Cor de um evento pelo nível dele (1 neutro, 2 atenção, 3 alto, 4 e 5 crítico).
  function corDoEvento(nivel) {
    if (nivel >= 4) return "--n3";
    if (nivel === 3) return "--n2";
    if (nivel === 2) return "--n1";
    return "--grafite";
  }

  function nivelDe(medida) {
    return medida.nivel == null ? "n" : String(medida.nivel);
  }

  // ------------------------------------------------------------------ telas
  function desenhar(dados) {
    estado = dados;
    const tela = dados.fase === "resumo" ? "resumo" : ATIVAS.includes(dados.fase) ? "teste" : "inicio";
    if (tela !== telaAtual) trocarTela(tela);
    if (tela === "inicio") desenharInicio(dados);
    else if (tela === "teste") desenharTeste(dados);
    else desenharResumo(dados);
  }

  function trocarTela(tela) {
    telaAtual = tela;
    // O teste é escuro (o vídeo no centro); o início e o relatório do fim são claros, para ler com calma.
    document.documentElement.dataset.tema = tela === "teste" ? "escuro" : "claro";
    $("tela-inicio").hidden = tela !== "inicio";
    $("tela-teste").hidden = tela !== "teste";
    $("tela-resumo").hidden = tela !== "resumo";
    const video = $("video");
    if (tela !== "teste" && detalhesAbertos) {
      detalhesAbertos = false;
      $("tela-teste").classList.remove("com-detalhes");
      $("detalhes").hidden = true;
      $("detalhes-nav").hidden = true;
      $("detalhes-botao").setAttribute("aria-expanded", "false");
      textoLivre("detalhes-botao-texto", "Ver mais detalhes");
    }
    if (tela === "teste") {
      chaveEventos = "";
      semRostoDesde = null;
      ultimoNivel = 0;
      ligarVideo();
    } else {
      video.removeAttribute("src");
    }
    if (tela === "resumo") {
      chaveResumo = "";
      fecharTrecho();
    }
    if (tela === "inicio") chaveCameras = "";
    window.scrollTo(0, 0);
  }

  function ligarVideo() {
    $("video").src = `/video.mjpg?t=${encodeURIComponent(TOKEN)}&n=${Date.now()}`;
  }

  // ------------------------------------------------------------------ início
  function desenharInicio(dados) {
    if (!opcoesCarregadas && dados.opcoes) {
      Object.assign(opcoes, dados.opcoes);
      cameraEscolhida = ["auto", "0", "1", "2", "3", "4"].includes(opcoes.camera) ? opcoes.camera : "video";
      if (cameraEscolhida === "video") caminhoVideo = opcoes.camera;
      opcoesCarregadas = true;
      $("op-celular").checked = opcoes.celular;
      $("op-cardio").checked = opcoes.cardio;
      $("op-som").checked = opcoes.som;
      $("op-calibracao").checked = opcoes.calibracao_rapida;
      marcarSegmentado($("op-ir"), opcoes.camera_ir);
    }
    texto("pasta-dados", dados.pasta);
    desenharCentral(dados.central);
    texto("versao-inicio", `RotaGuard Script ${dados.versao}. Protótipo em validação, não é diagnóstico.`);
    texto("compilacao-inicio", dados.compilacao || "");
    desenharCameras(dados.cameras);

    const erro = dados.fase === "erro" ? dados.erro : null;
    $("erro-inicio").hidden = !erro;
    if (erro) {
      texto("erro-titulo", erro.titulo);
      texto("erro-detalhe", erro.detalhe);
      const lista = $("erro-dicas");
      if (lista.dataset.chave !== erro.titulo) {
        lista.dataset.chave = erro.titulo;
        lista.replaceChildren(...(erro.dicas || []).map((dica) => criar("li", "", dica)));
      }
    }
    const semVideo = cameraEscolhida === "video" && !caminhoVideo.trim();
    $("iniciar").disabled = semVideo;
    $("iniciar").title = semVideo ? "Escolha o arquivo de vídeo" : "";
  }

  function desenharCameras(cameras) {
    const procurando = cameras.procurando;
    const total = cameras.lista.length;
    textoLivre("cameras-status", procurando ? "Procurando câmeras neste computador…" :
      total ? `${total} ${total === 1 ? "câmera encontrada" : "câmeras encontradas"}.` :
        "Nenhuma câmera encontrada. Use a automática para tentar de novo ou um vídeo gravado.");
    $("procurar-cameras").hidden = procurando;
    const chave = JSON.stringify([cameras, cameraEscolhida, caminhoVideo, videoManual]);
    if (chave === chaveCameras) return;
    chaveCameras = chave;

    const lista = $("lista-cameras");
    const itens = [escolha("auto", "Automática", "Primeira câmera livre", null)];
    for (const camera of cameras.lista) {
      const ocupada = camera.situacao === "ocupada";
      itens.push(escolha(camera.valor, camera.nome, ocupada ? "Em uso por outro programa" : "Livre", camera.situacao));
    }
    if (procurando && !total) itens.push(criar("div", "choice-skeleton"));
    const descricaoVideo = caminhoVideo ? `${nomeArquivo(caminhoVideo)} · trocar` : "Escolher um arquivo";
    itens.push(escolha("video", "Vídeo gravado", descricaoVideo, null));
    lista.replaceChildren(...itens);
    $("video-escolha").hidden = !(cameraEscolhida === "video" && videoManual);
  }

  function escolha(valor, nome, descricao, situacao) {
    const botao = criar("button", "choice");
    botao.type = "button";
    botao.setAttribute("role", "radio");
    botao.setAttribute("aria-checked", String(cameraEscolhida === valor));
    botao.dataset.camera = valor;
    botao.append(criar("span", "choice-mark"), criar("span", "choice-name", nome));
    const desc = criar("span", "choice-desc");
    if (situacao) {
      const ponto = criar("span", "status-dot");
      ponto.dataset.situacao = situacao;
      desc.append(ponto);
    }
    desc.append(document.createTextNode(descricao));
    botao.append(desc);
    return botao;
  }

  async function escolherCamera(valor) {
    if (valor === "video") {
      const resposta = await agir("escolher_video");
      if (!resposta) return;
      if (resposta.manual) {
        videoManual = true;
        cameraEscolhida = "video";
        setTimeout(() => $("caminho-video").focus(), 50);
      } else if (resposta.caminho) {
        caminhoVideo = resposta.caminho;
        videoManual = false;
        cameraEscolhida = "video";
      }
    } else {
      cameraEscolhida = valor;
    }
    chaveCameras = "";
    if (estado) desenharInicio(estado);
  }

  function iniciar() {
    const camera = cameraEscolhida === "video" ? caminhoVideo.trim() : cameraEscolhida;
    if (!camera) {
      avisar("Escolha o arquivo de vídeo.");
      return;
    }
    Object.assign(opcoes, {
      camera,
      celular: $("op-celular").checked,
      cardio: $("op-cardio").checked,
      som: $("op-som").checked,
      calibracao_rapida: $("op-calibracao").checked,
    });
    agir("iniciar", { opcoes });
  }

  // ------------------------------------------------------------------ enviar para a empresa (spec 026)
  function textoPendentes(pendentes) {
    if (!pendentes) return "";
    const partes = [];
    if (pendentes.trechos) partes.push(`${pendentes.trechos} ${pendentes.trechos === 1 ? "trecho" : "trechos"}`);
    if (pendentes.eventos) partes.push(`${pendentes.eventos} ${pendentes.eventos === 1 ? "evento" : "eventos"}`);
    if (pendentes.sessoes) partes.push(`${pendentes.sessoes} ${pendentes.sessoes === 1 ? "teste" : "testes"}`);
    return partes.length ? `${partes.join(", ")} na fila` : "";
  }

  function desenharCentral(central) {
    if (!central) return;
    $("central-desconectado").hidden = central.conectado;
    $("central-conectado").hidden = !central.conectado;
    if (!enderecoPreenchido && central.endereco) {
      $("central-endereco").value = central.endereco;
      enderecoPreenchido = true;
    }
    if (!central.conectado) {
      const erro = $("central-erro");
      if (central.aviso && erro.hidden) {
        erro.textContent = central.aviso;
        erro.hidden = false;
      }
      return;
    }
    textoLivre("central-empresa", central.empresa || "empresa");
    const interruptor = $("central-enviar");
    if (document.activeElement !== interruptor) interruptor.checked = !!central.enviar;
    let situacao = central.enviar ? central.situacao_texto || "" : "Desligado: nada sai deste computador";
    const fila = central.enviar ? textoPendentes(central.pendentes) : "";
    if (fila) situacao += ` · ${fila}`;
    textoLivre("central-situacao", situacao);
  }

  async function conectar() {
    const erro = $("central-erro");
    erro.hidden = true;
    const botao = $("central-conectar");
    botao.disabled = true;
    textoLivre("central-conectar", "Conectando…");
    try {
      const resposta = await pedir("/acao", { acao: "conectar", codigo: $("central-codigo").value,
        endereco: $("central-endereco").value });
      $("central-codigo").value = "";
      avisar(`Conectado a ${resposta.central.empresa || "empresa"}.`);
    } catch (falha) {
      erro.textContent = falha.message;
      erro.hidden = false;
    } finally {
      botao.disabled = false;
      textoLivre("central-conectar", "Conectar");
      consultar();
    }
  }

  function marcarSegmentado(grupo, valor) {
    for (const botao of grupo.querySelectorAll("button")) {
      botao.setAttribute("aria-checked", String(botao.dataset.valor === valor));
    }
  }

  // ------------------------------------------------------------------ teste
  function desenharTeste(dados) {
    const fase = dados.fase;
    const desempenho = dados.desempenho || {};
    $("ao-vivo").dataset.ativo = fase === "rodando" || fase === "calibrando" ? "sim" : "nao";
    textoLivre("ao-vivo-texto", fase === "abrindo" ? "Abrindo" : dados.espelhar ? "Ao vivo" : "Vídeo gravado");
    textoLivre("relogio", relogio(dados.sessao ? dados.sessao.duracao_s : 0));
    textoLivre("camera-nome", dados.sessao && dados.sessao.camera);
    $("tag-ir").hidden = !(dados.rosto && dados.rosto.infravermelho);
    marcarSegmentado($("malha"), dados.malha);
    const semPontos = !!(dados.rosto && dados.rosto.pontos_disponiveis === false);
    $("malha").title = semPontos ? "Malha indisponível neste modo de câmera: só os olhos são marcados" :
      "Malha do rosto (tecla M)";
    $("malha").classList.toggle("indisponivel", semPontos);
    $("botao-som").setAttribute("aria-pressed", String(dados.som));
    textoLivre("som-texto", dados.som ? "Som ligado" : "Som desligado");

    const quadro = $("quadro-video");
    const palco = quadro.parentElement;
    quadro.classList.toggle("espelhado", !!dados.espelhar);
    const video = $("video");
    const temImagem = video.naturalWidth > 0 && fase !== "abrindo";
    if (temImagem) {
      const proporcao = video.naturalWidth / video.naturalHeight;
      if (Math.abs(proporcao - Number(palco.dataset.proporcao || 0)) > 0.01) {
        palco.dataset.proporcao = String(proporcao);
        palco.style.setProperty("--ar", `${video.naturalWidth} / ${video.naturalHeight}`);
        palco.style.setProperty("--arn", String(proporcao));
      }
    }
    $("video-carregando").hidden = temImagem;
    texto("etapa", fase === "abrindo" ? dados.etapa || "Preparando o teste" : "Esperando a primeira imagem");

    const painel = dados.painel;
    const nivel = painel ? painel.agora.nivel : 0;
    quadro.dataset.nivel = String(nivel);
    if (nivel >= 2 && nivel > ultimoNivel) {
      quadro.classList.remove("subiu");
      void quadro.offsetWidth;
      quadro.classList.add("subiu");
    }
    ultimoNivel = nivel;

    const rosto = dados.rosto || {};
    const semRosto = !!(dados.rosto && !rosto.encontrado);
    if (semRosto && semRostoDesde == null) semRostoDesde = performance.now();
    if (!semRosto) semRostoDesde = null;
    const maoNaFrente = !!rosto.mao_na_frente;
    $("sem-rosto").hidden = !((semRosto && temImagem && performance.now() - semRostoDesde > 1000) || maoNaFrente);
    textoLivre("sem-rosto-titulo", maoNaFrente ? "Mão na frente do rosto" : "Procurando o rosto");
    textoLivre("sem-rosto-texto", maoNaFrente ? "As medidas do olho voltam quando a mão sair." :
      "Centralize o rosto na câmera, chegue mais perto e deixe a luz de frente.");

    desenharAgora(painel, dados.calibracao, dados);
    desenharCartoes(painel, dados);
    if (detalhesAbertos) desenharDetalhes(painel, dados);
    desenharLinhaDoTempo(dados);
    desenharEnvioDoTeste(dados);
  }

  function desenharEnvioDoTeste(dados) {
    const central = dados.central || {};
    $("gravando-tag").hidden = !dados.gravando_trecho;
    const etiqueta = $("envio-tag");
    etiqueta.hidden = !dados.enviando_sessao;
    // Com os selos de envio a barra de cima fica cheia: o nome da câmera sai (ele continua no resumo).
    $("camera-nome").hidden = !!(dados.enviando_sessao || dados.gravando_trecho);
    if (!dados.enviando_sessao) return;
    etiqueta.dataset.situacao = central.situacao || "";
    etiqueta.title = `Enviando para ${central.empresa || "a empresa"}`;
    textoLivre("envio-tag", central.situacao === "sem_conexao" || central.situacao === "limite" ? "Na fila" :
      central.situacao === "recusado" ? "Envio recusado" : "Enviando");
  }

  // A frase do agora é o único lugar do risco: uma frase, a situação em palavra e, quando houver, o recado ao motorista.
  function desenharAgora(painel, calibracao, dados) {
    const caixa = $("agora");
    if (!painel) {
      caixa.dataset.nivel = "0";
      textoLivre("agora-frase", dados.fase === "abrindo" ? dados.etapa || "Preparando o teste" :
        "Esperando a primeira imagem");
      textoLivre("agora-detalhe", "A detecção começa assim que a câmera mandar imagem.");
      const situacao = $("agora-situacao");
      situacao.dataset.nivel = "n";
      trocar(situacao, "Aguardando");
      $("agora-mensagem").hidden = true;
      $("agora-nota").hidden = true;
      $("calibracao").hidden = true;
      return;
    }
    const agora = painel.agora;
    caixa.dataset.nivel = String(agora.nivel);
    textoLivre("agora-frase", agora.frase);
    textoLivre("agora-detalhe", agora.detalhe);
    const situacao = $("agora-situacao");
    situacao.dataset.nivel = String(agora.nivel);
    trocar(situacao, agora.situacao);
    $("agora-mensagem").hidden = !agora.mensagem;
    textoLivre("agora-mensagem", agora.mensagem ? `Recado ao motorista: ${agora.mensagem}` : "");
    const nota = agora.nota || (dados.som === false && agora.nivel >= 2 ? "O som do alarme está desligado." : "");
    $("agora-nota").hidden = !nota;
    textoLivre("agora-nota", nota);

    const ativa = !!(calibracao && calibracao.ativa);
    $("calibracao").hidden = !ativa;
    if (ativa) {
      const progresso = calibracao.progresso || 0;
      texto("calibracao-valor", porcento(progresso));
      $("calibracao-barra").style.setProperty("width", `${Math.round(progresso * 100)}%`);
      const partes = [];
      if (calibracao.segundos != null && calibracao.minimo_s) {
        partes.push(`${numero0.format(calibracao.segundos)} s de ${numero0.format(calibracao.minimo_s)} s`);
      }
      if (calibracao.piscadas != null) {
        partes.push(`${calibracao.piscadas} ${calibracao.piscadas === 1 ? "piscada" : "piscadas"}`);
      }
      textoLivre("calibracao-texto", partes.length ? partes.join(" · ") : "Olhe para a câmera e pisque normalmente.");
    }
  }

  // ------------------------------------------------------------------ detalhes: um assunto por vez, cartões em grade
  // Pedido de 20/10, 2ª rodada ("os mais detalhes continuou tudo junto"): cada medida é um cartão pequeno com nome
  // curto, valor grande com unidade, a situação em palavra e UMA linha curta (medida.curta) no lugar do parágrafo.
  function criarCartaoDetalhe(medida) {
    const raiz = criar("li", "detail-card");
    const nome = criar("p", "dc-name");
    const valor = criar("p", "dc-value");
    const numero = criar("span", "dc-number");
    const unidade = criar("span", "dc-unit");
    valor.append(numero, unidade);
    const espera = criar("p", "dc-wait");
    const situacao = criar("span", "status-word");
    const principal = criar("div", "dc-main");
    principal.append(valor, espera, situacao);
    const normal = criar("p", "dc-normal");
    const linha = criar("p", "dc-line");
    raiz.append(nome, principal, normal, linha);
    raiz.partes = { nome, valor, numero, unidade, espera, situacao, normal, linha };
    atualizarCartaoDetalhe(raiz, medida);
    return raiz;
  }

  function atualizarCartaoDetalhe(raiz, medida) {
    const p = raiz.partes;
    raiz.dataset.medida = medida.id;
    raiz.dataset.nivel = nivelDe(medida);
    trocar(p.nome, medida.nome);
    const temValor = medida.valor != null;
    p.valor.hidden = !temValor;
    raiz.classList.toggle("esmaecido", temValor && !!medida.espera);
    // Resposta em palavras longa ("Início da tarde: horário de mais sono") fica menor que um número.
    raiz.classList.toggle("valor-texto", temValor && /[A-Za-zÀ-ú]/.test(medida.valor) && String(medida.valor).length > 14);
    trocar(p.numero, temValor ? medida.valor : "");
    trocar(p.unidade, temValor ? medida.unidade : "");
    p.espera.hidden = temValor;
    trocar(p.espera, temValor ? "" : medida.espera_curta || medida.espera || "");
    p.situacao.dataset.nivel = nivelDe(medida);
    trocar(p.situacao, medida.situacao);
    p.normal.hidden = !medida.seu_normal;
    trocar(p.normal, medida.seu_normal || "");
    trocar(p.linha, medida.curta || medida.o_que_e);
  }

  // Painel ao lado do vídeo (pedido de 20/10: "tudo muito junto e confuso"): três blocos com pouca coisa cada.
  // Sono: dois números grandes. Atenção na estrada: uma linha por pergunta. Coração: o pulso, a onda e a confiança
  // embaixo; enquanto mede, um anel com quanto falta. A explicação de cada número fica em "Ver mais detalhes".
  function criarNumero(medida) {
    const raiz = criar("div", "tile");
    const nome = criar("p", "tile-name");
    const valor = criar("p", "tile-value");
    const numero = criar("span", "tile-number");
    const unidade = criar("span", "tile-unit");
    valor.append(numero, unidade);
    const espera = criar("p", "tile-wait");
    const pe = criar("p", "tile-foot");
    const situacao = criar("span", "status-word");
    const normal = criar("span", "tile-normal");
    pe.append(situacao, normal);
    raiz.append(nome, valor, espera, pe);
    raiz.partes = { nome, valor, numero, unidade, espera, situacao, normal };
    atualizarNumero(raiz, medida);
    return raiz;
  }

  function atualizarNumero(raiz, medida) {
    const p = raiz.partes;
    raiz.dataset.medida = medida.id;
    raiz.dataset.nivel = nivelDe(medida);
    trocar(p.nome, medida.nome);
    const temValor = medida.valor != null;
    p.valor.hidden = !temValor;
    trocar(p.numero, temValor ? medida.valor : "");
    trocar(p.unidade, temValor ? medida.unidade : "");
    p.espera.hidden = temValor;
    trocar(p.espera, temValor ? "" : medida.espera_curta || medida.espera || "");
    p.situacao.dataset.nivel = nivelDe(medida);
    trocar(p.situacao, medida.situacao);
    p.normal.hidden = !medida.seu_normal;
    trocar(p.normal, medida.seu_normal || "");
  }

  function criarLinha(medida) {
    const raiz = criar("div", "line");
    const nome = criar("span", "line-name");
    const valor = criar("span", "line-value");
    const situacao = criar("span", "status-word");
    raiz.append(nome, valor, situacao);
    raiz.partes = { nome, valor, situacao };
    atualizarLinha(raiz, medida);
    return raiz;
  }

  function atualizarLinha(raiz, medida) {
    const p = raiz.partes;
    raiz.dataset.medida = medida.id;
    raiz.dataset.nivel = nivelDe(medida);
    trocar(p.nome, medida.nome);
    const temValor = medida.valor != null;
    raiz.classList.toggle("sem-valor", !temValor);
    const unidade = temValor && medida.unidade ? ` ${medida.unidade}` : "";
    trocar(p.valor, temValor ? `${medida.valor}${unidade}` : medida.espera_curta || medida.espera || "");
    // Normal não ganha palavra nem cor na linha (o valor já diz, ISA-101); o resto diz a situação.
    p.situacao.hidden = medida.nivel === 0;
    p.situacao.dataset.nivel = nivelDe(medida);
    trocar(p.situacao, medida.situacao);
  }

  function criarCoracao() {
    const raiz = criar("div", "heart");
    const leitura = criar("p", "heart-reading");
    const numero = criar("span", "heart-number");
    const unidade = criar("span", "heart-unit", "bpm");
    const qualidade = criar("span", "status-word heart-quality");
    leitura.append(numero, unidade, qualidade);
    const movimento = criar("p", "heart-move");

    // Anel de andamento (CSS, conic-gradient): enche com o progresso; sem progresso conhecido, gira devagar.
    const andamento = criar("div", "heart-progress");
    const anel = criar("span", "ring");
    anel.setAttribute("aria-hidden", "true");
    const textos = criar("div", "heart-progress-text");
    const titulo = criar("p", "heart-progress-title");
    const ultimo = criar("p", "heart-last");
    const motivo = criar("p", "heart-reason");
    textos.append(titulo, ultimo, motivo);
    andamento.append(anel, textos);

    const aviso = criar("p", "heart-note");
    const onda = criar("canvas", "chart chart-wave");
    onda.setAttribute("aria-hidden", "true");
    const confianca = criar("div", "heart-conf");
    const barra = criar("span", "conf-bar");
    const cheio = criar("span");
    barra.append(cheio);
    barra.setAttribute("aria-hidden", "true");
    const confTexto = criar("span", "conf-text");
    confianca.append(criar("span", "conf-label", "Confiança da leitura"), barra, confTexto);

    raiz.append(leitura, andamento, aviso, onda, movimento, confianca);
    raiz.partes = { leitura, numero, qualidade, movimento, andamento, anel, titulo, ultimo, motivo, aviso, onda, cheio,
      confTexto };
    return raiz;
  }

  function atualizarCoracao(raiz, dado) {
    const p = raiz.partes;
    const pulso = dado.principal;
    const medicao = dado.medicao || { ativa: false };
    const conf = (dado.medidas || []).find((m) => m.id === "confianca");
    const pronto = !medicao.ativa && pulso.valor != null;
    raiz.dataset.estado = medicao.ativa ? "medindo" : pronto ? "pronto" : "sem_leitura";

    p.leitura.hidden = !pronto;
    if (pronto) {
      trocar(p.numero, pulso.valor);
      p.qualidade.dataset.nivel = "n";
      trocar(p.qualidade, pulso.situacao);
    }
    // Com número e a pessoa se mexendo: o número continua e só uma nota pequena avisa (nunca pede para parar).
    const comNota = !!(pronto && dado.nota);
    raiz.classList.toggle("com-nota", comNota);
    p.movimento.hidden = !comNota;
    trocar(p.movimento, comNota ? dado.nota : "");

    p.andamento.hidden = !medicao.ativa;
    if (medicao.ativa) {
      const conhecido = medicao.progresso != null;
      p.andamento.classList.toggle("girando", !conhecido);
      const fracao = conhecido ? Math.max(0.04, Math.min(1, medicao.progresso)) : 0.25;
      p.anel.style.setProperty("--p", fracao.toFixed(3));
      trocar(p.titulo, medicao.texto);
      p.ultimo.hidden = !medicao.ultimo;
      trocar(p.ultimo, medicao.ultimo ? `último valor: ${medicao.ultimo} bpm` : "");
      p.motivo.hidden = !medicao.motivo;
      trocar(p.motivo, medicao.motivo || "");
    }

    // Sem medida em andamento e sem número (sem rosto, desligado, modo sem pontos): uma frase, nunca vazio.
    const semLeitura = !pronto && !medicao.ativa;
    p.aviso.hidden = !semLeitura;
    const ultimoTexto = medicao.ultimo ? ` Último valor: ${medicao.ultimo} bpm.` : "";
    trocar(p.aviso, semLeitura ? `${pulso.espera_curta || pulso.espera || pulso.situacao}.${ultimoTexto}`.replace("..", ".") :
      "");

    // A confiança vale para o número na tela: só aparece com ele (medindo, a barra fica vazia e diz que já vem).
    const temConfianca = pronto && !!(conf && conf.valor != null);
    const porcentagem = temConfianca ? Math.max(0, Math.min(100, Number(String(conf.valor).replace(",", ".")))) : 0;
    p.cheio.style.setProperty("width", `${porcentagem}%`);
    trocar(p.confTexto, temConfianca ? `${conf.valor}%` : medicao.ativa ? "vem com o número" : "sem leitura");
  }

  function criarCartao(dado) {
    const cartao = criar("article", "card");
    cartao.dataset.cartao = dado.id;
    const cabeca = criar("header", "card-head");
    const titulo = criar("h2", "card-title", dado.titulo);
    titulo.id = `cartao-${dado.id}`;
    cartao.setAttribute("aria-labelledby", titulo.id);
    const situacao = criar("span", "status-word");
    cabeca.append(titulo, situacao);
    cartao.append(cabeca);
    let corpo;
    if (dado.id === "sono") corpo = criar("div", "tiles");
    else if (dado.id === "coracao") corpo = criarCoracao();
    else corpo = criar("div", "lines");
    cartao.append(corpo);
    cartao.partes = { situacao, corpo };
    return cartao;
  }

  function atualizarItens(lugar, medidas, criarItem, atualizarItem) {
    const existentes = new Map([...lugar.children].map((item) => [item.dataset.medida, item]));
    const ordem = medidas.map((medida) => {
      const item = existentes.get(medida.id);
      if (!item) return criarItem(medida);
      atualizarItem(item, medida);
      return item;
    });
    const mudou = ordem.length !== lugar.children.length || ordem.some((item, i) => lugar.children[i] !== item);
    if (mudou) lugar.replaceChildren(...ordem);
  }

  function desenharCartoes(painel, dados) {
    const lugar = $("cartoes");
    if (!painel) {
      if (!lugar.querySelector(".card-wait")) {
        lugar.replaceChildren(criar("p", "card-wait", "As medidas aparecem com a primeira imagem do rosto."));
        cartoesDom.clear();
      }
      return;
    }
    const espera = lugar.querySelector(".card-wait");
    if (espera) espera.remove();
    for (const dado of painel.cartoes) {
      let cartao = cartoesDom.get(dado.id);
      if (!cartao) {
        cartao = criarCartao(dado);
        cartoesDom.set(dado.id, cartao);
        lugar.append(cartao);
      }
      cartao.dataset.nivel = String(dado.nivel);
      // A palavra do bloco só aparece fora do normal; o coração não tem nível (é estimativa).
      cartao.partes.situacao.hidden = dado.id === "coracao" || !dado.nivel;
      cartao.partes.situacao.dataset.nivel = String(dado.nivel);
      trocar(cartao.partes.situacao, dado.situacao);
      const medidas = [dado.principal, ...dado.medidas];
      if (dado.id === "sono") atualizarItens(cartao.partes.corpo, medidas, criarNumero, atualizarNumero);
      else if (dado.id === "coracao") {
        atualizarCoracao(cartao.partes.corpo, dado);
        const cardio = dados.rosto && dados.rosto.pontos_disponiveis === false ? { estado: "sem_pontos" } : dados.cardio || {};
        graficoOnda(cartao.partes.corpo.partes.onda, cardio.onda || [], cardio.estado);
      } else atualizarItens(cartao.partes.corpo, medidas, criarLinha, atualizarLinha);
    }
  }

  const NOMES_NIVEL = { 1: "atenção", 2: "alto", 3: "crítico" };

  function desenharAbas(assuntos) {
    const abas = $("detalhes-abas");
    const chave = assuntos.map((a) => `${a.id}:${a.nivel}`).join(",");
    if (chave !== chaveAbas) {
      chaveAbas = chave;
      abas.replaceChildren(...assuntos.map((assunto) => {
        const aba = criar("button", "details-tab");
        aba.type = "button";
        aba.id = `aba-${assunto.id}`;
        aba.dataset.assunto = assunto.id;
        aba.setAttribute("role", "tab");
        aba.setAttribute("aria-controls", "detalhes");
        aba.append(criar("span", "tab-name", assunto.titulo));
        // Assunto com algo fora do normal ganha a palavra do nível, para achar rápido onde olhar.
        if (assunto.nivel > 0) {
          const marca = criar("span", "status-word tab-level", NOMES_NIVEL[assunto.nivel]);
          marca.dataset.nivel = String(assunto.nivel);
          aba.append(marca);
        }
        return aba;
      }));
    }
    for (const aba of abas.children) {
      const escolhida = aba.dataset.assunto === assuntoAtual;
      aba.setAttribute("aria-selected", String(escolhida));
      aba.tabIndex = escolhida ? 0 : -1;
    }
  }

  function desenharDetalhes(painel, dados) {
    if (!painel || !painel.assuntos) return;
    const assuntos = painel.assuntos;
    if (!assuntos.some((a) => a.id === assuntoAtual)) assuntoAtual = assuntos[0].id;
    desenharAbas(assuntos);
    const assunto = assuntos.find((a) => a.id === assuntoAtual);
    $("detalhes").setAttribute("aria-labelledby", `aba-${assunto.id}`);
    textoLivre("assunto-titulo", assunto.titulo);
    textoLivre("assunto-descricao", assunto.descricao);
    atualizarItens($("assunto-medidas"), assunto.medidas, criarCartaoDetalhe, atualizarCartaoDetalhe);
    const figura = $("assunto-grafico");
    figura.hidden = !assunto.grafico;
    figura.dataset.tipo = assunto.grafico || "";
    if (assunto.grafico === "abertura") {
      textoLivre("assunto-grafico-titulo", "Abertura do olho nos últimos 60 s");
      textoLivre("assunto-grafico-nota", "Abaixo da linha tracejada (20%), o olho conta como fechado.");
      graficoAbertura($("assunto-grafico-tela"), dados.series ? dados.series.abertura : [], true);
    } else if (assunto.grafico === "pulso") {
      textoLivre("assunto-grafico-titulo", "Pulso nos últimos 2 min");
      textoLivre("assunto-grafico-nota", "Só leituras boas; a linha mostra se subiu ou desceu.");
      graficoTendencia($("assunto-grafico-tela"), (dados.cardio && dados.cardio.historico_bpm) || []);
    }
    $("assunto-nota").hidden = !assunto.nota;
    if (assunto.nota) textoLivre("assunto-nota", assunto.nota);
  }

  function escolherAssunto(id, focar) {
    assuntoAtual = id;
    $("detalhes").scrollTop = 0;
    if (estado && estado.painel) desenharDetalhes(estado.painel, estado);
    if (focar) {
      const aba = $(`aba-${id}`);
      if (aba) aba.focus();
    }
  }

  // Abre e fecha os detalhes: a camada cobre o palco e o vídeo fica pequeno no canto (a frase do agora e os blocos
  // continuam ao lado). Esc fecha os detalhes antes de encerrar o teste.
  function abrirDetalhes(abrir) {
    detalhesAbertos = abrir;
    $("tela-teste").classList.toggle("com-detalhes", abrir);
    $("detalhes").hidden = !abrir;
    $("detalhes-nav").hidden = !abrir;
    const botao = $("detalhes-botao");
    botao.setAttribute("aria-expanded", String(abrir));
    textoLivre("detalhes-botao-texto", abrir ? "Fechar detalhes" : "Ver mais detalhes");
    if (estado && telaAtual === "teste") desenharTeste(estado);
    if (abrir) {
      const aba = $(`aba-${assuntoAtual}`);
      if (aba) aba.focus();
    } else if (document.activeElement === document.body || !document.activeElement) {
      botao.focus();
    }
  }

  // ------------------------------------------------------------------ linha do tempo
  function linhaEvento(evento, novo) {
    const item = criar("li", novo ? "event novo" : "event");
    item.append(criar("span", "event-time", evento.hora));
    const marca = criar("span", "event-mark");
    marca.dataset.categoria = evento.categoria;
    marca.style.setProperty("--cor-evento", `var(${corDoEvento(evento.nivel)})`);
    marca.setAttribute("aria-hidden", "true");
    item.append(marca, criar("span", "event-name", evento.rotulo));
    item.append(criar("span", "event-extra", evento.duracao_s ? `${numero1.format(evento.duracao_s)} s` : ""));
    return item;
  }

  function desenharLinhaDoTempo(dados) {
    const eventos = dados.eventos || [];
    const chave = `${eventos.length}:${eventos.length ? eventos[0].t + eventos[0].tipo : ""}`;
    if (chave !== chaveEventos) {
      const tinhaAntes = chaveEventos !== "";
      chaveEventos = chave;
      $("eventos").replaceChildren(...eventos.map((evento, i) => linhaEvento(evento, tinhaAntes && i === 0)));
      $("eventos-vazio").hidden = eventos.length > 0;
      $("eventos").hidden = eventos.length === 0;
    }
    const alertas = eventos.filter((evento) => evento.categoria !== "sistema").length;
    const avisos = eventos.length - alertas;
    const partes = [];
    if (alertas) partes.push(`${alertas} ${alertas === 1 ? "alerta" : "alertas"}`);
    if (avisos) partes.push(`${avisos} ${avisos === 1 ? "aviso do sistema" : "avisos do sistema"}`);
    let total = partes.length ? partes.join(" e ") : "Nenhum alerta ainda";
    if (eventos.length && dados.sessao) {
      total += ` · último há ${duracaoTexto(Math.max(0, dados.sessao.duracao_s - eventos[0].t))}`;
    }
    textoLivre("eventos-total", total);
    trilha($("trilha"), eventos, dados.sessao ? dados.sessao.duracao_s : 0, true);
  }

  // ------------------------------------------------------------------ gráficos (todos com título dizendo o que mostram)
  function graficoAbertura(canvas, valores, comEscala) {
    if (!canvas) return;
    const area = prepararCanvas(canvas);
    if (!area) return;
    const { ctx, w, h } = area;
    const topo = comEscala ? 7 : 4;
    const base = comEscala ? h - 20 : h - 4;
    const yDe = (v) => base - Math.min(Math.max(v, 0), 1) * (base - topo);
    ctx.fillStyle = cssVar("--apagado");
    ctx.font = "11px " + cssVar("--fonte");
    ctx.textBaseline = "middle";
    const esquerda = comEscala ? 82 : 50;
    if (comEscala) {
      ctx.fillText("100% aberto", 0, yDe(1));
      ctx.fillText("20% fechado", 0, yDe(0.2));
      if (yDe(0) - yDe(0.2) >= 15) ctx.fillText("0%", 0, yDe(0));
      ctx.strokeStyle = cssVar("--fio");
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(esquerda, yDe(1));
      ctx.lineTo(w, yDe(1));
      ctx.moveTo(esquerda, yDe(0));
      ctx.lineTo(w, yDe(0));
      ctx.stroke();
      ctx.textBaseline = "alphabetic";
      ctx.fillText("60 s atrás", esquerda, h - 3);
      ctx.textAlign = "center";
      ctx.fillText("30 s", esquerda + (w - esquerda) / 2, h - 3);
      ctx.textAlign = "right";
      ctx.fillText("agora", w, h - 3);
      ctx.textAlign = "left";
    } else {
      ctx.fillText("aberto", 0, yDe(1) + 5);
      ctx.fillText("fechado", 0, yDe(0.2) + 7);
    }
    ctx.strokeStyle = cssVar("--fio-forte");
    ctx.setLineDash([3, 4]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(esquerda, yDe(0.2));
    ctx.lineTo(w, yDe(0.2));
    ctx.stroke();
    ctx.setLineDash([]);
    if (!valores || !valores.length) return;
    const n = valores.length;
    const xDe = (i) => esquerda + (i / (n - 1)) * (w - esquerda);
    ctx.lineWidth = 1.4;
    ctx.lineJoin = "round";
    ctx.strokeStyle = cssVar("--lima");
    ctx.beginPath();
    let aberto = false;
    for (let i = 0; i < n; i += 1) {
      const v = valores[i];
      if (v == null) {
        aberto = false;
        continue;
      }
      if (!aberto) ctx.moveTo(xDe(i), yDe(v));
      else ctx.lineTo(xDe(i), yDe(v));
      aberto = true;
    }
    ctx.stroke();
  }

  function graficoOnda(canvas, onda, estadoCardio) {
    if (!canvas) return;
    const area = prepararCanvas(canvas);
    if (!area) return;
    const { ctx, w, h } = area;
    const meio = h / 2;
    ctx.strokeStyle = cssVar("--fio");
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, meio);
    ctx.lineTo(w, meio);
    ctx.stroke();
    if (!onda.length || ["desligado", "sem_rosto", "sem_pontos"].includes(estadoCardio)) return;
    const pronto = estadoCardio === "pronto";
    const n = onda.length;
    ctx.save();
    ctx.strokeStyle = pronto ? cssVar("--lima") : cssVar("--grafite");
    ctx.globalAlpha = pronto ? 1 : 0.55;
    if (estadoCardio === "sinal_fraco" || estadoCardio === "movimento") ctx.setLineDash([4, 3]);
    ctx.lineWidth = 1.5;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    for (let i = 0; i < n; i += 1) {
      const x = n === 1 ? w : (i / (n - 1)) * w;
      const y = meio - Math.max(-1, Math.min(1, onda[i])) * (meio - 3);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();
  }

  function graficoTendencia(canvas, valores) {
    const area = prepararCanvas(canvas);
    if (!area) return;
    const { ctx, w, h } = area;
    const pontos = valores.filter((v) => v != null);
    if (pontos.length < 2) {
      ctx.strokeStyle = cssVar("--fio-forte");
      ctx.setLineDash([2, 3]);
      ctx.beginPath();
      ctx.moveTo(0, h / 2);
      ctx.lineTo(w, h / 2);
      ctx.stroke();
      ctx.setLineDash([]);
      return;
    }
    let menor = Math.min(...pontos);
    let maior = Math.max(...pontos);
    if (maior - menor < 6) {
      const meio = (maior + menor) / 2;
      menor = meio - 3;
      maior = meio + 3;
    }
    const direita = 46;
    const n = pontos.length;
    const yDe = (v) => h - 4 - ((v - menor) / (maior - menor)) * (h - 8);
    ctx.fillStyle = cssVar("--apagado");
    ctx.font = "10.5px " + cssVar("--fonte");
    ctx.textBaseline = "middle";
    ctx.fillText(`${numero0.format(maior)} bpm`, w - direita + 6, 6);
    ctx.fillText(`${numero0.format(menor)} bpm`, w - direita + 6, h - 6);
    ctx.strokeStyle = cssVar("--lima");
    ctx.lineWidth = 1.3;
    ctx.lineJoin = "round";
    ctx.beginPath();
    pontos.forEach((v, i) => {
      const x = (i / (n - 1)) * (w - direita);
      if (i === 0) ctx.moveTo(x, yDe(v));
      else ctx.lineTo(x, yDe(v));
    });
    ctx.stroke();
  }

  function marcaNaTrilha(ctx, categoria, x, y, tamanho) {
    ctx.beginPath();
    if (categoria === "sonolencia") {
      ctx.arc(x, y, tamanho / 2, 0, Math.PI * 2);
      ctx.fill();
    } else if (categoria === "celular") {
      ctx.fillRect(x - tamanho / 2, y - tamanho / 2, tamanho, tamanho);
    } else if (categoria === "jornada" || categoria === "ativacao") {
      ctx.moveTo(x, y - tamanho / 2 - 1);
      ctx.lineTo(x + tamanho / 2 + 1, y);
      ctx.lineTo(x, y + tamanho / 2 + 1);
      ctx.lineTo(x - tamanho / 2 - 1, y);
      ctx.fill();
    } else {
      ctx.fillRect(x - 1, y - tamanho / 2 - 1, 2, tamanho + 2);
    }
  }

  function trilha(canvas, eventos, duracao, agoraMarcado) {
    const area = prepararCanvas(canvas);
    if (!area) return;
    const { ctx, w, h } = area;
    const total = Math.max(duracao || 0, 30);
    const meio = 9;
    ctx.strokeStyle = cssVar("--fio-forte");
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, meio);
    ctx.lineTo(w, meio);
    ctx.stroke();
    ctx.fillStyle = cssVar("--grafite");
    ctx.font = "10.5px " + cssVar("--fonte");
    ctx.textBaseline = "alphabetic";
    const passo = total > 1800 ? 600 : total > 600 ? 300 : total > 180 ? 60 : 30;
    ctx.fillText("início", 0, meio + 15);
    for (let s = passo; s < total; s += passo) {
      const x = (s / total) * w;
      ctx.fillRect(x, meio - 3, 1, 6);
      const rotulo = s >= 60 ? `${Math.round(s / 60)} min` : `${s} s`;
      if (x > 34 && x < w - 40) ctx.fillText(rotulo, x + 3, meio + 15);
    }
    for (const evento of [...eventos].reverse()) {
      const x = Math.min(w - 4, Math.max(4, (evento.t / total) * w));
      ctx.fillStyle = cssVar(corDoEvento(evento.nivel));
      marcaNaTrilha(ctx, evento.categoria, x, meio, 8);
    }
    if (agoraMarcado) {
      ctx.fillStyle = cssVar("--tinta");
      const agora = Math.min(w - 3, ((duracao || 0) / total) * w);
      ctx.fillRect(agora - 1, meio - 6, 2, 12);
      if (agora > w - 40) ctx.fillText("agora", Math.max(0, agora - 34), meio + 15);
    } else {
      ctx.fillText("fim", w - 18, meio + 15);
    }
  }

  // ------------------------------------------------------------------ resumo: relatório
  function desenharResumo(dados) {
    const resumo = dados.resumo;
    if (!resumo) return;
    const chave = JSON.stringify([resumo.inicio, resumo.fim, dados.salvo, dados.aviso,
      dados.central && dados.central.pendentes]);
    if (chave === chaveResumo) return;
    chaveResumo = chave;

    const inicio = resumo.inicio ? new Date(resumo.inicio) : null;
    const fim = resumo.fim ? new Date(resumo.fim) : null;
    const hora = (data) => data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    const partes = [];
    if (inicio) partes.push(inicio.toLocaleDateString("pt-BR"));
    if (inicio && fim) partes.push(`${hora(inicio)} às ${hora(fim)}`);
    if (resumo.camera) partes.push(resumo.camera);
    $("resumo-quando").textContent = partes.join(" · ");
    texto("resumo-frase", resumo.frase || `Teste de ${duracaoTexto(resumo.duracao_s)}.`);
    const meta = [];
    if (inicio && fim) meta.push(`${inicio.toLocaleDateString("pt-BR")}, das ${hora(inicio)} às ${hora(fim)}`);
    meta.push(`duração ${duracaoTexto(resumo.duracao_s)}`);
    if (resumo.camera) meta.push(resumo.camera);
    textoLivre("resumo-meta", meta.join(" · "));
    $("resumo-aviso").hidden = !dados.aviso;
    if (dados.aviso) texto("resumo-aviso", dados.aviso);
    $("resumo-salvo").hidden = !dados.salvo;
    if (dados.salvo) texto("resumo-salvo", `Resumo salvo em ${dados.salvo.pasta} (JSON e CSV).`);
    $("salvar-resumo").textContent = dados.salvo ? "Salvo" : "Salvar resumo (JSON e CSV)";
    $("salvar-resumo").disabled = !!dados.salvo;

    desenharNiveis(resumo.tempo_por_nivel_s || {});
    desenharAlertas(resumo, dados.central || {});
    desenharComoEstava(resumo.como_estava || []);
    desenharTecnico(resumo, dados.central || {});
    requestAnimationFrame(() => trilhaDoResumo(resumo));
  }

  function trilhaDoResumo(resumo) {
    const alertas = (resumo.alertas || []).map((alerta) => ({ ...alerta,
      categoria: alerta.grupo === "sono" ? "sonolencia" : alerta.grupo === "celular" || alerta.grupo === "distracao" ?
        "celular" : "jornada" }));
    trilha($("r-trilha"), alertas, resumo.duracao_s, false);
  }

  function desenharNiveis(niveis) {
    const chaves = ["normal", "atencao", "alto", "critico"];
    const soma = chaves.reduce((total, k) => total + (niveis[k] || 0), 0) || 1;
    $("r-niveis-barra").replaceChildren(...chaves.map((k, i) => {
      const parte = criar("span");
      parte.style.setProperty("width", `${((niveis[k] || 0) / soma) * 100}%`);
      parte.style.setProperty("background", `var(--n${i})`);
      return parte;
    }));
    $("r-niveis").replaceChildren(...chaves.map((k, i) => {
      const linha = criar("div");
      const ponto = criar("span", "dot");
      ponto.style.setProperty("background", `var(--n${i})`);
      const parte = Math.round(((niveis[k] || 0) / soma) * 100);
      linha.append(ponto, criar("dt", "", NIVEIS[i]), criar("dd", "", `${relogio(niveis[k] || 0)} (${parte}%)`));
      return linha;
    }));
  }

  function celulaSituacao(situacao, nivel) {
    const celula = criar("td");
    const palavra = criar("span", "status-word", situacao);
    palavra.dataset.nivel = nivel == null ? "n" : String(nivel);
    celula.append(palavra);
    return celula;
  }

  function desenharAlertas(resumo, central) {
    const trechos = resumo.trechos || [];
    const porUid = new Map(trechos.map((trecho) => [trecho.uid, trecho]));
    const usados = new Set();
    const linhas = (resumo.alertas || []).map((alerta) => {
      const linha = criar("tr");
      linha.append(criar("td", "mono", alerta.hora), criar("td", "", alerta.rotulo),
        criar("td", "", alerta.duracao_s ? `${numero1.format(alerta.duracao_s)} s` : "instantâneo"),
        celulaSituacao(alerta.situacao, alerta.cor));
      const video = criar("td");
      const trecho = alerta.trecho_uid ? porUid.get(alerta.trecho_uid) : null;
      if (trecho) {
        usados.add(trecho.uid);
        video.append(botaoVideo(trecho));
      } else {
        video.append(criar("span", "muted small", "sem vídeo"));
      }
      linha.append(video);
      return linha;
    });
    for (const trecho of trechos) {
      if (usados.has(trecho.uid)) continue;
      const linha = criar("tr");
      linha.append(criar("td", "mono", new Date(trecho.inicio).toLocaleTimeString("pt-BR")),
        criar("td", "", trecho.rotulo), criar("td", "", `${numero0.format(trecho.duracao_s)} s de vídeo`),
        celulaSituacao("Atenção", 1));
      const video = criar("td");
      video.append(botaoVideo(trecho));
      linha.append(video);
      linhas.push(linha);
    }
    $("r-alertas-corpo").replaceChildren(...linhas);
    $("r-alertas").hidden = linhas.length === 0;
    $("r-alertas-vazio").hidden = linhas.length > 0;
    const fila = central.conectado && central.pendentes ? central.pendentes.trechos : 0;
    textoLivre("r-trechos-envio", !trechos.length ? "" : !central.conectado ? "Vídeo guardado só neste computador." :
      fila ? `${fila} na fila para ${central.empresa}.` : `Enviado para ${central.empresa}.`);
  }

  function botaoVideo(trecho) {
    const botao = criar("button", "btn btn-small", "Ver vídeo");
    botao.type = "button";
    botao.dataset.trecho = trecho.uid;
    botao.setAttribute("aria-label", `Ver vídeo: ${trecho.rotulo}`);
    return botao;
  }

  function desenharComoEstava(linhas) {
    $("r-como").replaceChildren(...linhas.map((linha) => {
      const tr = criar("tr");
      const medida = criar("td", "how-name");
      medida.append(criar("span", "how-title", linha.nome), criar("span", "how-what", linha.o_que_e));
      if (linha.tecnico) medida.append(criar("span", "m-tech", linha.tecnico));
      const valor = criar("td", "how-value");
      if (linha.valor != null) {
        valor.append(criar("span", "m-number", linha.valor));
        if (linha.unidade) valor.append(criar("span", "m-unit", ` ${linha.unidade}`));
      } else {
        valor.append(criar("span", "m-wait-inline", linha.espera || "não medido"));
      }
      if (linha.seu_normal) valor.append(criar("span", "m-normal", linha.seu_normal));
      tr.append(medida, valor, criar("td", "how-range", linha.faixa_normal), celulaSituacao(linha.situacao, linha.nivel));
      return tr;
    }));
  }

  function desenharTecnico(resumo, central) {
    const fc = resumo.frequencia_cardiaca || {};
    const base = resumo.base || {};
    const calibracao = [];
    if (base.perclos_base != null) calibracao.push(`olho fechado ${numero1.format(base.perclos_base * 100)}% do tempo`);
    if (base.duracao_base_ms != null) calibracao.push(`piscada de ${numero0.format(base.duracao_base_ms)} ms`);
    const trechos = resumo.trechos || [];
    const itens = [
      ["Duração", `${relogio(resumo.duracao_s)} (${duracaoTexto(resumo.duracao_s)})`],
      ["Início e fim", resumo.inicio && resumo.fim ?
        `${new Date(resumo.inicio).toLocaleString("pt-BR")} até ${new Date(resumo.fim).toLocaleTimeString("pt-BR")}` : ""],
      ["Câmera", resumo.camera || ""],
      ["Versão do programa", resumo.versao || ""],
      ["Imagens analisadas", resumo.quadros != null ? numero0.format(resumo.quadros) : ""],
      ["Imagens por segundo (média)", resumo.fps_medio != null ? numero0.format(resumo.fps_medio) : "não medido"],
      ["Seu normal na calibração", calibracao.length ? calibracao.join(" · ") : "a calibração não terminou neste teste"],
      ["Piscadas contadas", `${resumo.piscadas ?? 0}`],
      ["Pulso (estimativa)", fc.media != null ?
        `média ${numero0.format(fc.media)} bpm, de ${numero0.format(fc.minima)} a ${numero0.format(fc.maxima)}, ` +
        `${fc.leituras} leituras. ${fc.observacao || ""}` : "sem leitura estável neste teste"],
      ["Eventos, com os avisos do sistema", `${resumo.total_eventos ?? 0}`],
      ["Vídeos gravados", trechos.length ? `${trechos.length} (${trechos[0].formato})` + (central.conectado ?
        `, para ${central.empresa}` : ", só neste computador") : "nenhum (só com o computador conectado a uma empresa)"],
    ];
    $("r-tecnico").replaceChildren(...itens.filter(([, valor]) => valor !== "").map(([rotulo, valor]) => {
      const bloco = criar("div");
      bloco.append(criar("dt", "", rotulo), criar("dd", "", valor));
      return bloco;
    }));
    const tipos = resumo.eventos_por_tipo_lista || [];
    $("r-tipos").replaceChildren(...tipos.map((tipo) => {
      const linha = criar("li", "type-row");
      const marca = criar("span", "event-mark");
      marca.dataset.categoria = tipo.categoria;
      marca.setAttribute("aria-hidden", "true");
      linha.append(marca, criar("span", "type-name", tipo.rotulo), criar("span", "type-count", tipo.quantidade));
      return linha;
    }));
    $("r-tipos-vazio").hidden = tipos.length > 0;
    const eventos = resumo.eventos || [];
    $("r-linha").replaceChildren(...eventos.map((evento) => linhaEvento(evento, false)));
    $("r-linha-vazio").hidden = eventos.length > 0;
  }

  function fecharTrecho() {
    trechoTocando = null;
    cancelAnimationFrame(animacaoTrecho);
    const video = $("r-player");
    video.pause();
    video.removeAttribute("src");
    $("r-player-bloco").hidden = true;
  }

  async function tocarTrecho(uid) {
    const trecho = ((estado && estado.resumo && estado.resumo.trechos) || []).find((t) => t.uid === uid);
    if (!trecho) return;
    trechoTocando = uid;
    cancelAnimationFrame(animacaoTrecho);
    const bloco = $("r-player-bloco");
    bloco.hidden = false;
    const video = $("r-player");
    const tela = $("r-player-canvas");
    const sufixo = `t=${encodeURIComponent(TOKEN)}`;
    textoLivre("r-player-legenda", `${trecho.rotulo} · ${new Date(trecho.inicio).toLocaleString("pt-BR")} · ` +
      "o rosto como a câmera viu, com a hora e o tipo na faixa de baixo");
    bloco.scrollIntoView({ block: "nearest", behavior: "smooth" });
    if (trecho.formato !== "rgclip") {
      tela.hidden = true;
      video.hidden = false;
      video.src = `/trecho/${uid}?${sufixo}`;
      video.play().catch(() => {});
      return;
    }
    // .rgclip: quadros JPEG tocados num canvas no ritmo do índice
    video.pause();
    video.removeAttribute("src");
    video.hidden = true;
    tela.hidden = false;
    const indice = await pedir(`/trecho/${uid}/indice`);
    tela.width = indice.largura || 640;
    tela.height = indice.altura || 480;
    const ctx = tela.getContext("2d");
    const imagens = indice.quadros.map((_, n) => {
      const imagem = new Image();
      imagem.src = `/trecho/${uid}/quadro/${n}?${sufixo}`;
      return imagem;
    });
    const comeco = performance.now();
    const passo = () => {
      if (trechoTocando !== uid) return;
      const segundos = (performance.now() - comeco) / 1000;
      let n = indice.quadros.findIndex((quadro) => quadro.t > segundos) - 1;
      if (n < 0) n = segundos > 0 ? indice.quadros.length - 1 : 0;
      if (imagens[n] && imagens[n].complete) ctx.drawImage(imagens[n], 0, 0, tela.width, tela.height);
      if (segundos <= indice.quadros[indice.quadros.length - 1].t) animacaoTrecho = requestAnimationFrame(passo);
    };
    animacaoTrecho = requestAnimationFrame(passo);
  }

  // ------------------------------------------------------------------ textos legais
  async function abrirLegal() {
    quemAbriuLegal = document.activeElement;
    $("legal").hidden = false;
    if (!textosLegais) {
      try {
        textosLegais = await pedir("/legal");
      } catch (erro) {
        $("legal-texto").textContent = "Não foi possível carregar os textos.";
        return;
      }
    }
    texto("compilacao-legal", textosLegais.compilacao || (estado && estado.compilacao) || "");
    const abas = $("legal-abas");
    abas.replaceChildren(...textosLegais.secoes.map((secao, indice) => {
      const botao = criar("button", "", secao.titulo);
      botao.type = "button";
      botao.setAttribute("role", "tab");
      botao.dataset.indice = String(indice);
      return botao;
    }));
    mostrarAba(abaLegal);
    abas.querySelector("button").focus();
  }

  function mostrarAba(indice) {
    abaLegal = indice;
    for (const botao of $("legal-abas").querySelectorAll("button")) {
      botao.setAttribute("aria-selected", String(Number(botao.dataset.indice) === indice));
      botao.tabIndex = Number(botao.dataset.indice) === indice ? 0 : -1;
    }
    const caixa = $("legal-texto");
    caixa.textContent = textosLegais.secoes[indice].texto;
    caixa.scrollTop = 0;
  }

  function fecharLegal() {
    $("legal").hidden = true;
    $("confirmar-apagar-legal").hidden = true;
    if (quemAbriuLegal) quemAbriuLegal.focus();
  }

  // ------------------------------------------------------------------ ações da interface
  async function telaCheia() {
    const resposta = await agir("tela_cheia");
    if (resposta && resposta.feito) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen().catch(() => avisar("Tela cheia indisponível aqui."));
  }

  function rotuloDaMalha(modo) {
    const lista = (estado && estado.modos_malha_rotulos) || [];
    const achado = lista.find((item) => item.id === modo);
    return achado ? achado.rotulo : MALHA_PADRAO[modo] || modo;
  }

  function trocarMalha(modo) {
    agir("malha", { modo });
    avisar(modo === "desligada" ? "Malha desligada: só o rosto" : `Malha ${rotuloDaMalha(modo).toLowerCase()}`);
  }

  function proximaMalha() {
    const modos = (estado && estado.modos_malha) || Object.keys(MALHA_PADRAO);
    const atual = estado ? modos.indexOf(estado.malha) : 0;
    trocarMalha(modos[(atual + 1) % modos.length]);
  }

  function alternarSom() {
    const ligado = !(estado && estado.som);
    agir("som", { ligado });
    avisar(ligado ? "Som do alarme ligado" : "Som do alarme desligado");
  }

  async function acaoDoBotao(nome) {
    switch (nome) {
      case "parar":
        avisar("Encerrando o teste…");
        await agir("parar");
        break;
      case "recalibrar":
        if (await agir("recalibrar")) avisar("Recalibrando: olhe para a câmera e pisque normalmente.");
        break;
      case "salvar_resumo": {
        const resposta = await agir("salvar_resumo");
        if (resposta) avisar("Resumo salvo na pasta de dados.");
        break;
      }
      case "apagar_dados": {
        const resposta = await agir("apagar_dados");
        $("confirmar-apagar").hidden = true;
        $("confirmar-apagar-legal").hidden = true;
        if (resposta) avisar(`Dados apagados (${resposta.removidos} ${resposta.removidos === 1 ? "arquivo" : "arquivos"}).`);
        break;
      }
      default:
        await agir(nome);
    }
  }

  function acaoDaInterface(nome) {
    const acoes = {
      legal: abrirLegal,
      "fechar-legal": fecharLegal,
      "confirmar-apagar": () => { $("confirmar-apagar").hidden = false; },
      "cancelar-apagar": () => { $("confirmar-apagar").hidden = true; },
      "confirmar-apagar-legal": () => { $("confirmar-apagar-legal").hidden = false; },
      "cancelar-apagar-legal": () => { $("confirmar-apagar-legal").hidden = true; },
      "tela-cheia": telaCheia,
    };
    if (acoes[nome]) acoes[nome]();
  }

  document.addEventListener("click", (evento) => {
    const alvo = evento.target.closest("button");
    if (!alvo) return;
    if (alvo.dataset.acao) acaoDoBotao(alvo.dataset.acao);
    else if (alvo.dataset.acaoUi) acaoDaInterface(alvo.dataset.acaoUi);
    else if (alvo.dataset.camera) escolherCamera(alvo.dataset.camera);
    else if (alvo.closest("#op-ir")) {
      opcoes.camera_ir = alvo.dataset.valor;
      marcarSegmentado($("op-ir"), opcoes.camera_ir);
    } else if (alvo.closest("#malha")) {
      trocarMalha(alvo.dataset.valor);
    } else if (alvo.id === "botao-som") {
      alternarSom();
    } else if (alvo.id === "iniciar") {
      iniciar();
    } else if (alvo.closest("#legal-abas")) {
      mostrarAba(Number(alvo.dataset.indice));
    } else if (alvo.id === "central-conectar") {
      conectar();
    } else if (alvo.id === "central-desconectar") {
      agir("desconectar").then((resposta) => resposta &&
        avisar("Desconectado. O que já foi enviado continua com a empresa."));
    } else if (alvo.id === "detalhes-botao") {
      abrirDetalhes(!detalhesAbertos);
    } else if (alvo.id === "detalhes-fechar") {
      abrirDetalhes(false);
    } else if (alvo.dataset.assunto) {
      escolherAssunto(alvo.dataset.assunto, true);
    } else if (alvo.id === "r-player-fechar") {
      fecharTrecho();
    } else if (alvo.dataset.trecho) {
      tocarTrecho(alvo.dataset.trecho);
    }
  });

  $("central-enviar").addEventListener("change", (evento) => {
    const ligado = evento.target.checked;
    agir("enviar", { ligado }).then((resposta) => resposta &&
      avisar(ligado ? "Envio para a empresa ligado." : "Envio desligado: nada mais sai deste computador."));
  });

  $("central-codigo").addEventListener("keydown", (evento) => {
    if (evento.key === "Enter") conectar();
  });

  $("caminho-video").addEventListener("input", (evento) => {
    caminhoVideo = evento.target.value;
    if (estado) desenharInicio(estado);
  });

  $("legal").addEventListener("click", (evento) => {
    if (evento.target === $("legal")) fecharLegal();
  });

  // Abas dos detalhes: setas trocam de assunto (em cima/embaixo e esquerda/direita), Home e End vão às pontas.
  $("detalhes-abas").addEventListener("keydown", (evento) => {
    if (!estado || !estado.painel || !estado.painel.assuntos) return;
    const ids = estado.painel.assuntos.map((a) => a.id);
    const atual = Math.max(0, ids.indexOf(assuntoAtual));
    const passos = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 };
    let proximo = null;
    if (evento.key in passos) proximo = (atual + passos[evento.key] + ids.length) % ids.length;
    else if (evento.key === "Home") proximo = 0;
    else if (evento.key === "End") proximo = ids.length - 1;
    if (proximo == null) return;
    evento.preventDefault();
    evento.stopPropagation();
    escolherAssunto(ids[proximo], true);
  });

  $("legal-abas").addEventListener("keydown", (evento) => {
    if (!textosLegais || !["ArrowRight", "ArrowLeft"].includes(evento.key)) return;
    const total = textosLegais.secoes.length;
    const proximo = (abaLegal + (evento.key === "ArrowRight" ? 1 : total - 1)) % total;
    mostrarAba(proximo);
    $("legal-abas").querySelectorAll("button")[proximo].focus();
  });

  document.addEventListener("keydown", (evento) => {
    if (evento.ctrlKey || evento.metaKey || evento.altKey) return;
    if (evento.target.matches && evento.target.matches("input[type=text], textarea")) return;
    if (!$("legal").hidden) {
      if (evento.key === "Escape") fecharLegal();
      return;
    }
    if (telaAtual !== "teste") return;
    if (evento.key === "Escape" && detalhesAbertos) {
      abrirDetalhes(false);
      evento.preventDefault();
      return;
    }
    const tecla = evento.key.toLowerCase();
    if (tecla === "q" || tecla === "escape") acaoDoBotao("parar");
    else if (tecla === "c") acaoDoBotao("recalibrar");
    else if (tecla === "m") proximaMalha();
    else if (tecla === "s") alternarSom();
    else if (tecla === "f") telaCheia();
    else return;
    evento.preventDefault();
  });

  $("video").addEventListener("error", () => {
    if (telaAtual === "teste") setTimeout(() => telaAtual === "teste" && ligarVideo(), 1000);
  });

  window.addEventListener("resize", () => {
    if (estado && telaAtual === "teste") desenharTeste(estado);
    if (estado && telaAtual === "resumo" && estado.resumo) trilhaDoResumo(estado.resumo);
  });

  consultar();
})();
