# Avisos de terceiros

Este projeto usa software, modelos e dados de terceiros. Cada item mantém a sua própria licença.

## Modelos incluídos em `caixa/vision/models/`

| Arquivo | Origem | Autor | Licença | SHA-256 |
|---|---|---|---|---|
| `face_landmarker.task` | [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) (float16, versão 1) | Google | Apache 2.0 | `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` |
| `hand_landmarker.task` | [MediaPipe Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker) (float16, versão 1) | Google | Apache 2.0 (model card) | `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1` |
| `efficientdet_lite0_int8.tflite` | [MediaPipe Object Detector](https://developers.google.com/edge/mediapipe/solutions/vision/object_detector), EfficientDet-Lite0 int8 (COCO 2017) | Google / TensorFlow | Apache 2.0 | `0720bf247bd76e6594ea28fa9c6f7c5242be774818997dbbeffc4da460c723bb` |
| `efficientdet_lite0_float16.tflite` | Idem, float16 | Google / TensorFlow | Apache 2.0 | `4b59100025bea1235a84c1038879a6cccc9f6c49f5e41144e91e74d99e780993` |
| `ocec_s.onnx` | [OCEC](https://github.com/PINTO0309/OCEC) (classificador de olho aberto/fechado) | Katsuya Hyodo | MIT | `9a346a08b256ad70725044cd2aa582858e108c6f45d42a9c3415afc604ba9b64` |
| `face_detection_yunet_2026may.onnx` | [OpenCV Zoo — YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | Shiqi Yu | MIT | `ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0` |

Os modelos do MediaPipe foram baixados de `storage.googleapis.com/mediapipe-models` e conferidos pelo SHA-256.
O EfficientDet-Lite0 foi treinado no COCO 2017; as anotações do COCO são do COCO Consortium, sob CC BY 4.0.

### O que os model cards dizem (leia antes de vender o produto)

- **Face Mesh V2 e Blendshape V2:** não foram feitos para decisões críticas à vida humana.
- **BlazeFace (detector de rosto dentro do Face Landmarker):** lista "qualquer forma de vigilância ou reconhecimento
  de identidade" como aplicação fora do escopo.
- **Hand Tracking (Lite/Full), outubro de 2021:**
  - Fora do escopo: mãos com luvas ou oclusões, "por exemplo quando a mão está segurando objetos", e qualquer
    forma de vigilância ou reconhecimento de identidade.
  - Treinado com dados limitados, "para uso experimental".
  - Por isso, na detecção de celular, a mão é só evidência de apoio: o aparelho detectado e o movimento dele também contam.

A licença Apache 2.0 permite o uso comercial. As restrições acima são orientação de uso do fabricante, não cláusula de
licença.
- Este sistema não identifica pessoas, não guarda nem envia imagens e serve para alertar o próprio motorista.
- Mesmo assim, o envio de eventos para a empresa pode ser lido como monitoramento de trabalhador.
- **Vale avaliar com o jurídico antes da venda:** LGPD, CLT e as orientações dos model cards.

### Licença MIT (OCEC e YuNet)

```
Copyright (c) 2025 Katsuya Hyodo (OCEC)
Copyright (c) 2020 Shiqi Yu (YuNet)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Dados de treino do OCEC

Contém informação do banco de dados **closed-open-eyes**, de Michał Młodawski (2024,
<https://huggingface.co/datasets/MichalMlodawski/closed-open-eyes>), disponibilizado sob a
[Open Data Commons Attribution License v1.0](https://opendatacommons.org/licenses/by/1-0/).

## Bibliotecas Python

Instaladas pelo `pip`, não redistribuídas neste repositório. Versões testadas e licença declarada no pacote:

| Uso | Pacote | Versão | Licença |
|---|---|---|---|
| Dispositivo | mediapipe | 1.0.1 | Apache 2.0 |
| Dispositivo | opencv-contrib-python | 5.0.0.93 | Apache 2.0 |
| Dispositivo | numpy | 2.5.3 | BSD-3-Clause (e componentes 0BSD, MIT, Zlib, CC0) |
| Dispositivo | matplotlib (dependência do MediaPipe; gráfico do `ferramentas/analisar_video.py`) | 3.11.1 | licença própria do matplotlib (estilo PSF) |
| Dispositivo | sounddevice (dependência do MediaPipe) | 0.5.6 | MIT |
| Dispositivo | absl-py, flatbuffers (dependências do MediaPipe) | 2.5.0, 25.12.19 | Apache 2.0 |
| Avaliação (opcional) | scikit-learn | 1.9.0 | BSD-3-Clause |
| Servidor | fastapi | 0.141.1 | MIT |
| Servidor | starlette | 1.6.0 | BSD-3-Clause |
| Servidor | uvicorn | 0.52.4 | BSD-3-Clause |
| Servidor | websockets | 17.1 | BSD-3-Clause |
| Servidor | sqlalchemy | 2.0.52 | MIT |
| Servidor | pydantic, pydantic-core | 2.13.5, 2.46.5 | MIT |
| Servidor | pytz | 2026.3.post1 | MIT |
| Servidor | psycopg, psycopg-binary | 3.3.5 | LGPL-3.0-only |

O psycopg é LGPL-3.0:
- Usá-lo como biblioteca instalada é permitido em software fechado.
- Distribuir o servidor empacotado com ele exige cumprir a LGPL (por exemplo, permitir trocar a biblioteca).
- Vale confirmar com o jurídico antes de vender o servidor como produto fechado.

## Base científica e normativa (métodos reimplementados, sem código copiado)

### Sonolência e piscadas
- Soukupová, T.; Čech, J. *Real-Time Eye Blink Detection using Facial Landmarks*. CVWW, 2016. <https://vision.fe.uni-lj.si/cvww2016/proceedings/papers/05.pdf>
- Wierwille, W. et al., 1994; Dinges, D. et al., 1998. *PERCLOS: A Valid Psychophysiological Measure of Alertness*. FHWA-MCRT-98-006. <https://rosap.ntl.bts.gov/view/dot/113>
- Ingre, M. et al. *Subjective sleepiness, simulated driving performance and blink duration*. J Sleep Res, 2006. doi:10.1111/j.1365-2869.2006.00504.x
- Johns, M. W. et al. *The amplitude-velocity ratio of blinks: a new method for monitoring drowsiness*. Sleep 26 (resumos), 2003. <https://www.mwjohns.com/wp-content/uploads/2017/05/apss_2003_06_03_the_amplitude_velocity_ratio_of_blinks_a_new_method_of_monitoring_drowsiness_poster_69.pdf>
- Johns, M. W. et al. *The Amplitude-Velocity Ratios for Eyelid Movements During Blinks*. APSS, 2005. <https://www.mwjohns.com/wp-content/uploads/2017/05/apss_2005-06-18_the_amplitude-velocity_ratios_for_eyelid_movements.pdf>
- Anund, A.; Fors, C.; Ahlström, C. *The severity of driver fatigue in terms of line crossing*. Eur Transp Res Rev, 2017. doi:10.1007/s12544-017-0248-6
- Friedrichs, F.; Yang, B. *Camera-based drowsiness reference for driver state classification under real driving conditions*. IEEE IV, 2010. <https://www.iss.uni-stuttgart.de/forschung/publikationen/friedrichs_iv2010.pdf>
- Ghoddoosian, R.; Galib, M.; Athitsos, V. *A Realistic Dataset and Baseline Temporal Model for Early Drowsiness Detection*. CVPRW, 2019. arXiv:1904.07312
- Owens, J. et al. *Prevalence of Drowsy Driving Crashes: Estimates from a Large-Scale Naturalistic Driving Study*. AAA Foundation for Traffic Safety, 2018.
- Mulhall, M. et al. *Pre-drive ocular assessment predicts driving performance*. Accid Anal Prev, 2020. doi:10.1016/j.aap.2019.105386
- Cori, J. et al., 2023. J Sleep Res. doi:10.1111/jsr.13785
- Abe, T. *PERCLOS-based technologies for detecting drowsiness: current evidence and future directions*. SLEEP Advances, 2023. doi:10.1093/sleepadvances/zpad006
- Navascues-Cornago, M. et al., 2026. Ocular Surface. doi:10.1016/j.jtos.2026.01.003
- Horne, J. A.; Reyner, L. A. *Sleep related vehicle accidents*. BMJ 310:565–567, 1995. doi:10.1136/bmj.310.6979.565
- Euro NCAP. *Safe Driving — Driver Engagement*, v1.1 (2025, vigência 2026).
- Bocejo e fala como confusão do MAR: FG 2018, Universidade de Cambridge. <https://www.cl.cam.ac.uk/~mmam3/pub/FG2018-HBU-yawining.pdf>

### Sinais compatíveis com ativação atípica
- Takitane, J. et al. *Uso de anfetaminas por motoristas de caminhão em rodovias do Estado de São Paulo: um risco à ocorrência de acidentes de trânsito?* Ciência & Saúde Coletiva, 2013. <https://www.scielo.br/j/csc/a/M3NQ7dq85YwPNftxWprmB3y/?format=html&lang=pt> (efeito rebote: "depressão, fadiga e sono")
- Kuijpers, K. W. K. et al. *Eye reactions under the influence of drugs of abuse as measured by smartphones: a controlled clinical study in healthy volunteers*. Front. Neurosci., 2025. doi:10.3389/fnins.2024.1492246 (pupila dilatada após lisdexanfetamina a ~50 e ~500 lux)
- Shiferaw, B. et al. *Gaze Entropy Measures Reveal Alcohol-Induced Visual Scanning Impairment During Ascending and Descending Phases of Intoxication*. J Stud Alcohol Drugs 80(2), 2019. doi:10.15288/jsad.2019.80.236
- Shiferaw, B.; Crewther, D.; Downey, L. *Gaze entropy measures detect alcohol-induced driver impairment*. Drug Alcohol Depend 204:107519, 2019.
- Frequência de piscadas e drogas dopaminérgicas, com resultados divergentes:
  - *Spontaneous Eye Blink Rate (EBR) Is Uncorrelated with Dopamine D2 Receptor Availability and Unmodulated by Dopamine Agonism in Healthy Adults*. eNeuro, 2017. <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5602106/>
  - *Striatal D1 and D2 receptor availability are selectively associated with eye-blink rates after methylphenidate treatment*. Communications Biology, 2022. <https://www.nature.com/articles/s42003-022-03979-5>

### Celular ao volante
- Dingus, T. A. et al. *Driver crash risk factors and prevalence evaluation using naturalistic driving data*. PNAS 113(10):2636–2641, 2016. doi:10.1073/pnas.1513271113
- NHTSA. *Visual-Manual NHTSA Driver Distraction Guidelines for In-Vehicle Electronic Devices*. Federal Register, 26/04/2013 (olhadas de até 2 s e 12 s no total por tarefa).

### Legislação brasileira
- Código de Trânsito Brasileiro, art. 252, parágrafo único (Lei 13.281/2016): segurar ou manusear celular dirigindo é infração gravíssima.
- Código de Trânsito Brasileiro, art. 67-C (Lei 13.103/2015): até 5 h 30 min de direção ininterrupta para motorista profissional.
- Lei Geral de Proteção de Dados, Lei 13.709/2018: art. 5º, II (dado sensível) e art. 11 (tratamento de dado sensível).

## Projetos que inspiraram a arquitetura (sem código copiado)

- [e-candeloro/Driver-State-Detection](https://github.com/e-candeloro/Driver-State-Detection) (MIT): Face Landmarker com EAR, PERCLOS e pose da cabeça.
- [rezaghoddoosian/Early-Drowsiness-Detection](https://github.com/rezaghoddoosian/Early-Drowsiness-Detection) (MIT): medidas por piscada normalizadas por pessoa.
- [Tandon-A/Drowsiness-Detection-Mediapipe](https://github.com/Tandon-A/Drowsiness-Detection-Mediapipe) (MIT): calibração inicial por pessoa.

## Arquivo existente com licença restritiva

- `ferramentas/modelos/yolov8n.pt` (Ultralytics YOLOv8): AGPL-3.0. Uso em produto comercial fechado exige a licença Enterprise
  da Ultralytics. O código atual não usa esse arquivo; a detecção de celular usa o EfficientDet-Lite0 (Apache 2.0).

Nenhum dataset de sonolência (NTHU-DDD, UTA-RLDD, DMD, YawDD, MRL Eye, DROZY) está incluído neste
repositório nem foi usado para treinar os modelos acima. Esses datasets costumam ser liberados só para pesquisa:
o `ferramentas/avaliar_dataset.py` serve para medir o detector, e usar os resultados em produto exige conferir cada licença.
