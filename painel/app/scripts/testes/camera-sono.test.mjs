// Spec 025 · sinais de sono no navegador com as mesmas regras do Python (caixa/vision/face.py, eyes.py e drowsiness.py).
// Séries sintéticas a 30 quadros por segundo; roda no Node, sem câmera.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  LEFT_EYE,
  ModeloDeAbertura,
  MonitorDeSono,
  RIGHT_EYE,
  combinarOlhos,
  ear,
  eulerDaMatriz,
} from "../../src/components/live/camera-sono.ts";

const FPS = 30;

/** Roda uma série quadro a quadro; cada função recebe o tempo em segundos. */
function rodar(segundos, f = {}) {
  const monitor = new MonitorDeSono();
  const leituras = [];
  for (let i = 0; i <= Math.round(segundos * FPS); i++) {
    const t = i / FPS;
    const rosto = f.rosto ? f.rosto(t) : true;
    leituras.push(
      monitor.atualizar({
        t,
        rosto,
        abertura: rosto ? (f.abertura ? f.abertura(t) : 1) : null,
        jawOpen: rosto ? (f.jaw ? f.jaw(t) : 0.05) : null,
        pitch: rosto ? (f.pitch ? f.pitch(t) : 0) : null,
      }),
    );
  }
  return { monitor, leituras, ultima: leituras.at(-1) };
}

function olho(indices, pontos) {
  const lista = Array.from({ length: 478 }, () => ({ x: 0, y: 0 }));
  indices.forEach((indice, k) => (lista[indice] = { x: pontos[k][0], y: pontos[k][1] }));
  return lista;
}

// Valores calculados pelo próprio Python (vision.face.eye_aspect_ratio, .venv do repositório, 19/10/2026).
const ABERTO = [[250, 200], [262.5, 192], [277, 191.5], [290, 201], [276, 209.5], [263, 209]];
const QUASE_FECHADO = [[250, 200], [262, 198.5], [277, 198.8], [290, 200.5], [276.5, 201.2], [263, 201]];
const EAR_PYTHON_ABERTO = 0.4378020548409242;
const EAR_PYTHON_QUASE_FECHADO = 0.06429638376613847;

test("CAM-03 EAR de seis pontos igual ao do Python (face.py) em três casos", () => {
  assert.deepEqual(RIGHT_EYE, [33, 160, 158, 133, 153, 144]);
  assert.deepEqual(LEFT_EYE, [362, 385, 387, 263, 373, 380]);
  assert.ok(Math.abs(ear(olho(RIGHT_EYE, ABERTO), RIGHT_EYE) - EAR_PYTHON_ABERTO) < 1e-12, "olho aberto");
  assert.ok(Math.abs(ear(olho(RIGHT_EYE, QUASE_FECHADO), RIGHT_EYE) - EAR_PYTHON_QUASE_FECHADO) < 1e-12, "olho quase fechado");
  const angulo = (20 * Math.PI) / 180;
  const girado = ABERTO.map(([x, y]) => [
    270 + (x - 270) * Math.cos(angulo) - (y - 200) * Math.sin(angulo),
    200 + (x - 270) * Math.sin(angulo) + (y - 200) * Math.cos(angulo),
  ]);
  assert.ok(Math.abs(ear(olho(LEFT_EYE, girado), LEFT_EYE) - EAR_PYTHON_ABERTO) < 1e-12, "cabeça inclinada 20°, olho esquerdo");
  const degenerado = olho(RIGHT_EYE, ABERTO.map(() => [10, 10]));
  assert.equal(ear(degenerado, RIGHT_EYE), null, "largura zero não vira número");
});

test("CAM-03 dois olhos como no Python: média, ou só o mais visível com a cabeça virada (razão < 0,7)", () => {
  assert.equal(combinarOlhos(0.3, 0.2, 40, 25), 0.3);
  assert.equal(combinarOlhos(0.3, 0.2, 40, 30), 0.25);
  assert.equal(combinarOlhos(null, 0.2, 0, 30), 0.2);
  assert.equal(combinarOlhos(null, null, 0, 0), null);
});

test("CAM-04 olho fechado por 1,2 s gera um evento de microssono; 0,3 s conta como piscada", () => {
  const longo = rodar(4, { abertura: (t) => (t >= 1 && t < 2.2 ? 0.05 : 1) });
  const fechamentos = longo.monitor.eventos.filter((evento) => evento.tipo === "microssono");
  assert.equal(fechamentos.length, 1, JSON.stringify(longo.monitor.eventos));
  assert.ok(Math.abs(fechamentos[0].duracao - 1.2) < 0.1, `duração ${fechamentos[0].duracao}`);
  assert.ok(longo.leituras.some((leitura) => leitura.estagio === "microssono"));
  assert.equal(longo.ultima.piscadas, 0, "fechamento de 1,2 s não é piscada (MAX_BLINK_S = 1,0)");

  const piscada = rodar(3, { abertura: (t) => (t >= 1 && t < 1.3 ? 0.05 : 1) });
  assert.equal(piscada.ultima.piscadas, 1);
  assert.equal(piscada.monitor.eventos.length, 0, "piscada não entra na linha do tempo");
  assert.ok(piscada.leituras.every((leitura) => leitura.estagio === "normal"));
});

test("CAM-04 3,2 s vira sono e 6,2 s vira sem resposta, no mesmo evento; 0,9 s ainda é normal", () => {
  const sono = rodar(6, { abertura: (t) => (t >= 1 && t < 4.2 ? 0.05 : 1) });
  assert.deepEqual(sono.monitor.eventos.map((evento) => evento.tipo), ["sono"], "o evento sobe de microssono para sono");
  const semResposta = rodar(9, { abertura: (t) => (t >= 1 && t < 7.2 ? 0.05 : 1) });
  assert.deepEqual(semResposta.monitor.eventos.map((evento) => evento.tipo), ["sem_resposta"]);
  const curto = rodar(3, { abertura: (t) => (t >= 1 && t < 1.9 ? 0.05 : 1) });
  assert.ok(curto.leituras.every((leitura) => leitura.estagio === "normal"));
  assert.equal(curto.monitor.eventos.length, 0);
});

test("CAM-04 evento em andamento: sem duração enquanto o olho está fechado", () => {
  const { monitor, ultima } = rodar(2.5, { abertura: (t) => (t >= 1 ? 0.05 : 1) });
  assert.equal(ultima.estagio, "microssono");
  assert.equal(monitor.eventos[0].duracao, null);
  assert.ok(ultima.fechadoHa >= 1.4 && ultima.fechadoHa <= 1.6, `fechado há ${ultima.fechadoHa}`);
});

test("CAM-05 PERCLOS de 60 s: fechamentos de 2 s a cada 10 s (20% fechado) dão 0,20 ± 0,01", () => {
  const { ultima } = rodar(61, { abertura: (t) => (t > 1 && t % 10 < 2 ? 0.05 : 1) });
  assert.ok(Math.abs(ultima.perclos60s - 0.2) <= 0.01, `PERCLOS ${ultima.perclos60s}`);
});

test("CAM-05 PERCLOS ignora fechamentos abaixo de 250 ms, como no Python, e só vale com metade da janela", () => {
  const curtos = rodar(61, { abertura: (t) => (t > 1 && t % 3 < 0.2 ? 0.05 : 1) });
  assert.equal(curtos.ultima.perclos60s, 0);
  assert.equal(rodar(20).ultima.perclos60s, null, "20 s não preenchem metade de 60 s");
});

test("CAM-05 PERCLOS acima de 12% entra na linha do tempo uma vez", () => {
  const { monitor } = rodar(61, { abertura: (t) => (t > 1 && t % 10 < 2 ? 0.05 : 1) });
  assert.equal(monitor.eventos.filter((evento) => evento.tipo === "perclos_alto").length, 1);
});

test("CAM-06 bocejo: boca aberta acima do limiar por mais de 2,0 s conta um; 1,5 s (fala) não conta", () => {
  const bocejo = rodar(6, { jaw: (t) => (t >= 1 && t < 3.5 ? 0.6 : 0.05) });
  assert.equal(bocejo.ultima.bocejos, 1);
  const eventos = bocejo.monitor.eventos.filter((evento) => evento.tipo === "bocejo");
  assert.equal(eventos.length, 1);
  assert.ok(Math.abs(eventos[0].duracao - 2.5) < 0.1, `duração ${eventos[0].duracao}`);
  assert.equal(rodar(5, { jaw: (t) => (t >= 1 && t < 2.5 ? 0.6 : 0.05) }).ultima.bocejos, 0);
  assert.equal(rodar(5, { jaw: (t) => (t >= 1 && t < 3.5 ? 0.4 : 0.05) }).ultima.bocejos, 0, "abaixo de 0,45 não é bocejo");
});

test("cabeceio: queda de 20° em 0,3 s, 1 s baixo e volta conta um; inclinar devagar não conta", () => {
  const rapido = (t) => (t < 11 ? 0 : t < 11.3 ? ((t - 11) / 0.3) * 20 : t < 12.3 ? 20 : 0);
  const { ultima, monitor } = rodar(14, { pitch: rapido });
  assert.equal(ultima.cabeceios, 1);
  assert.equal(monitor.eventos.filter((evento) => evento.tipo === "cabeceio").length, 1);
  assert.equal(rodar(20, { pitch: (t) => (t < 11 ? 0 : Math.min(20, (t - 11) * 4)) }).ultima.cabeceios, 0);
});

test("rosto fora da câmera por mais de 2 s entra na linha do tempo com a duração", () => {
  const { monitor, ultima } = rodar(8, { rosto: (t) => !(t >= 2 && t < 5) });
  const fora = monitor.eventos.filter((evento) => evento.tipo === "sem_rosto");
  assert.equal(fora.length, 1);
  assert.ok(Math.abs(fora[0].duracao - 3) < 0.1, `duração ${fora[0].duracao}`);
  assert.equal(ultima.semRostoHa, 0);
  assert.equal(rodar(4, { rosto: (t) => !(t >= 2 && t < 3) }).monitor.eventos.length, 0, "1 s fora não conta");
});

test("piscadas por minuto: 12 piscadas em 60 s dão 12; nada nos primeiros 10 s", () => {
  const { ultima, leituras } = rodar(60.5, { abertura: (t) => (t % 5 >= 2 && t % 5 < 2.15 ? 0.05 : 1) });
  assert.equal(ultima.piscadas, 12);
  assert.equal(ultima.piscadasPorMinuto, 12);
  assert.equal(leituras[5 * FPS].piscadasPorMinuto, null);
});

test("matriz do rosto igual ao Python (rotation_to_euler): pitch 20, yaw -10, roll 5 com os dados em coluna", () => {
  // Matriz Rz(5°)·Ry(-10°)·Rx(20°) com translação, em coluna como o MediaPipe entrega (gerada no Python).
  const coluna = [
    0.98106026219, 0.085831651177, 0.173648177667, 0, -0.141064781583, 0.930940524727, 0.336824088833, 0, -0.132745957934,
    -0.354940371158, 0.925416578398, 0, 1.5, -2, -40, 1,
  ];
  const { pitch, yaw, roll } = eulerDaMatriz(coluna);
  assert.ok(Math.abs(pitch - 20) < 1e-6 && Math.abs(yaw + 10) < 1e-6 && Math.abs(roll - 5) < 1e-6, `${pitch} ${yaw} ${roll}`);
});

test("abertura sem calibração como o OpennessModel do Python: aprende o aberto e os dois sinais precisam concordar", () => {
  const modelo = new ModeloDeAbertura();
  const quadro = (earAtual, piscada) => modelo.abertura({ ear: earAtual, piscada, distanciaOlhosPx: 120 });
  assert.equal(quadro(0.3, 0.05), null, "antes de 30 quadros ainda não sabe o que é aberto");
  assert.equal(modelo.aprendendo, true);
  for (let i = 0; i < 60; i++) quadro(0.3, 0.05);
  assert.equal(modelo.aprendendo, false);
  assert.ok(Math.abs(quadro(0.3, 0.05) - 1) < 1e-9, "aberto habitual = 1");
  assert.ok(quadro(0.09, 0.8) < 1e-9, "EAR em 30% do aberto e piscada alta: fechado");
  assert.ok(quadro(0.12, 0.05) > 0.9, "olho pequeno (EAR baixo) com a piscada dizendo aberto: não fecha");
  assert.equal(modelo.abertura({ ear: 0.3, piscada: 0.05, distanciaOlhosPx: 20 }), null, "rosto pequeno demais (< 30 px)");
  assert.equal(modelo.abertura({ ear: null, piscada: null, distanciaOlhosPx: 120 }), null);
});
