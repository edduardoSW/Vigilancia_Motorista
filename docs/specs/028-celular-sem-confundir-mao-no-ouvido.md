# Spec 028 · Celular no ouvido sem confundir a mão vazia

| Campo | Valor |
|---|---|
| Status | implementada em 19/10/2026 (`tests/test_celular.py`: 25 verificações; antes da correção falhavam CEL-04 a CEL-09 e CEL-11 a CEL-14); falta a validação com gravação real (CEL-03, roteiro em `docs/validacao/roteiro-cel03-celular.md`) |
| PRD | RF-02 |
| Pedido | "outra coisa a parte do celular era algo que pecava muito pois a pessoa antes estava com a mão no ouvido e o script detectava como celular isso não pode acontecer" (19/10/2026). Antes: "o celular no ouvido ainda não está 100 por cento funcional, pois quando eu coloco a mão no ouvido reconhece como celular ainda" (14/09/2026) |
| Specs irmãs | 009 (CEL-01 a CEL-03), 027 (DMS-09 e DMS-10) |
| Código | `caixa/vision/phone.py`, `ferramentas/avaliar_celular.py` |
| Testes | `tests/test_celular.py` (CEL-01 e CEL-02 continuam; CEL-04 a CEL-14 novos) |

## Por que ainda falha (conferido no código em 19/10/2026)

- "No ouvido" depende só do EfficientDet-Lite0 (COCO, classe `cell phone`) achar uma caixa perto da orelha em 3
  detecções em 2 s (`phone.py`, `EAR_CONFIRM_HITS = 3`), com confiança mínima de 0,35.
- O detector chama a **própria mão** de celular. A correção de 14/09 só subiu o número de detecções exigidas; a 4
  detecções por segundo, a mão parada na orelha passa de 3 em 2 s.
- O model card do Hand Landmarker põe fora do escopo a mão segurando objetos, então os pontos da mão podem falhar
  justo com o celular de verdade: a mão sozinha também não serve de prova.

## Princípio

**Na orelha, celular só existe com prova de objeto que não é a mão.** O detector propõe; três verificações
independentes confirmam. Na dúvida, "sem celular": o pedido é que a mão vazia nunca vire celular, mesmo que algum
celular real demore mais a ser reconhecido.

## Decisões

1. **Pele da própria pessoa.** Referência de cor da pele tirada das bochechas (pontos do rosto, ou região fixa da caixa
   do rosto no modo YuNet), em YCrCb, renovada aos poucos. Caixa candidata na orelha com **≥ 60% dos pixels com cor de
   pele** dessa pessoa não conta como celular.
2. **O aparelho passa da mão.** Com mão detectada perto da orelha: a caixa candidata precisa ter **≥ 30% da área fora
   do contorno da mão** (envoltória convexa dos 21 pontos, dilatada em 10% da largura do rosto). Caixa contida na mão é
   a mão.
3. **Exigência maior na orelha:** confiança ≥ 0,55 perto da orelha (fora dela continua 0,35) e caixa com proporção de
   aparelho (lado maior ÷ lado menor entre 1,3 e 3,2) e tamanho entre 0,35 e 1,6 larguras do rosto no lado maior.
4. **Maioria no tempo:** "no ouvido" exige que **≥ 60% das detecções dos últimos 2 s** tenham candidato aprovado nas
   verificações 1 a 3, com pelo menos 3 aprovados. Detecção solta não mantém o estado.
5. **Memória mais curta e condicionada:** a mão na orelha só segura "no ouvido" por até 5 s se o aparelho tiver sido
   **aprovado** (não só detectado) na orelha nesse tempo.
6. **Caminho legítimo continua:** aparelho confirmado longe da orelha (na mão, se mexendo) e levado à orelha continua
   valendo, porque já foi provado objeto antes.
7. **Nada de imagem guardada:** as verificações usam só o quadro em memória; o registro leva só os números (fração de
   pele, fração fora da mão, confiança) para calibrar depois.
8. **Calibrar com a equipe** (CEL-03): roteiro curto no app de teste e em `ferramentas/avaliar_celular.py`: mão vazia na
   orelha, coçar a orelha, apoiar a cabeça na mão, ajeitar o cabelo, boné; celular no ouvido com 3 aparelhos e capinhas
   diferentes (inclusive capinha cor de pele), de dia e com pouca luz. Metas da spec 009 (pergunta 1).

## Critérios de aceite

| ID | Critério |
|---|---|
| CEL-04 | Detector falso chamando a mão de celular **em 100% das detecções por 30 s**, com a caixa da cor da pele: estado sempre "sem celular", nenhum evento, nenhum alarme |
| CEL-05 | Mesma cena com a caixa dentro do contorno da mão (cor qualquer): "sem celular" |
| CEL-06 | Celular escuro na orelha, parte coberto pela mão (≥ 30% fora do contorno): "no ouvido" em ≤ 2,5 s e evento aos 3 s, como antes |
| CEL-07 | Confiança 0,45 na orelha: não conta; 0,45 longe da orelha: conta como hoje |
| CEL-08 | Caixa quadrada (proporção 1,0) ou do tamanho do rosto inteiro na orelha: não conta |
| CEL-09 | 3 aprovados em 2 s, mas só 40% das detecções: não vira "no ouvido" |
| CEL-10 | Aparelho confirmado na mão, se mexendo, levado à orelha: "no ouvido" (caminho legítimo) |
| CEL-11 | Depois de "no ouvido", aparelho some e a mão fica na orelha: mantém no máximo 5 s; mão vazia sem aprovação anterior: nunca |
| CEL-12 | Referência de pele: com iluminação mudando 30% devagar, a fração de pele da mão continua ≥ 60% |
| CEL-13 | Os números das verificações saem nos detalhes do evento e no CSV de `avaliar_celular.py`; nenhuma imagem é gravada |
| CEL-14 | Custo das verificações < 2 ms por detecção em 640×480 |
| CEL-01, CEL-02 | Continuam passando |
| CEL-03 | Com as gravações da equipe: zero "no ouvido" nas cenas de mão vazia e sensibilidade ≥ 80% nas de celular real (meta inicial; o Matheus decide a final) |

## Riscos

- Capinha cor de pele: pode virar "sem celular" na orelha (preferimos isso a acusar a mão vazia). Mitigação: o
  caminho da decisão 6 e as gravações de calibração.
- Pouca luz: a cor de pele fica menos confiável; a verificação 2 (fora da mão) e a 3 seguram.

## Notas da implementação (19/10/2026)

- As verificações rodam numa classe `PhoneVerifier`, chamada no `PhoneMonitor` logo depois do detector, na mesma
  thread e no mesmo quadro em memória (o `PhoneDetector.detect` só recebe a caixa do rosto, sem os pontos). A decisão
  usa só os números (`PhoneObservation.checks`).
- Referência de pele: bochechas pelos mesmos pontos do cardio (ou posição fixa da caixa do rosto no modo YuNet),
  mediana em YCrCb com média exponencial (τ = 5 s), caduca em 10 s; bochecha tapada é pulada. Fora da faixa de pele
  plausível (Chai e Ngan, 1999), como na câmera infravermelha, a verificação 1 fica de fora e seguram a 2 e a 3.
- Limiares a mais, escolhidos na implementação (hipóteses a calibrar): **lado menor da caixa ≤ 0,8 rosto** (sem isso
  uma caixa do tamanho do rosto passava; aparelho de 15 × 7 cm inclinado 30° dá 0,66); tolerância de cor de 55% da
  distância da referência ao cinza (8 a 18), para preto, cinza e branco nunca contarem como pele; luminância entre
  0,45× e 1,9× a da referência.
- Com aparelho chegando à orelha sem ter sido visto antes, "no ouvido" leva ~1,1 s (antes 0,5 s): dentro dos 2,5 s
  do CEL-06; o evento continua 3 s depois.
- Riscos que só a gravação mostra: aparelho de perfil (caixa pega bochecha e orelha), aparelho inclinado ~45°
  (proporção perto de 1,0), capinha cor de pele, câmera infravermelha.
