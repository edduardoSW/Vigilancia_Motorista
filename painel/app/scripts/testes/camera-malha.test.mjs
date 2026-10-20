// Spec 029 · MAL-07: a câmera do painel segue as mesmas regras de malha do script Python (MAL-01 a MAL-04 e MAL-08).
// O desenho roda num canvas falso que rasteriza o que o código pede (caminhos, preenchimentos, traços com tracejado,
// recorte), com 16 amostras por pixel: qualquer amostra coberta conta como pixel alterado (critério conservador).
// Nada é preenchido: o desenho só usa traços (stroke); o canvas falso conta cada fill e fillRect.
// O rosto sintético repete o tests/test_tela_teste.py (rosto_anatomico): contorno, olhos, íris, boca e regiões do
// pulso nos lugares do Face Mesh; o resto dos 478 pontos é aleatório dentro do rosto, inclusive perto dos olhos.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import path from "node:path";
import { test } from "node:test";

// Os arquivos do painel importam "./camera-cores" sem extensão (o bundler resolve); no Node, procurar o .ts.
registerHooks({
  resolve(especificador, contexto, proximo) {
    if (/^\.\.?\//.test(especificador) && !path.extname(especificador) && contexto.parentURL?.endsWith(".ts")) {
      return proximo(`${especificador}.ts`, contexto);
    }
    return proximo(especificador, contexto);
  },
});

const malha = await import("../../src/components/live/camera-malha.ts");
const { MODOS_DA_MALHA, situacaoDoPulso } = await import("../../src/components/live/camera-regras.ts");
const { ROIS, AQUECIMENTO_S, MonitorDoPulso } = await import("../../src/components/live/camera-rppg.ts");

const { desenharMalha, CONTORNO_DO_ROSTO, OLHO_DIREITO, OLHO_ESQUERDO, BOCA_DE_FORA, BOCA_DE_DENTRO, IRIS } = malha;
const LARGURA = 640;
const ALTURA = 480;
const AMOSTRAS = 4; // 4 × 4 por pixel

// ------------------------------------------------------------------------------------------------ canvas falso
function alfaDe(estilo) {
  const texto = String(estilo);
  const rgba = texto.match(/rgba\([^)]*,\s*([\d.]+)\s*\)/);
  if (rgba) return Number(rgba[1]);
  return 1;
}

function dentroDoCaminho(caminho, x, y, regra) {
  let voltas = 0;
  let cruzamentos = 0;
  for (const { pts } of caminho) {
    for (let i = 0; i < pts.length; i++) {
      const [x1, y1] = pts[i];
      const [x2, y2] = pts[(i + 1) % pts.length];
      if (y1 <= y ? y2 > y : y2 <= y) {
        const xCruza = x1 + ((y - y1) / (y2 - y1)) * (x2 - x1);
        if (xCruza > x) {
          cruzamentos++;
          voltas += y2 > y1 ? 1 : -1;
        }
      }
    }
  }
  return regra === "evenodd" ? cruzamentos % 2 === 1 : voltas !== 0;
}

function caixaDe(pontos) {
  const xs = pontos.map((p) => p[0]);
  const ys = pontos.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

/** Pedaços de traço (com o tracejado aplicado) de um subcaminho. */
function pedacos(sub, tracejado) {
  const pts = sub.fechado ? [...sub.pts, sub.pts[0]] : sub.pts;
  const segmentos = [];
  for (let i = 0; i + 1 < pts.length; i++) segmentos.push([pts[i], pts[i + 1]]);
  if (!tracejado.length) return segmentos;
  const padrao = tracejado.length % 2 ? [...tracejado, ...tracejado] : tracejado;
  const saida = [];
  let k = 0;
  let resto = padrao[0];
  for (const [a, b] of segmentos) {
    const comprimento = Math.hypot(b[0] - a[0], b[1] - a[1]);
    let andado = 0;
    while (andado < comprimento - 1e-9) {
      const passo = Math.min(resto, comprimento - andado);
      if (k % 2 === 0 && passo > 0) {
        const t0 = andado / comprimento;
        const t1 = (andado + passo) / comprimento;
        saida.push([
          [a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0],
          [a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1],
        ]);
      }
      andado += passo;
      resto -= passo;
      if (resto <= 1e-9) {
        k = (k + 1) % padrao.length;
        resto = padrao[k];
      }
    }
  }
  return saida;
}

function distanciaAoSegmento(px, py, [a, b], ponta) {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const comprimento2 = dx * dx + dy * dy;
  let t = comprimento2 ? ((px - a[0]) * dx + (py - a[1]) * dy) / comprimento2 : 0;
  if (ponta === "butt" && comprimento2 && (t < 0 || t > 1)) return Infinity;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy));
}

class TelaFalsa {
  constructor(largura, altura) {
    this.canvas = { width: largura, height: altura };
    this.alfa = new Float32Array(largura * altura);
    this.recorte = null;
    this.pilha = [];
    this.caminho = [];
    this.preenchimentos = []; // caixa de cada subcaminho preenchido
    this.chamadasDeFill = 0; // fill e fillRect: a malha não pode chamar nenhum (nada preenchido sobre a pele)
    this.fillStyle = "#000";
    this.strokeStyle = "#000";
    this.lineWidth = 1;
    this.lineCap = "butt";
    this.lineJoin = "miter";
    this.globalAlpha = 1;
    this.tracejado = [];
  }
  save() {
    const { fillStyle, strokeStyle, lineWidth, lineCap, lineJoin, globalAlpha, tracejado, recorte } = this;
    this.pilha.push({ fillStyle, strokeStyle, lineWidth, lineCap, lineJoin, globalAlpha, tracejado, recorte });
  }
  restore() {
    Object.assign(this, this.pilha.pop() ?? {});
  }
  setLineDash(lista) {
    this.tracejado = lista.slice();
  }
  getLineDash() {
    return this.tracejado.slice();
  }
  beginPath() {
    this.caminho = [];
  }
  moveTo(x, y) {
    this.caminho.push({ pts: [[x, y]], fechado: false });
  }
  lineTo(x, y) {
    const ultimo = this.caminho.at(-1);
    if (!ultimo || ultimo.fechado) this.moveTo(x, y);
    else ultimo.pts.push([x, y]);
  }
  closePath() {
    const ultimo = this.caminho.at(-1);
    if (ultimo) {
      ultimo.fechado = true;
      this.caminho.push({ pts: [ultimo.pts[0].slice()], fechado: false });
    }
  }
  rect(x, y, w, h) {
    this.caminho.push({ pts: [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], fechado: true });
    this.caminho.push({ pts: [[x, y]], fechado: false });
  }
  arc(cx, cy, r, a0, a1) {
    let ultimo = this.caminho.at(-1);
    if (!ultimo || ultimo.fechado) {
      this.caminho.push({ pts: [], fechado: false });
      ultimo = this.caminho.at(-1);
    }
    const passos = 32;
    for (let i = 0; i <= passos; i++) {
      const angulo = a0 + ((a1 - a0) * i) / passos;
      ultimo.pts.push([cx + r * Math.cos(angulo), cy + r * Math.sin(angulo)]);
    }
  }
  clearRect(x, y, w, h) {
    for (let j = Math.max(0, Math.floor(y)); j < Math.min(this.canvas.height, Math.ceil(y + h)); j++) {
      for (let i = Math.max(0, Math.floor(x)); i < Math.min(this.canvas.width, Math.ceil(x + w)); i++) this.alfa[j * this.canvas.width + i] = 0;
    }
  }
  fillRect(x, y, w, h) {
    this.chamadasDeFill++;
    const salvo = this.caminho;
    this.caminho = [];
    this.rect(x, y, w, h);
    this.fill();
    this.caminho = salvo;
  }
  /** Pinta os pixels com cobertura > 0 dentro da caixa, usando cobre(x, y) em 16 amostras por pixel. */
  pintar([x0, y0, x1, y1], cobre, alfa) {
    const { width, height } = this.canvas;
    for (let j = Math.max(0, Math.floor(y0) - 1); j <= Math.min(height - 1, Math.ceil(y1) + 1); j++) {
      for (let i = Math.max(0, Math.floor(x0) - 1); i <= Math.min(width - 1, Math.ceil(x1) + 1); i++) {
        let n = 0;
        for (let sy = 0; sy < AMOSTRAS; sy++) {
          for (let sx = 0; sx < AMOSTRAS; sx++) {
            const px = i + (sx + 0.5) / AMOSTRAS;
            const py = j + (sy + 0.5) / AMOSTRAS;
            if (cobre(px, py) && (!this.recorte || this.recorte(px, py))) n++;
          }
        }
        if (!n) continue;
        const a = (alfa * n) / (AMOSTRAS * AMOSTRAS);
        const k = j * width + i;
        this.alfa[k] = a + (1 - a) * this.alfa[k];
      }
    }
  }
  fill(regra = "nonzero") {
    this.chamadasDeFill++;
    const subs = this.caminho.filter(({ pts }) => pts.length >= 3);
    if (!subs.length) return;
    for (const { pts } of subs) this.preenchimentos.push(caixaDe(pts));
    const caixa = caixaDe(subs.flatMap(({ pts }) => pts));
    this.pintar(caixa, (x, y) => dentroDoCaminho(subs, x, y, regra), alfaDe(this.fillStyle) * this.globalAlpha);
  }
  stroke() {
    const meia = this.lineWidth / 2;
    const ponta = this.lineCap;
    const alfa = alfaDe(this.strokeStyle) * this.globalAlpha;
    for (const sub of this.caminho) {
      for (const pedaco of pedacos(sub, this.tracejado)) {
        const [x0, y0, x1, y1] = caixaDe(pedaco);
        const folga = meia + 1;
        this.pintar([x0 - folga, y0 - folga, x1 + folga, y1 + folga], (x, y) => {
          const d = distanciaAoSegmento(x, y, pedaco, ponta);
          if (ponta === "square") {
            return distanciaAoSegmento(x, y, pedaco, "round") <= meia * Math.SQRT2 && d <= meia + 1e-9 ? true : d <= meia;
          }
          return d <= meia;
        }, alfa);
      }
    }
  }
  clip(regra = "nonzero") {
    const subs = this.caminho.filter(({ pts }) => pts.length >= 3).map((sub) => ({ pts: sub.pts.map((p) => p.slice()) }));
    const anterior = this.recorte;
    this.recorte = (x, y) => (!anterior || anterior(x, y)) && dentroDoCaminho(subs, x, y, regra);
  }
}

// ------------------------------------------------------------------------------------------------ rosto sintético
function gerador(semente) {
  let estado = semente;
  return () => {
    estado = (estado * 16807) % 2147483647;
    return estado / 2147483647;
  };
}

function rostoAnatomico({ cx = 320, cy = 250, largura = 190, altura = 230, semente = 29 } = {}) {
  const aleatorio = gerador(semente);
  const a = largura / 2;
  const b = altura / 2;
  const pts = Array.from({ length: 478 }, () => {
    const angulo = aleatorio() * 2 * Math.PI;
    const raio = Math.sqrt(aleatorio()) * 0.92;
    return [cx + Math.cos(angulo) * raio * a, cy + Math.sin(angulo) * raio * b];
  });
  const anel = (indices, ccx, ccy, ra, rb, fase = Math.PI) =>
    indices.forEach((indice, k) => {
      const angulo = fase + (2 * Math.PI * k) / indices.length;
      pts[indice] = [ccx + ra * Math.cos(angulo), ccy + rb * Math.sin(angulo)];
    });
  anel(CONTORNO_DO_ROSTO, cx, cy, a, b, -Math.PI / 2);
  const olhoDir = [cx - 0.21 * largura, cy - 0.1 * altura];
  const olhoEsq = [cx + 0.21 * largura, cy - 0.1 * altura];
  anel(ROIS[0], cx, cy - 0.34 * altura, 0.16 * largura, 0.06 * altura);
  anel(ROIS[1], cx - 0.24 * largura, cy + 0.08 * altura, 0.07 * largura, 0.06 * altura);
  anel(ROIS[2], cx + 0.24 * largura, cy + 0.08 * altura, 0.07 * largura, 0.06 * altura);
  anel(OLHO_DIREITO, ...olhoDir, 0.1 * largura, 0.04 * largura);
  anel(OLHO_ESQUERDO, ...olhoEsq, 0.1 * largura, 0.04 * largura);
  IRIS.forEach(({ centro, anel: indices }, k) => {
    const [ex, ey] = k === 0 ? olhoDir : olhoEsq;
    pts[centro] = [ex, ey];
    anel(indices, ex, ey, 0.033 * largura, 0.033 * largura, 0);
  });
  anel(BOCA_DE_FORA, cx, cy + 0.27 * altura, 0.17 * largura, 0.06 * altura);
  anel(BOCA_DE_DENTRO, cx, cy + 0.27 * altura, 0.12 * largura, 0.025 * altura);
  return pts;
}

const CORES = { lima: [213, 246, 105], sobreVideo: [234, 242, 236], alarme: [244, 96, 84], verde: [80, 200, 120], apagado: [120, 120, 120], fio: [60, 60, 60] };
const PIXELS = rostoAnatomico();
const PONTOS = PIXELS.map(([x, y]) => ({ x: x / LARGURA, y: y / ALTURA, z: 0 }));
const TODAS_AS_AREAS = [true, true, true];

function desenhar(modo, extra = {}) {
  const tela = new TelaFalsa(LARGURA, ALTURA);
  desenharMalha(tela, PONTOS, { modo, pulso: 0.8, olhosFechados: false, areas: TODAS_AS_AREAS, cores: CORES, ...extra });
  return tela;
}

function mascaraDoPoligono(poligono) {
  const caminho = [{ pts: poligono }];
  const dentro = [];
  const [x0, y0, x1, y1] = caixaDe(poligono);
  for (let j = Math.floor(y0); j <= Math.ceil(y1); j++) {
    for (let i = Math.floor(x0); i <= Math.ceil(x1); i++) {
      if (dentroDoCaminho(caminho, i + 0.5, j + 0.5, "nonzero")) dentro.push(j * LARGURA + i);
    }
  }
  return dentro;
}

const OLHOS = [OLHO_DIREITO, OLHO_ESQUERDO].map((caminho) => mascaraDoPoligono(caminho.map((i) => PIXELS[i])));
const REGIOES = ROIS.map((regiao) => mascaraDoPoligono(regiao.map((i) => PIXELS[i])));
const MODOS_VISIVEIS = ["discreta", "completa"];
const SITUACOES = [
  { nome: "olho aberto, pulso medido", extra: {} },
  { nome: "olho fechado", extra: { olhosFechados: true } },
  { nome: "pulso ainda medindo", extra: { pulso: null } },
];

function caixaDoRosto() {
  const [x0, y0, x1, y1] = caixaDe(PIXELS);
  const indices = [];
  for (let j = Math.floor(y0); j <= Math.ceil(y1); j++) for (let i = Math.floor(x0); i <= Math.ceil(x1); i++) indices.push(j * LARGURA + i);
  return indices;
}

const fracaoAlterada = (tela, indices) => indices.filter((k) => tela.alfa[k] > 0).length / indices.length;

// ------------------------------------------------------------------------------------------------ testes
test("MAL-07 · MAL-08 modos da câmera do painel: Discreta (padrão), Completa e Só o rosto; Pontos e Essencial saíram", () => {
  assert.deepEqual(
    MODOS_DA_MALHA.map(({ id, rotulo }) => [id, rotulo]),
    [
      ["discreta", "Discreta"],
      ["completa", "Completa"],
      ["desligada", "Só o rosto"],
    ],
  );
  const pasta = path.join(import.meta.dirname, "..", "..", "src", "components", "live");
  for (const nome of readdirSync(pasta).filter((arquivo) => arquivo.startsWith("camera-"))) {
    const texto = readFileSync(path.join(pasta, nome), "utf8");
    assert.doesNotMatch(texto, /"essencial"|"pontos"/, `${nome}: modo antigo da malha`);
  }
  const tela = readFileSync(path.join(pasta, "camera-tela.tsx"), "utf8");
  assert.match(tela, /escolhaDeModo \?\? "discreta"/, "a câmera abre na Discreta, no computador e no celular");
  const motor = readFileSync(path.join(pasta, "camera-motor.ts"), "utf8");
  assert.match(motor, /private modo: ModoDaMalha = "discreta"/);
});

test("MAL-07 · MAL-01 nenhum pixel dentro dos olhos é pintado, em todos os modos e situações", () => {
  for (const olho of OLHOS) assert.ok(olho.length > 100, "olho sintético com área");
  for (const modo of MODOS_VISIVEIS) {
    for (const { nome, extra } of SITUACOES) {
      const tela = desenhar(modo, extra);
      assert.ok(tela.alfa.some((a) => a > 0), `${modo}: a malha aparece`);
      OLHOS.forEach((olho, k) => {
        const pintados = olho.filter((indice) => tela.alfa[indice] > 0).length;
        assert.equal(pintados, 0, `${modo}, ${nome}: ${pintados} pixels pintados dentro do olho ${k ? "esquerdo" : "direito"}`);
      });
    }
  }
});

test("MAL-07 · MAL-01 mesmo com pontos do rosto caindo dentro do olho, o recorte protege o olho", () => {
  const pontos = PONTOS.map((ponto) => ({ ...ponto }));
  // Pior caso: pontos comuns em cima do centro de cada olho.
  const [dx, dy] = [PIXELS[468], PIXELS[473]].map(([x, y]) => ({ x: x / LARGURA, y: y / ALTURA, z: 0 }));
  pontos[1] = { ...dx };
  pontos[2] = { ...dy };
  for (const modo of MODOS_VISIVEIS) {
    const tela = new TelaFalsa(LARGURA, ALTURA);
    desenharMalha(tela, pontos, { modo, pulso: 0.5, olhosFechados: false, areas: TODAS_AS_AREAS, cores: CORES });
    for (const olho of OLHOS) assert.equal(olho.filter((indice) => tela.alfa[indice] > 0).length, 0, modo);
  }
});

test("MAL-07 · MAL-02 nada preenchido: nenhuma chamada de fill e regiões do pulso com menos de 3% pintado", () => {
  for (const modo of [...MODOS_VISIVEIS, "desligada"]) {
    for (const { nome, extra } of SITUACOES) {
      const tela = desenhar(modo, extra);
      assert.equal(tela.chamadasDeFill, 0, `${modo}, ${nome}: ${tela.chamadasDeFill} chamadas de fill`);
      assert.equal(tela.preenchimentos.length, 0, `${modo}, ${nome}: algo preenchido`);
      REGIOES.forEach((regiao, k) => {
        const fracao = fracaoAlterada(tela, regiao);
        assert.ok(fracao < 0.03, `${modo}, ${nome}: região ${k} com ${(fracao * 100).toFixed(1)}% pintado`);
      });
    }
  }
  const fonte = readFileSync(path.join(import.meta.dirname, "..", "..", "src", "components", "live", "camera-malha.ts"), "utf8");
  assert.doesNotMatch(fonte, /\.fill(Rect)?\(|fillStyle/, "camera-malha.ts não preenche nada");
});

test("MAL-07 · MAL-03 Discreta pinta menos de 1,5% da caixa do rosto e Completa menos de 6% (quadro 640 × 480)", () => {
  const caixa = caixaDoRosto();
  const discreta = fracaoAlterada(desenhar("discreta"), caixa);
  const completa = fracaoAlterada(desenhar("completa"), caixa);
  assert.ok(discreta < 0.015, `discreta: ${(discreta * 100).toFixed(2)}%`);
  assert.ok(completa < 0.06, `completa: ${(completa * 100).toFixed(2)}%`);
  assert.ok(completa > discreta, "a completa mostra mais que a discreta");
});

test("MAL-07 · MAL-04 Só o rosto não pinta nenhum pixel", () => {
  const tela = desenhar("desligada");
  assert.equal(tela.alfa.filter((a) => a > 0).length, 0);
  assert.equal(tela.preenchimentos.length, 0);
});

test("MAL-07 lima só no que mede: os olhos em lima; contorno e boca em branco translúcido", () => {
  const tela = new TelaFalsa(LARGURA, ALTURA);
  const estilos = [];
  for (const metodo of ["fill", "stroke"]) {
    const original = tela[metodo].bind(tela);
    tela[metodo] = (...args) => {
      estilos.push({ metodo, estilo: metodo === "fill" ? tela.fillStyle : tela.strokeStyle });
      return original(...args);
    };
  }
  desenharMalha(tela, PONTOS, { modo: "discreta", pulso: null, olhosFechados: false, areas: TODAS_AS_AREAS, cores: CORES });
  const lima = `rgba(${CORES.lima.join(", ")}`;
  const branco = `rgba(${CORES.sobreVideo.join(", ")}`;
  assert.ok(estilos.some(({ estilo }) => estilo.startsWith(lima)), "olhos em lima");
  assert.ok(estilos.some(({ estilo }) => estilo.startsWith(branco)), "o resto em branco");
  for (const { estilo } of estilos.filter(({ estilo }) => estilo.startsWith(branco))) {
    assert.ok(alfaDe(estilo) <= 0.45, `branco translúcido: ${estilo}`);
  }
});

test("MAL-07 legenda da câmera: olhos marcados por fora, sem íris", () => {
  const palco = readFileSync(path.join(import.meta.dirname, "..", "..", "src", "components", "live", "camera-palco.tsx"), "utf8");
  assert.doesNotMatch(palco, /Olhos e íris/);
  assert.match(palco, /Olhos, marcados por fora/);
  assert.match(palco, /Cantos das áreas do pulso/);
});

// ------------------------------------------------------------------------------------------------ coração
const leitura = (extra) => ({ estado: "medindo", bpm: null, confianca: 0, snrDb: null, progresso: 0, onda: [], ultimoBpm: null, ...extra });

test("MAL-07 coração: medindo mostra o andamento \"Medindo seu pulso, faltam ~N s\" e a barra de progresso", () => {
  const inicio = situacaoDoPulso(leitura({ progresso: 0 }));
  assert.equal(inicio.andamento.texto, `Medindo seu pulso, faltam ~${AQUECIMENTO_S} s`);
  assert.equal(inicio.andamento.progresso, 0);
  assert.equal(inicio.numero, null);
  assert.equal(situacaoDoPulso(leitura({ progresso: 0.6 })).andamento.texto, "Medindo seu pulso, faltam ~6 s");
  assert.equal(situacaoDoPulso(leitura({ progresso: 0.99 })).andamento.texto, "Medindo seu pulso, faltam ~1 s", "nunca 0 s");
  const pronto = situacaoDoPulso(leitura({ estado: "pronto", bpm: 72.4, confianca: 0.8, progresso: 1, ultimoBpm: 72.4 }));
  assert.deepEqual([pronto.numero, pronto.esmaecido, pronto.andamento], [72, false, null]);
  assert.equal(pronto.rotulo, "Confiança 80%");
});

test("MAL-07 coração: quando o sinal piora não para: último valor esmaecido e continua medindo", () => {
  for (const estado of ["sinal_fraco", "movimento"]) {
    const ruim = situacaoDoPulso(leitura({ estado, progresso: 1, ultimoBpm: 71.6 }));
    assert.equal(ruim.numero, 72, `${estado}: mostra o último valor`);
    assert.equal(ruim.esmaecido, true, `${estado}: esmaecido`);
    assert.ok(ruim.andamento, `${estado}: com indicativo de andamento`);
    assert.equal(ruim.andamento.progresso, null, `${estado}: andamento contínuo (sem barra parada)`);
    assert.match(ruim.andamento.texto, /continua medindo/i, estado);
    const semUltimo = situacaoDoPulso(leitura({ estado, progresso: 1 }));
    assert.equal(semUltimo.numero, null);
    assert.match(semUltimo.andamento.texto, /continua medindo/i, `${estado} sem número anterior`);
  }
  // Medindo de novo depois de já ter tido número (o aquecimento recomeçou): o último valor fica esmaecido.
  const recomecou = situacaoDoPulso(leitura({ progresso: 0.2, ultimoBpm: 70 }));
  assert.deepEqual([recomecou.numero, recomecou.esmaecido], [70, true]);
  assert.match(recomecou.andamento.texto, /^Medindo seu pulso, faltam ~12 s$/);
  const semRosto = situacaoDoPulso(leitura({ estado: "sem_rosto" }));
  assert.equal(semRosto.numero, null);
  assert.match(semRosto.aviso, /rosto/);
});

test("MAL-07 coração: com o sinal piorando no meio, o monitor segue medindo e volta a dar número sozinho", () => {
  // 72 bpm limpo por 20 s, 6 s de ruído forte (sinal fraco) e 72 bpm limpo de novo: a leitura nunca trava.
  const monitor = new MonitorDoPulso();
  const pontos = Array.from({ length: 478 }, (_, k) => ({ x: 200 + (k % 20) * 10, y: 150 + Math.floor(k / 20) * 8 }));
  let semente = 7;
  const aleatorio = () => ((semente = (semente * 16807) % 2147483647) / 2147483647);
  const estados = [];
  for (let i = 0; i < 45 * 30; i++) {
    const t = i / 30;
    const ruido = t >= 20 && t < 26;
    const p = ruido ? 0 : Math.sin(2 * Math.PI * 1.2 * t) * 0.004;
    const medias = [0, 1, 2].map(() => {
      const n = () => (aleatorio() - 0.5) * (ruido ? 0.05 : 0.0005);
      return [120 * (1 + 0.33 * p + n()), 90 * (1 + p + n()), 70 * (1 + 0.5 * p + n())];
    });
    const atual = monitor.atualizar(t, { pontos, medias });
    estados.push([t, atual.estado, atual.ultimoBpm]);
    const situacao = situacaoDoPulso(atual);
    if (atual.estado !== "pronto") {
      assert.ok(situacao.andamento, `t=${t.toFixed(2)}: ${atual.estado} sem indicativo de andamento`);
      if (atual.ultimoBpm !== null) assert.equal(situacao.esmaecido, true, `t=${t.toFixed(2)}: último valor esmaecido`);
    }
  }
  assert.ok(estados.some(([t, estado]) => t < 20 && estado === "pronto"), "deu número antes do ruído");
  assert.ok(estados.some(([t, estado]) => t >= 20 && t < 32 && estado !== "pronto"), "o ruído piorou o sinal");
  assert.ok(estados.filter(([t]) => t >= 20).every(([, , ultimo]) => ultimo !== null), "o último valor nunca some");
  assert.equal(estados.at(-1)[1], "pronto", "voltou a dar número sozinho depois do ruído");
});
