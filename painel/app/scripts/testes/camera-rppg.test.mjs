// Spec 025 · pulso estimado pela câmera no navegador, conferido número a número com o caixa/vision/cardio.py (spec 022).
// As séries sintéticas são as mesmas nos dois lados (ruído de Park-Miller, exato em JavaScript); os valores esperados
// saíram do próprio Python em 19/10/2026 (.venv do repositório). Roda no Node, sem câmera.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  AQUECIMENTO_S,
  FPS_MINIMO,
  LAMBDA_TENDENCIA,
  LIMIAR_SNR_DB,
  MEDIANA_N,
  MEIA_BANDA_SNR_HZ,
  MonitorDoPulso,
  PIXEL_ESCURO,
  PIXEL_SATURADO,
  RAZAO_BOCHECHAS_MIN,
  ROI_BOCHECHA_DIR,
  ROI_BOCHECHA_ESQ,
  ROI_TESTA,
  arredondarPython,
  espectro,
  estimarBpm,
  fft,
  passaFaixa,
  picoESnr,
  pos,
  reamostrar,
  regioesUsaveis,
  removerTendencia,
} from "../../src/components/live/camera-rppg.ts";

function gerador(semente) {
  let estado = semente;
  return () => {
    estado = (estado * 16807) % 2147483647;
    return estado / 2147483647;
  };
}

/** Testa, bochecha esq e bochecha dir: pulso com a assinatura do sangue (mais forte no verde), luz oscilando e ruído. */
function serie(bpm, segundos, pulso, semente, fps = 30) {
  const rnd = gerador(semente);
  const bases = [[180, 125, 105], [170, 118, 100], [175, 121, 103]];
  const assinatura = [0.33, 0.77, 0.53];
  const saida = [];
  let t = 0;
  while (t < segundos) {
    const fase = ((2 * Math.PI * bpm) / 60) * t;
    const p = pulso * (Math.sin(fase) + 0.3 * Math.sin(2 * fase + 0.6)) * 0.004;
    const luz = 1 + 0.03 * Math.sin(2 * Math.PI * 0.25 * t);
    const medias = bases.map((base) => base.map((valor, k) => valor * luz * (1 + assinatura[k] * p) + (rnd() - 0.5) * 0.6));
    saida.push({ t, medias });
    t += (1 / fps) * (0.9 + 0.2 * rnd());
  }
  return saida;
}

const PONTOS = Array.from({ length: 478 }, () => ({ x: 0, y: 0 }));
PONTOS[33] = { x: 200, y: 200 };
PONTOS[263] = { x: 300, y: 200 };
PONTOS[6] = { x: 250, y: 210 };
PONTOS[168] = { x: 250, y: 190 };

function rodar(amostras, semRosto = []) {
  const monitor = new MonitorDoPulso();
  return amostras.map(({ t, medias }) => ({ t, ...monitor.atualizar(t, semRosto.some(([a, b]) => a <= t && t < b) ? null : { pontos: PONTOS, medias }) }));
}

const marco = (leituras, alvo) => leituras.reduce((melhor, leitura) => (Math.abs(leitura.t - alvo) < Math.abs(melhor.t - alvo) ? leitura : melhor));
const perto = (atual, esperado, tolerancia, nome) => assert.ok(Math.abs(atual - esperado) <= tolerancia, `${nome}: ${atual} contra ${esperado} do Python`);

function conferir(leituras, gabarito) {
  for (const esperado of gabarito) {
    const leitura = marco(leituras, esperado.t);
    const onde = `t=${esperado.t.toFixed(2)}`;
    assert.equal(leitura.estado, esperado.estado, `${onde}: estado`);
    if (esperado.bpm === null) assert.equal(leitura.bpm, null, `${onde}: sem número`);
    else perto(leitura.bpm, esperado.bpm, 0.051, `${onde} bpm`);
    perto(leitura.confianca, esperado.confianca, 0.0011, `${onde} confiança`);
    if (esperado.snr === null) assert.equal(leitura.snrDb, null, `${onde}: SNR`);
    else perto(leitura.snrDb, esperado.snr, 0.011, `${onde} SNR`);
    perto(leitura.progresso, esperado.progresso, 0.0002, `${onde} progresso`);
    assert.equal(leitura.onda.length, esperado.onda_n, `${onde}: tamanho da onda`);
    esperado.onda_fim.forEach((valor, i) => perto(leitura.onda.at(i - esperado.onda_fim.length), valor, 0.002, `${onde} onda`));
  }
}

// Gerado por gabarito_cardio.py (rodar(serie(...)) com o CardioMonitor do Python, mesmas chamadas por quadro).
const GABARITO_MONITOR = [
  { t: 4.990909483260899, estado: "medindo", bpm: null, confianca: 0, snr: null, progresso: 0.3327, onda_n: 150, onda_fim: [0.0351, 0.0446, 0.0353] },
  { t: 6.4942502055119675, estado: "medindo", bpm: null, confianca: 0, snr: 2.2, progresso: 0.433, onda_n: 180, onda_fim: [0.0345, 0.0809, 0.1197] },
  { t: 9.997465250771864, estado: "medindo", bpm: null, confianca: 0, snr: 3.83, progresso: 0.6665, onda_n: 180, onda_fim: [0.2624, 0.3626, 0.4767] },
  { t: 14.90974101820483, estado: "medindo", bpm: null, confianca: 0, snr: 3.25, progresso: 0.994, onda_n: 180, onda_fim: [-0.1482, -0.2503, -0.3272] },
  { t: 15.208181726826131, estado: "pronto", bpm: 71.9, confianca: 0.503, snr: 3.37, progresso: 1, onda_n: 180, onda_fim: [0.1972, 0.1963, 0.1503] },
  { t: 18.00238810596944, estado: "pronto", bpm: 72.2, confianca: 0.467, snr: 2.89, progresso: 1, onda_n: 180, onda_fim: [-0.0342, -0.0486, -0.0823] },
  { t: 25.888919958467095, estado: "pronto", bpm: 71.7, confianca: 0.472, snr: 2.96, progresso: 1, onda_n: 180, onda_fim: [0.0735, 0.1431, 0.2505] },
];
const GABARITO_RUIDO = [
  { t: 10.007660154793873, estado: "medindo", bpm: null, confianca: 0, snr: -4.66, progresso: 0.6672, onda_n: 180, onda_fim: [-0.0962, -0.0046, 0.0992] },
  { t: 15.99302900883819, estado: "sinal_fraco", bpm: null, confianca: 0, snr: -5.55, progresso: 1, onda_n: 180, onda_fim: [0.005, -0.0271, -0.0556] },
  { t: 25.911407717023078, estado: "sinal_fraco", bpm: null, confianca: 0, snr: -8.11, progresso: 1, onda_n: 180, onda_fim: [0.2909, 0.2351, 0.1416] },
];
const GABARITO_SEM_ROSTO = [
  { t: 12.48896190861192, estado: "medindo", bpm: null, confianca: 0, snr: 3.88, progresso: 0.8, onda_n: 180, onda_fim: [-0.0363, -0.1051, -0.19] },
  { t: 14.008444290098321, estado: "medindo", bpm: null, confianca: 0, snr: 3.59, progresso: 0.8796, onda_n: 180, onda_fim: [-0.0704, -0.091, -0.1045] },
  { t: 17.898276732066467, estado: "pronto", bpm: 72.2, confianca: 0.283, snr: 1.39, progresso: 1, onda_n: 180, onda_fim: [-0.1622, -0.1927, -0.1995] },
  { t: 18.983591859243006, estado: "pronto", bpm: 72.2, confianca: 0.283, snr: 1.39, progresso: 1, onda_n: 180, onda_fim: [-0.1622, -0.1927, -0.1995] },
  { t: 20.500563223818588, estado: "sem_rosto", bpm: null, confianca: 0, snr: null, progresso: 0, onda_n: 0, onda_fim: [] },
  { t: 21.4843094877034, estado: "medindo", bpm: null, confianca: 0, snr: null, progresso: 0.0315, onda_n: 0, onda_fim: [] },
  { t: 25.888919958467095, estado: "medindo", bpm: null, confianca: 0, snr: null, progresso: 0.3251, onda_n: 146, onda_fim: [-0.0923, -0.0457, -0.0095] },
];

const base = serie(72, 26, 1, 12345);

test("CAM-01 mesmos parâmetros e regiões do cardio.py (esq e dir = lado da imagem)", () => {
  assert.deepEqual(ROI_TESTA, [69, 108, 151, 337, 299, 296, 336, 9, 107, 66]);
  assert.deepEqual(ROI_BOCHECHA_ESQ, [117, 118, 101, 36, 205, 187, 123], "117 é a bochecha direita do motorista, à esquerda na imagem");
  assert.deepEqual(ROI_BOCHECHA_DIR, [346, 347, 330, 266, 425, 411, 352]);
  assert.equal(AQUECIMENTO_S, 15);
  assert.equal(FPS_MINIMO, 15);
  assert.equal(LIMIAR_SNR_DB, 0);
  assert.equal(MEIA_BANDA_SNR_HZ, 0.2);
  assert.equal(LAMBDA_TENDENCIA, 300);
  assert.equal(MEDIANA_N, 5);
  assert.equal(RAZAO_BOCHECHAS_MIN, 0.5);
  assert.deepEqual([PIXEL_ESCURO + 1, PIXEL_SATURADO - 1], [16, 249], "pixel vale com os canais entre 16 e 249");
});

test("CAM-01 funções iguais às do Python: reamostragem, POS, Tarvainen (λ = 300) e passa-faixa", () => {
  const trecho = base.slice(0, 300);
  const { grade, colunas } = reamostrar(trecho.map(({ t }) => t), trecho.map(({ medias }) => medias[0]));
  assert.equal(grade.length, 300);
  [182.66418003883462, 127.03681518976579, 106.69666423736004].forEach((valor, c) => perto(colunas[c][10], valor, 1e-9, "reamostrar"));
  const h = pos(colunas[0], colunas[1], colunas[2]);
  const esperadoPos = [0.0036571774870153284, -0.02767861233677138, 0.037430762505827886, -0.01981559058589255, -0.04580661942414821, 0.0016449916846397183];
  [0, 47, 48, 100, 200, 299].forEach((i, k) => perto(h[i], esperadoPos[k], 1e-9, `pos[${i}]`));
  const verde = trecho.map(({ medias }) => medias[0][1]);
  const semTendencia = removerTendencia(verde);
  [-2.105791073917331, -2.1611937659960034, 1.106199365664935, 1.7729894125748302, -2.1125169081924753].forEach((valor, k) =>
    perto(semTendencia[[0, 1, 50, 150, 299][k]], valor, 1e-6, "Tarvainen"),
  );
  const filtrado = passaFaixa(verde.slice(0, 180));
  [-0.4134051198203449, 0.18441492415126717, 0.019071719282578434, -0.3586255764789545].forEach((valor, k) =>
    perto(filtrado[[0, 30, 90, 179][k]], valor, 1e-9, "passa-faixa"),
  );
});

test("CAM-01 POS com série sintética de 72 bpm: erro de no máximo 2 bpm depois de 10 s (e o mesmo número do Python)", () => {
  const trecho = base.filter(({ t }) => t <= 10.05);
  const { colunas } = reamostrar(trecho.map(({ t }) => t), trecho.map(({ medias }) => medias[0]));
  const estimativa = estimarBpm(pos(colunas[0], colunas[1], colunas[2]));
  assert.ok(Math.abs(estimativa.bpm - 72) <= 2, `estimou ${estimativa.bpm}`);
  const doPython = estimarBpm(pos(...reamostrar(base.slice(0, 300).map(({ t }) => t), base.slice(0, 300).map(({ medias }) => medias[0])).colunas));
  perto(doPython.bpm, 71.97479461028831, 1e-6, "bpm");
  perto(doPython.snrDb, 4.784903834782258, 1e-6, "SNR");
});

test("CAM-01 monitor igual ao CardioMonitor: aquecimento de 15 s, depois mediana das últimas 5 estimativas", () => {
  const leituras = rodar(base);
  conferir(leituras, GABARITO_MONITOR);
  assert.ok(leituras.filter((leitura) => leitura.t < AQUECIMENTO_S).every((leitura) => leitura.bpm === null), "nenhum número no aquecimento");
  const prontas = leituras.filter((leitura) => leitura.estado === "pronto");
  assert.ok(prontas.length > 0 && prontas.every((leitura) => Math.abs(leitura.bpm - 72) <= 2));
});

test("CAM-02 só ruído: sinal fraco, sem número (igual ao Python)", () => {
  const leituras = rodar(serie(72, 26, 0, 777));
  conferir(leituras, GABARITO_RUIDO);
  assert.ok(leituras.every((leitura) => leitura.bpm === null));
});

test("CAM-02 rosto some por 0,8 s: mantém a leitura; por mais de 2 s: zera tudo e recomeça o aquecimento (igual ao Python)", () => {
  conferir(rodar(base, [[12, 12.8], [18, 21]]), GABARITO_SEM_ROSTO);
});

test("CAM-02 número só com 15 quadros por segundo ou mais", () => {
  const lento = rodar(serie(72, 26, 1, 12345, 12));
  assert.ok(lento.every((leitura) => leitura.bpm === null), "a 12 quadros por segundo não mostra número");
});

test("movimento da cabeça: estado movimento e o trecho recomeça (sem número errado)", () => {
  const monitor = new MonitorDoPulso();
  let ultima;
  for (const { t, medias } of base) {
    const mexendo = t >= 20 && t < 20.5;
    const pontos = mexendo ? PONTOS.map((ponto) => ({ x: ponto.x + (t - 20) * 120, y: ponto.y })) : PONTOS;
    ultima = monitor.atualizar(t, { pontos, medias });
    if (t >= 20.2 && t < 20.5) assert.equal(ultima.estado, "movimento", `t=${t}`);
  }
  assert.equal(ultima.estado, "pronto");
});

test("bochecha com menos da metade da área da outra (rosto virado) sai da média", () => {
  const quadrado = (lado) => [{ x: 0, y: 0 }, { x: lado, y: 0 }, { x: lado, y: lado }, { x: 0, y: lado }];
  assert.deepEqual(regioesUsaveis([quadrado(10), quadrado(10), quadrado(9)]), [true, true, true]);
  assert.deepEqual(regioesUsaveis([quadrado(10), quadrado(10), quadrado(7)]), [true, true, false], "49% da área da outra");
  assert.deepEqual(regioesUsaveis([quadrado(10), quadrado(6), quadrado(10)]), [true, false, true]);
});

test("apoio: FFT, pico no meio harmônico e arredondamento do Python", () => {
  const n = 64;
  const re = new Float64Array(n);
  const im = new Float64Array(n);
  for (let i = 0; i < n; i++) re[i] = Math.sin((2 * Math.PI * 8 * i) / n);
  fft(re, im);
  const magnitude = Array.from(re, (valor, i) => Math.hypot(valor, im[i])).slice(0, n / 2);
  assert.equal(magnitude.indexOf(Math.max(...magnitude)), 8);
  // Pulso de 1,0 Hz com 2º harmônico mais forte (2,0 Hz): fica 1,0 Hz.
  const sinal = Float64Array.from({ length: 300 }, (_, i) => 0.8 * Math.sin((2 * Math.PI * 1.0 * i) / 30) + Math.sin((2 * Math.PI * 2.0 * i) / 30));
  const { freqs, potencia } = espectro(sinal);
  assert.ok(Math.abs(picoESnr(freqs, potencia).hz - 1.0) < 0.02);
  assert.equal(arredondarPython(0.125, 2), 0.12);
  assert.equal(arredondarPython(71.95, 1), 72);
  assert.equal(arredondarPython(2.5), 2);
});
