# Roteiro CEL-03 · celular no ouvido × mão vazia (5 minutos)

Spec 028. Sentado como se estivesse dirigindo, câmera do notebook na altura do rosto, luz normal da sala.

## Passada 1: ao vivo no RotaGuard Script

Abra o RotaGuard Script, espere a calibração e acompanhe o cartão "Celular" com um cronômetro.

| Tempo | O que fazer |
|---|---|
| 0:00–0:30 | Olhando à frente, mãos no "volante" |
| 0:30–1:00 | Mão vazia parada em concha na orelha esquerda |
| 1:00–1:20 | Coçar a orelha e ajeitar o cabelo atrás dela |
| 1:20–1:50 | Cotovelo apoiado, cabeça apoiada na mão |
| 1:50–2:10 | Boné ou capuz, mão vazia na orelha direita |
| 2:10–2:40 | Celular 1 (capinha escura) no ouvido do lado da janela, falando |
| 2:40–3:10 | Celular 1 no outro ouvido |
| 3:10–3:40 | Celular 2 (outra capinha ou sem capinha) |
| 3:40–4:00 | Celular 3 ou capinha clara / cor de pele |
| 4:00–4:30 | Pegar o celular da mesa, olhar a tela uns 5 s e levar ao ouvido |
| 4:30–5:00 | Apagar a luz principal: 15 s de mão vazia na orelha, depois 15 s de celular no ouvido |

**Passa se:** nunca aparecer "Celular no ouvido" em 0:30–2:10 nem em 4:30–4:45, e aparecer em 1 a 2 s e ficar na
maior parte do tempo (≥ 80%) nos trechos com celular.

## Passada 2: gravar para ter os números

Grave o mesmo roteiro com o app Câmera do Windows (mesma posição, RotaGuard Script fechado), salvando como `cel03.mp4`.
O vídeo tem o seu rosto: fica só no computador, fora do git (`resultados/` e vídeos são ignorados).

```
python ferramentas/analisar_video.py cel03.mp4 --celular --saida resultados/
python ferramentas/avaliar_celular.py cel03_anotacao.csv --resultados resultados/
```

`cel03_anotacao.csv` (já pula 1 s em cada borda de trecho):

```
arquivo;aparelho;inicio_s;fim_s;estado;situacao;cena
cel03.mp4;sem_aparelho;1;29;sem_celular;base;
cel03.mp4;sem_aparelho;31;59;sem_celular;mao_vazia_orelha_esquerda;mao_vazia
cel03.mp4;sem_aparelho;61;79;sem_celular;cocar_orelha_cabelo;mao_vazia
cel03.mp4;sem_aparelho;81;109;sem_celular;cabeca_apoiada_na_mao;mao_vazia
cel03.mp4;sem_aparelho;111;129;sem_celular;bone_mao_orelha_direita;mao_vazia
cel03.mp4;celular1_capinha_escura;131;159;celular_no_ouvido;ouvido_janela;celular_real
cel03.mp4;celular1_capinha_escura;161;189;celular_no_ouvido;ouvido_outro_lado;celular_real
cel03.mp4;celular2;191;219;celular_no_ouvido;ouvido;celular_real
cel03.mp4;celular3_capinha_clara;221;239;celular_no_ouvido;ouvido_capinha_clara;celular_real
cel03.mp4;celular1_capinha_escura;241;254;celular_na_mao;pegar_e_olhar;
cel03.mp4;celular1_capinha_escura;256;269;celular_no_ouvido;levar_ao_ouvido;celular_real
cel03.mp4;sem_aparelho;271;284;sem_celular;pouca_luz_mao_na_orelha;mao_vazia
cel03.mp4;celular1_capinha_escura;286;299;celular_no_ouvido;pouca_luz_ouvido;celular_real
```

**Meta inicial:** zero episódios de "no ouvido" na cena mão vazia e sensibilidade ≥ 80% na cena celular real (o valor
final é decisão do Matheus). Os números `fracao_pele`, `fracao_fora_da_mao` e `confianca_orelha` por quadro servem para
calibrar `SKIN_MAX_FRACTION`, `OUTSIDE_HAND_MIN_FRACTION` e `EAR_MIN_SCORE` em `caixa/vision/phone.py`.
