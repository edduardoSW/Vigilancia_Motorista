# Spec 032 · Olhos esfregados detectados de verdade

| Campo | Valor |
|---|---|
| Status | implementada em 20/10/2026 (`tests/test_face_touch.py` 23, `tests/test_celular.py` GES-12 e GES-13); falta conferir com a webcam (roteiro abaixo) |
| PRD | RF-01 (sinais leves de sono) |
| Pedido | "coçar os olhos não esta pegando muito bem" (20/10/2026) |
| Specs irmãs | 009, 011, 028 |
| Código | `caixa/vision/face_touch.py`, `caixa/vision/phone.py` |

## Causa (simulação com os limiares antigos)

1. As mãos chegavam ~3,75 vezes por segundo (e ~2 com o computador ocupado, porque o intervalo avançava mesmo com a
   detecção anterior rodando). Esfregar tem 2 a 4 vai e vens por segundo: a regra "2 inversões em 2 s" falhava.
2. Só 4 pontos da mão contavam (nós e pontas do indicador e do médio).
3. Uma caixa de "celular" que era a própria mão tirava a mão dos gestos: esfregar virava "celular na mão".

## Decisões

- Qualquer ponto da mão (1 a 20) na região do olho, ou o centro do olho dentro do contorno da mão.
- Esfregar = dedo no olho de 0,5 a 5 s **e** (vai e vem com 2 inversões em 2 s **ou** olho tapado por ≥ 0,8 s com a mão
  mexendo). Posição do olho guardada por 1,5 s e enquanto a mão está no rosto.
- Detecção ocupada: o quadro seguinte tenta de novo (GES-12). Caixa na cor de pele da pessoa não tira a mão dos gestos;
  celular de verdade continua tirando (GES-13).

## Critérios

GES-01 a GES-11 em `tests/test_face_touch.py` (rosto sumindo enquanto a mão cobre conta; óculos, nariz, queixo, mão
passando e cabeça apoiada parada não contam; dois esfregões contam 2 com 1 aviso); GES-12 e GES-13 em
`tests/test_celular.py`.

## Roteiro de 2 minutos com a webcam

1. 15 s olhando para a câmera sem mão no rosto.
2. Esfregar o olho direito com os nós dos dedos por 2 s: "Olhos esfregados" sobe para 1.
3. Esfregar o esquerdo com a ponta do indicador, fechando o olho, por 2 s: sobe para 2.
4. Esfregar com o polegar ou a mão tapando o olho por 2 a 3 s: sobe para 3.
5. Não pode subir: ajeitar óculos, coçar o nariz, mão no queixo, mão passando na frente, cabeça apoiada parada.

## Limitações

Ponta de dedo esfregando rápido de olho aberto sem cobrir o centro ainda pode escapar; mão parada tapando o olho com o
rosto perdido conta; coçar a sobrancelha cruzando o olho conta.
