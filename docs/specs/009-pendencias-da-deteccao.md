# Spec 009 · Pendências da detecção (etapa 1)

| Campo | Valor |
|---|---|
| Status | em implementação: CEL-01 corrigido em 14/09/2026; limiar a calibrar com gravações (CEL-03) |
| PRD | RF-01, RF-02 |
| Pedido | "o celular no ouvido ainda não está 100 por cento funcional, pois quando eu coloco a mão no ouvido reconhece como celular ainda" (14/09/2026, testando o app da spec 010) |
| Código | `caixa/vision/phone.py` |
| Testes | `tests/test_celular.py` |

## Contexto

`caixa/vision/phone.py` junta duas fontes:
- o EfficientDet-Lite0 (classe "cell phone" do COCO), que acha o aparelho num recorte ao redor do motorista;
- os 21 pontos por mão do Hand Landmarker.

**O que o teste mostrou.** No teste de 14/09 com o app de teste, houve dois eventos `celular_no_ouvido` (13:42:22 e
13:46:40 UTC, fila local `eventos.db`). Nos dois, `confianca_celular` estava vazio no momento do evento e havia 1 mão
detectada.

**Por que acontecia.** Pelo código anterior, "no ouvido" só aparece se o detector achou "celular" perto da orelha pelo
menos uma vez nos 5 s anteriores:
- **Direto:** 2 detecções de celular em 2 s em qualquer lugar da imagem, com uma delas perto da orelha.
- **Memória:** mão na orelha e 1 detecção perto da orelha nos últimos 5 s.

Uma detecção solta da mão como celular, a cada poucos segundos, bastava para manter o estado. O teste CEL-01
reproduziu isso antes da correção: evento `celular_no_ouvido` com a mão vazia.

## Decisões

1. Detecções perto da orelha e longe dela são contadas separadamente (`_ear_hits` e `_away_hits`).
2. "No ouvido" direto exige uma destas condições:
   - 3 detecções perto da orelha em 2 s (`EAR_CONFIRM_HITS`);
   - o aparelho já confirmado fora da orelha (2 detecções em 2 s) e visto na orelha agora: pegou e atendeu.
3. A memória de 5 s com a mão na orelha só vale depois de o aparelho ter sido confirmado na orelha pela regra 2.
4. "Na mão", "olhando o celular" e o movimento do aparelho usam só detecções longe da orelha. Assim, a mão confundida
   com celular na orelha também não vira "na mão".
5. **Limiares iniciais, sem gravação real.** Se o detector chamar a mão de celular em metade das detecções, 3 em 2 s
   ainda passa. A calibração vem com `ferramentas/analisar_video.py --celular` e `ferramentas/avaliar_celular.py`,
   sobre gravações de mão vazia na orelha e de aparelho real na orelha.

## Comportamento

- Dado a mão vazia na orelha e o detector chamando a mão de celular em 1 de cada 4 ou 5 detecções, quando passam 15 s,
  então o estado fica "sem celular" e não há evento de celular.
- Dado o aparelho real na orelha visto em detecções seguidas, quando passam 3 s, então sai o evento `celular_no_ouvido`
  com alarme (sem regressão).
- Dado o aparelho na mão e levado à orelha, quando chega à orelha, então o estado muda para "no ouvido" na primeira
  detecção na orelha, e cada estado conta o próprio tempo (sem regressão).
- Dado o aparelho visto na orelha e depois tapado pela mão, então "no ouvido" continua por até 5 s (sem regressão).

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| CEL-01 | Mão vazia na orelha, confundida com celular em 1 de cada 4 ou 5 detecções por 15 s: nenhum evento de celular e estado sempre "sem celular" | `tests/test_celular.py` |
| CEL-02 | Casos anteriores seguem iguais: no ouvido por 3 s → evento e alarme; tapado pela mão; da mão para o ouvido; na altura do queixo; outra mão na orelha; suporte; detecção solta; veículo parado | demais verificações de `tests/test_celular.py` |
| CEL-03 | Com gravações reais (mão vazia na orelha, aparelho real na orelha, pelo menos 3 aparelhos, luz de dia e de noite), "no ouvido" atinge as metas da pergunta 1 | `ferramentas/avaliar_celular.py`: pendente, precisa das gravações |

## Fora de escopo

- Bocejo, olheiras, expressões ao redor dos olhos e movimento da cabeça: spec 011 (rascunho).
- Trocar o modelo de detecção de celular (outro modelo exigiria nova avaliação de licença, RNF-10).

## Riscos

- Aparelho real na orelha quase todo tapado pela mão, visto em menos de 3 detecções em 2 s e sem ter sido visto antes
  fora da orelha, pode deixar de contar. Só as gravações dizem quanto isso acontece.
- Detector que confunde a mão com celular com frequência (metade das detecções ou mais) ainda gera "no ouvido". Nesse
  caso o próximo passo é usar a forma da mão ou a caixa do aparelho, medidas nas gravações.

## Perguntas para o Matheus

1. Metas de acerto para "no ouvido" por trecho gravado. Sugestão: precisão de pelo menos 90% (alarme falso raro) e
   sensibilidade de pelo menos 80%.
2. Pode gravar dois vídeos curtos (20 s cada), com a câmera do computador ou do celular, na mesma posição do teste?
   - um com a mão vazia na orelha;
   - um com o celular de verdade na orelha.

   Com eles, o limiar `EAR_CONFIRM_HITS` sai de medida, não de suposição.
