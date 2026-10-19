# Pesquisa: datasets e plano de validação do RotaGuard

Data: 19/10/2026. Autor: agente de avaliação (ML). Escopo: sono (olhos fechados 1/3/6 s, PERCLOS, piscadas, bocejo,
cabeceio, olhos esfregados), celular e frequência cardíaca pela face (rPPG, spec 022).

Como ler as marcações:
- **Conferido**: li o texto na fonte oficial (página do dataset, arquivo de licença, metadado DataCite/Zenodo ou API
  do GitHub) nesta data.
- **Hipótese**: não achei texto claro ou só achei fonte secundária. Confirmar antes de usar.
- Nada aqui é parecer jurídico. O que é "uso comercial" precisa ser confirmado com advogado (o PRD já registra que
  falta parecer).

---

## 0. Conclusão em uma página

1. **Quase todo dataset clássico de sono, distração e rPPG proíbe uso comercial** (NTHU-DDD, DMD, AUC, Drive&Act,
   RT-BENE, PURE, MMPD, VIPL-HR, BUAA-MIHR, SCAMPS), ou não tem licença escrita (UTA-RLDD, DROZY, MRL Eye, CEW,
   UBFC-rPPG, MR-NIRP, SUST-DDD, IMVIA-NIR). Gerar número para pitch de produto com esses dados é, muito
   provavelmente, uso comercial. Os termos da AUC dizem isso com todas as letras: "Commercial use includes […]
   Testing commercial systems".
2. **Há quatro fontes com licença que permite uso por empresa**, todas com alguma ressalva:
   - **NITYMED**: carro real em movimento, à noite, câmera no painel. CC BY.
   - **YawDD**: carro real, 107 pessoas. CC BY 4.0 no DataCite.
   - **UL-DD**: simulador de caminhão, câmera IR e frequência cardíaca de referência. CC BY 4.0, acesso por pedido.
   - **Eyeblink8**: piscadas. GPL-3 segundo a página do autor.
3. **Recomendação:** começar por NITYMED, YawDD e UL-DD (pedir já), mais a **gravação própria** com a equipe. A
   gravação própria é a única fonte de número de pitch sem nenhuma dúvida de licença, e a única com pessoas
   brasileiras. Nenhum dataset público tem brasileiros: o UTA-RLDD tem 5 hispânicos não brancos, e nenhum outro
   informa origem latino-americana.
4. **Lacunas nas ferramentas (com arquivo e linha):**
   - vídeo curto nunca sai da calibração (`analisar_video.py:184`);
   - o tempo é `índice/fps`, o que erra em vídeo de celular com fps variável (`analisar_video.py:213`,
     `avaliar_dataset.py:130`);
   - não existe avaliador por evento com latência e intervalo de confiança;
   - não há saída de bocejos e cabeceios por episódio;
   - não há `_cardio.csv` nem `avaliar_cardio.py`;
   - o relatório não registra commit e versões;
   - abaixo de 24 quadros/s, os sinais de duração de piscada desligam (`drowsiness.py:46`), e o Pi deve rodar a
     ~10–15 quadros/s.
5. **Números honestos exigem tamanho de amostra.** Com 0 falsos alarmes em 3 h, o limite superior de 95% ainda é
   ~1 alarme/h (regra de três). Para afirmar "≤ 0,5/h" são precisas ≥ 6 h de gravação sem evento. Para recall
   0,90 ± 0,05 são precisos ~140 eventos.

---

## 1. Datasets públicos por tarefa

Legenda da coluna "Empresa pode?":
- **Sim**: licença escrita que permite uso comercial.
- **Não**: proíbe.
- **?**: sem texto claro; pedir por escrito.

### 1.1 Sono, olhos fechados e piscada

| Dataset | Link oficial | Licença (conferido?) | Empresa pode? | Acesso | Tamanho | Câmera / ambiente | Anotações | Diversidade |
|---|---|---|---|---|---|---|---|---|
| **NTHU-DDD** | [cv.cs.nthu.edu.tw/…/DDD](http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/) | EULA ([PDF](http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/NTHU-DDD-LicenseAgreement.pdf)): "only for non-commercial research and educational purposes"; não redistribuir; assinado pelo chefe de departamento ou laboratório. **Conferido** | **Não** | Formulário assinado por e-mail para cvlablai636@my.nthu.edu.tw | 36 pessoas, ~9,5 h | **IR ativo**, 640×480 AVI, 30 fps de dia e 15 fps à noite. **Laboratório**: cadeira e jogo de direção, comportamento encenado | Sonolento/não sonolento **por quadro**; 5 cenários (sem nada, óculos, óculos escuros, noite, noite com óculos) | "Different ethnicities", sem números (Taiwan). Nenhum brasileiro informado |
| **UTA-RLDD** | [sites.google.com/view/utarldd](https://sites.google.com/view/utarldd/home) | **Nenhuma licença na página**, só pede citação (Ghoddoosian et al., CVPRW 2019). **Conferido que não há texto** | **?** Pedir a reza_ghoddoosian@honda-ri.com | Google Drive aberto | 60 pessoas, 180 vídeos de ~10 min, ~30 h, 111,3 GB | Celular ou webcam da própria pessoa, < 30 fps. **Casa, trabalho ou escola, não dirigindo** | Rótulo por vídeo: 0 alerta, 5 baixa vigilância, 10 sonolento (autodeclarado) | 10 caucasianos, **5 hispânicos não brancos**, 30 indo-arianos e dravidianos, 8 do Oriente Médio, 7 do Leste Asiático; 51 H e 9 M; óculos em 21 de 180 vídeos. Rosto publicável só de 36 das 60 pessoas |
| **DROZY** | [drozy.ulg.ac.be](http://www.drozy.ulg.ac.be/) (arquivo no ORBi da ULiège) | **Não achei licença** (página e ORBi). **Hipótese**: só pesquisa | **?** | Download no ORBi | 14 pessoas (3 H e 11 M, segundo o artigo do SUST-DDD) | Kinect v2 **NIR** 512×424, 30 fps (alguns testes a 15 fps); **laboratório** | KSS por teste, tempos de reação do PVT, polissonografia (EEG, EOG, ECG, EMG), 68 pontos do rosto | Não informado |
| **YawDD** | [IEEE DataPort](https://ieee-dataport.org/open-access/yawdd-yawning-detection-dataset), DOI 10.21227/e1qm-hb90 | **CC BY 4.0** no DataCite do DOI e pelos termos do DataPort ([termos, §g](https://ieee-dataport.org/ieee-dataport-terms-use)). As instruções dos autores dizem "You can use all videos for research" e proíbem publicar imagem de quem marcou "No". **Conferido** | **Sim (CC BY)**, com ressalva: confirmar por e-mail e nunca publicar quadro dos "No" | Open access (conta IEEE grátis) | 351 vídeos (322 com câmera no retrovisor e 29 no painel); 107 pessoas (57 H e 50 M, segundo o SUST-DDD e o UL-DD) | **RGB** 640×480, 30 fps, **carro real** (outros autores dizem que estava parado), luz natural | **Sem rótulos**: o nome do vídeo diz normal, falando/cantando ou bocejando | "Different ethnicities", com e sem óculos e óculos escuros (Canadá). Sem números por etnia |
| **CEW** | [parnec.nuaa.edu.cn/…/ClosedEyeDatabases](https://parnec.nuaa.edu.cn/_upload/tpl/02/db/731/template731/pages/xtan/ClosedEyeDatabases.html) | **Sem licença**. Fotos de olhos fechados tiradas "directly from Internet" e de olhos abertos do LFW: direito autoral de terceiros | **Não usar** em produto | Download direto (rar) | 2.423 pessoas (1.192 de olhos fechados) | Fotos da internet, recortes de 24×24 | Aberto ou fechado por imagem | Variada, sem dado |
| **MRL Eye** | [mrl.cs.vsb.cz/eyedataset.html](https://mrl.cs.vsb.cz/eyedataset.html) | "Publicly available", **sem licença**. **Conferido que não há texto** | **?** Pedir a Radovan Fusek | Zip direto ([mrlEyes_2018_01.zip](http://mrl.cs.vsb.cz/data/eyedataset/mrlEyes_2018_01.zip)) | 84.898 recortes de olho, 37 pessoas (33 H e 4 M) | **IR**, 3 sensores (RealSense 640×480, IDS 1280×1024, Aptina 752×480), "acquired in real conditions" de motorista | Aberto ou fechado, óculos, reflexo (nenhum, pequeno, grande), luz boa ou ruim, sensor; ~15 mil pupilas | Tchéquia; sem dado de pele |
| **ZJU Eyeblink** | Página original [cs.zju.edu.cn/~gpan/…](http://www.cs.zju.edu.cn/~gpan/database/db_blink.html) **fora do ar (404)** | Desconhecida. As anotações refeitas estão no [blinkingmatters](https://www.blinkingmatters.com/research) (GPL-3) | **?** | Só por espelhos de terceiros (**Hipótese**) | 80 clipes de poucos segundos, 20 pessoas, 255 a 261 piscadas | Webcam 320×240, ~30 fps, parado | Piscadas | "They are Asian ethnicity" |
| **Eyeblink8** e **Researcher's night** | [blinkingmatters.com/research](https://www.blinkingmatters.com/research) | Página: "All data available here is under **GPL3** license". O PDF de licença da mesma página é do **Silesian5** (só acadêmico) e não se aplica ao Eyeblink8. **Conferido**; GPL em dados é incomum (**Hipótese**: permite uso interno comercial) | **Sim?** Confirmar com o autor (A. Fogelton) | Eyeblink8: zip direto. Researcher's night: "available on demand" | Eyeblink8: 8 vídeos, 4 pessoas (1 de óculos), **408 piscadas**, 70.992 quadros 640×480. Researcher's night: 107 vídeos, >100 pessoas, 1.849 piscadas, 15 e 30 fps | Webcam, casa ou evento, H.264 de baixa qualidade | Intervalo de cada piscada **por olho**, com completa ou incompleta | Eslováquia; sem dado de pele |
| **RT-BENE** | [Zenodo 3685316](https://zenodo.org/records/3685316) | **CC BY-NC-SA 4.0**, "Commercial usage is not permitted" (API do Zenodo). **Conferido** | **Não** | Download no Zenodo | >200 mil recortes de olho, >10 mil fechados | RGB de laboratório (RT-GENE "noglasses") | Olho aberto ou fechado por imagem | Não informado |
| **DMD** (Vicomtech) | [dmd.vicomtech.org](https://dmd.vicomtech.org/) e [GitHub](https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset) | **CC BY-NC-ND 4.0** + "This dataset can only be used for **academic purposes**. Any other use beyond that is prohibited." **Conferido** | **Não** | Links no site, separados por Drowsiness, Distraction e Gaze & Hands | Originalmente 37 motoristas e ~41 h (fonte secundária). **Revisão de 2026: ficou só RGB do carro real**, sem simulador, IR e profundidade; liberado sem restrição só para os sujeitos 1, 5, 6, 7, 9, 10, 13, 14, 23, 28, 29, 33, 36 e 37 | RealSense D415/D435 (rosto, corpo e mãos); carro real, parado nas ações perigosas | VCD/OpenLABEL: **bocejo com e sem mão, microssono, direção sonolenta**, olhar, mãos, celular (E/D), mensagem (E/D) | 27% mulheres, idade média de 30, 10 de óculos (Espanha) |
| **SUST-DDD** | Artigo: [Zenodo 6519933](https://zenodo.org/records/6519933) (o CC BY 4.0 desse registro é **do artigo**, não dos vídeos) | **Não achei licença nem página de download dos vídeos**. **Hipótese**: pedir aos autores | **?** Pedir a esra.kavalci@sivas.edu.tr | Por pedido aos autores (**Hipótese**) | 19 motoristas de 24 a 42 anos; 2.074 clipes de 10 s (975 sonolento e 1.099 não), 224×224 | **Celular do próprio motorista, direção real**, pouca luz (ida e volta do trabalho) | Sonolento/não sonolento por clipe, voto de 3 jurados | Turquia |

Fontes extras encontradas na busca:

| Dataset | Link | Licença | Empresa pode? | O que tem |
|---|---|---|---|---|
| **NITYMED** | [datasets.esdalab.ece.uop.gr](https://datasets.esdalab.ece.uop.gr/) e [IEEE DataPort](https://ieee-dataport.org/documents/nitymed) (DOI 10.21227/85xe-3f88) | Site: "License: Creative Commons Attribution". DataCite do DOI: **CC BY 4.0**. **Conferido** | **Sim (CC BY)** | **130 vídeos de carro real em movimento, à noite, câmera no painel**. 21 motoristas (11 H e 10 M, cabelo, barba, óculos variados). 107 vídeos de bocejo (3 bocejos cada, 15–25 s) e 21 de microssono (~2 min, com fala e olhar para os lados). 25 fps, 720p e 1080p. Formulário aceita **"business/academic email"**. Sem anotação por tempo (**Hipótese**: só pastas por categoria) |
| **UL-DD** | [Zenodo 17978727](https://zenodo.org/records/17978727) e [artigo](https://arxiv.org/abs/2507.13403) | **CC BY 4.0** (API do Zenodo e artigo). Acesso "restricted": pedido ao autor. **Conferido** | **Sim (CC BY)**. **Hipótese**: o termo de pedido pode acrescentar regras; ler ao receber | 19 pessoas (15 H e 4 M, 25–40 anos), **2 sessões de 40 min (alerta e sonolento, KSS ≥ 6 para começar)**, KSS a cada 4 min. **Câmera IR** 640×360 a 60 fps, recortada em 240×220; ZED 2; câmera de postura. **FC de referência**: Empatica E4 (BVP 64 Hz, FC 1 Hz, IBI) e Checkme O2 Max. American Truck Simulator com 3 monitores. Aprovado por IRB; participantes avisados de que os dados seriam liberados |
| **3MDAD** | [HAL](https://hal.archives-ouvertes.fr/hal-03321535) | **Não achei licença** | **?** | Carro real, >60 motoristas, 16 ações, RGB + IR + profundidade, frontal e lateral (Tunísia). Só citado |

### 1.2 Celular e distração

| Dataset | Link | Licença | Empresa pode? | Acesso | Tamanho | Câmera / ambiente | Anotações | Diversidade |
|---|---|---|---|---|---|---|---|---|
| **DMD** | idem acima | CC BY-NC-ND 4.0, só acadêmico. **Conferido** | **Não** | idem | idem | RGB do carro real | Celular E/D, mensagem E/D, beber, rádio, cabelo e maquiagem, alcançar atrás, mãos no volante | idem |
| **State Farm Distracted Driver** | [Kaggle](https://www.kaggle.com/competitions/state-farm-distracted-driver-detection/rules) | A página de regras só abre com login e JavaScript; **não consegui ler**. **Hipótese**: as regras de competição limitam os dados à competição e a uso não comercial e proíbem redistribuir; projetos no GitHub dizem que "Kaggle's competition rules do not allow redistributing them" ([exemplo](https://github.com/Artificialhuman74/distracted-driver-detection)) | **Não** (até ler as regras logado) | Conta Kaggle + aceitar as regras | Dezenas de milhares de imagens em 10 classes (**não conferido**) | Câmera de painel lateral, carro real | Classe por imagem (celular D/E, mensagem D/E etc.) | Não informado |
| **AUC Distracted Driver (V1/V2)** | [heshameraqi.github.io/distraction_detection](https://heshameraqi.github.io/distraction_detection) | Termos: "Any commercial use of the dataset is strictly prohibited. Commercial use includes […] **Testing commercial systems**". **Conferido** | **Não** | Termo assinado por e-mail aos autores | V2: 44 motoristas, 14.478 quadros, 10 classes (celular D 1.256, celular E 1.320, mensagem D/E…) | 5 carros reais | Classe por quadro | Egito 37, Alemanha 2, EUA, Canadá, Uganda, Palestina e Marrocos 1 cada; 29 H e 15 M |
| **Drive&Act** | [driveandact.com](https://www.driveandact.com/) | "Copyright Fraunhofer IOSB. **Usage for research only.**" **Conferido** | **Não** | Download aberto desde 2021 | 12 h, 29 sequências longas, 83 rótulos hierárquicos | NIR, profundidade e cor, 5 vistas; Audi A3 em **simulador** com telas de projeção (material suplementar, **fonte secundária**) | Atividades em 3 níveis, pose 3D do corpo e da cabeça | Não informado (**Hipótese**: 15 participantes) |

Para **mão no ouvido sem celular**, **celular no colo** e **celular no suporte**, que são os negativos que mais derrubam
o `phone.py`, nenhum dataset aberto tem rótulo dedicado. Isso tem de vir da gravação própria (§3).

### 1.3 Frequência cardíaca pela face (rPPG)

| Dataset | Link | Licença | Empresa pode? | Acesso | Tamanho | Câmera / ambiente | Referência | Diversidade |
|---|---|---|---|---|---|---|---|---|
| **UBFC-rPPG** | [sites.google.com/view/ybenezeth/ubfcrppg](https://sites.google.com/view/ybenezeth/ubfcrppg) | "shared for research purpose", **sem licença formal**. **Conferido** | **?** Pedir a Y. Benezeth | Google Drive aberto | Conjunto 1: 8 vídeos. Conjunto 2: 42 vídeos (jogo de matemática para subir a FC) | Logitech C920, 640×480, 30 fps, **sem compressão**, ~1 m, ambiente interno | Oxímetro CMS50E (onda e FC) | Não informado (**Hipótese**: maioria de pele clara) |
| **UBFC-Phys** | [site](https://sites.google.com/view/ybenezeth/ubfc-phys), [IEEE DataPort](https://ieee-dataport.org/open-access/ubfc-phys-2) | **Conflito**: DataCite do DOI do DataPort (10.21227/5da0-7344) diz **CC BY 4.0**; DataCite do DOI do dat@UBFC (10.25666/dataubfc-2022-05-05) diz **CC BY-NC-SA 3.0**. **Conferido** | **?** Tratar como não comercial até os autores confirmarem | DataPort (conta grátis) ou dat@UBFC | 56 pessoas, 3 tarefas (repouso, fala, aritmética; estresse inspirado no TSST) | RGB, laboratório | Pulseira Empatica (BVP e EDA) | Não informado |
| **PURE** | [TU Ilmenau](https://www.tu-ilmenau.de/universitaet/fakultaeten/fakultaet-informatik-und-automatisierung/profil/institute-und-fachgebiete/institut-fuer-technische-informatik-und-ingenieurinformatik/fachgebiet-neuroinformatik-und-kognitive-robotik/data-sets-code/pulse-rate-detection-dataset-pure) | "We only accept requests from academic institutions […] **Requests from companies cannot be considered** […] due to licensing restrictions". **Conferido** | **Não** | E-mail acadêmico para nikr-datasets-request@tu-ilmenau.de | 10 pessoas (8 H e 2 M), 60 sequências de 1 min, 6 situações de movimento | 640×480, 30 Hz, laboratório | Oxímetro, FC de 42 a 148 bpm | Alemanha |
| **MMPD** | [GitHub](https://github.com/McJackTang/MMPD_rPPG_dataset) | "This dataset is built for academic use. **Any commercial usage is banned.**" O código do repositório é MIT, mas isso não vale para os dados. **Conferido** | **Não** | Termo assinado, enviado por **professor** com e-mail institucional | 33 pessoas, 11 h (1.152 mil quadros); 370 GB (320×240) ou 48 GB (80×60) | **Celular**; 4 luzes (LED fraco e forte, incandescente, natural); parado, girando, falando, andando | Onda de PPG | **Pele Fitzpatrick 3 a 6**, óculos, cabelo cobrindo, maquiagem (China) |
| **MR-NIRP (Car e Indoor)** | [computationalimaging.rice.edu/mr-nirp-dataset](https://computationalimaging.rice.edu/mr-nirp-dataset/) | **Sem licença na página**, só citação. README dentro do Drive (não lido). **Hipótese** | **?** Pedir aos autores (Rice e MERL) | Google Drive aberto | Car: 190 vídeos, 19 pessoas. Indoor: 15 vídeos, 8 pessoas | **RGB + NIR 940 e 975 nm**. Car: **dirigindo** e parado na garagem; sol, nublado, chuva, dia e noite | Oxímetro | Não informado |
| **VIPL-HR** | [vipl.ict.ac.cn](https://vipl.ict.ac.cn/resources/databases/201811/t20181129_32716.html) | EULA: só universidades e institutos, "research purpose only"; proibido material comercial e redistribuir. **Conferido por resumo da busca** (o PDF do EULA não foi lido) | **Não** | Termo assinado por funcionário efetivo, e-mail institucional | 107 pessoas; 2.378 vídeos visíveis e 752 NIR | Várias câmeras (inclusive celular), luz e movimento | FC e SpO2 | China (**Hipótese**) |
| **COHFACE** | [Idiap](https://www.idiap.ch/en/scientific-research/data/cohface) e [Zenodo 4081054](https://zenodo.org/record/4081054) | Zenodo com **acesso "restricted"**: os termos só aparecem no pedido. **Hipótese**: EULA da Idiap só para pesquisa | **?** Provavelmente não | Pedido no Zenodo | 40 pessoas (12 M e 28 H), 160 vídeos de 1 min | Logitech C525 640×480, **20 Hz**, comprimido | BVP e respiração | Suíça |
| **BUAA-MIHR** | [GitHub](https://github.com/xilin-x/Large-scale-Multi-illumination-HR-Database) | **CC BY-NC-SA 4.0**; "released to universities and research institutes for research purposes only". **Conferido** | **Não** | Termo assinado de e-mail institucional | 15 pessoas (12 H e 3 M, 18–30 anos), 165 vídeos de 60 s | C930e 640×480, 30 fps, sem compressão, **sala escura de 1 a 100 lux** | CMS50E | China |
| **IMVIA-NIR** (extra) | [sites.google.com/view/ybenezeth/imvia-nir](https://sites.google.com/view/ybenezeth/imvia-nir) | "Publicly available", **sem licença**. **Hipótese** | **?** | Link de download na página | 10 pessoas, 20 vídeos (parado e falando) | **NIR 850 nm**, IDS 1280×1024, 20 fps MJPEG | Empatica E4 BVP 64 Hz (sincronia manual) | Não informado |
| **UL-DD** (extra) | idem §1.1 | **CC BY 4.0** | **Sim** | Pedido | 19 × 2 × 40 min | **IR** 60 fps | FC 1 Hz e BVP 64 Hz (Empatica), oxímetro de pulso Checkme | Demografia não coletada |
| **SCAMPS** (sintético) | [GitHub](https://github.com/danmcduff/scampsdataset) | **Research Use of Data Agreement v1.0**: "you may not use the Data or any Results in any commercial offering […] (or to improve any product or service)". **Conferido** | **Não**, nem para testes de regressão do produto | Download direto | 2.800 vídeos sintéticos | Avatar renderizado | FC, respiração e IBI exatos | Sintética |

### 1.4 O que a licença significa na prática

- **NC (NonCommercial)** do Creative Commons: "not primarily intended for or directed towards commercial advantage or
  monetary compensation" ([CC BY-NC 4.0, legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode)).
  Medir o desempenho do RotaGuard para vender o RotaGuard é, muito provavelmente, uso comercial (**Hipótese
  jurídica**, confirmar com advogado). A AUC escreve isso explicitamente.
- **Sem licença escrita ≠ livre.** Sem licença, valem os direitos autorais e o direito de imagem dos participantes.
  Pedir por escrito ("podemos usar para avaliação interna de produto comercial e citar o número agregado, sem
  imagens?").
- **CC BY permite uso comercial com atribuição**, mas não resolve imagem de terceiros. Os autores do YawDD pedem
  explicitamente que não se publique quadro de quem marcou "No". Regra para nós: dataset CC BY entra em número
  agregado e em teste interno; imagem de pessoa de dataset nunca vai para pitch ou site.
- **Registro de licenças**: guardar a cópia do texto da licença e a data de download por dataset em
  `docs/validacao/licencas/` (ver VAL-01).

### 1.5 Conflitos com o que já está escrito (para o Matheus decidir)

- **Vault, `12 - Cardio pela face (rPPG).md`**, "Validar depois: UBFC-rPPG e MR-NIRP Car". Os dois não têm licença
  que cubra uso por empresa. A recomendação aqui troca a ordem: **UL-DD** (IR, CC BY 4.0) e **gravação própria com
  oxímetro** primeiro; UBFC e MR-NIRP só depois de autorização por escrito.
- **`docs/pesquisa/2026-10-19-pulso-pela-camera-rppg.md:655`**, MMPD "Não conferido". Agora conferido: só uso
  acadêmico, comercial proibido.
- **Vault, `05 - Privacidade, licencas e model cards.md`**, "Datasets de sonolência […] Em geral só pesquisa". Está
  certo, mas faltava a exceção: NITYMED, YawDD e UL-DD são CC BY.
- **DMD**: a revisão de 2026 tirou IR, profundidade e simulador. Números de artigos antigos com DMD IR não são mais
  reproduzíveis.

---

## 2. Quais usar primeiro e plano de avaliação

### 2.1 Escolha (licença + parecido com cabine)

| Ordem | Fonte | Por quê | Mede | Ressalva |
|---|---|---|---|---|
| 1 | **Gravação própria** (§3) | Único número de pitch sem dúvida de licença; pessoas brasileiras; negativos certos (mão no ouvido, colo, suporte); oxímetro sincronizado | Tudo | Encenado: sono real não aparece |
| 2 | **NITYMED** | **Carro real em movimento, à noite, câmera no painel**; CC BY; aceita e-mail de empresa | Bocejo (3 por vídeo, dá para conferir a contagem), microssono, falsos alarmes com fala e olhar para os lados | Precisa anotar por tempo; vídeos curtos exigem perfil (ver §2.4) |
| 3 | **YawDD** | Carro real, 107 pessoas, óculos e óculos escuros, CC BY 4.0 | Bocejo contra **falar e cantar** (o falso positivo clássico); robustez do rosto; óculos escuros | Sem rótulos por tempo; não publicar imagem dos "No" |
| 3b | **UL-DD** (pedir já) | CC BY 4.0, **IR** como a NoIR, **sono de verdade** (KSS), 40 min contínuos, FC de referência | Falsos alarmes por hora na sessão alerta, latência e detecção na sessão sonolenta, **rPPG em IR** | Simulador; recorte 240×220 pequeno; referência de pulso por pulseira, não por ECG |
| Extra | **Eyeblink8** | Única base de piscada com licença que parece permitir uso comercial (GPL-3) | F1 de piscada com tolerância | Pequena (4 pessoas); confirmar a licença com o autor |

Só para P&D interno, e só se os autores autorizarem por escrito: UTA-RLDD (sono real em 10 min), UBFC-rPPG e
MR-NIRP Car. Sem autorização, ficam fora até de teste interno, porque o número sairia contaminado para o pitch.

### 2.2 Métricas

**Por evento** (alarme e episódio):

| Métrica | Definição | Onde |
|---|---|---|
| Precisão, recall, F1 | Detecção do tipo X conta como acerto se cair em `[início, fim + 0,5 s]` de um evento anotado do mesmo tipo. Um evento casa com no máximo uma detecção. Detecções repetidas dentro do mesmo evento são fundidas, não contam como falso positivo | `avaliar_eventos.py` (novo) |
| **Falsos alarmes por hora** | Alarmes sonoros sem evento anotado ÷ horas de vídeo **sem** evento positivo (tempo negativo). Separar por condição (falando, comendo, óculos escuros, noite) | idem |
| Intervalo de 95% para a taxa | Poisson exato. Com 0 alarmes em T horas, limite superior ≈ 3/T por hora (regra de três). Exemplo: 0 em 3 h dá ≤ 1,0/h | idem |
| **Latência do alarme** | `t_alarme − início_anotado`. Reportar também `t_alarme − (início + limiar)`, com limiar 1, 3 ou 6 s, porque o O1 do PRD fala em "até 1,5 s depois de 1 s de olhos fechados". Mediana, p95 e máximo | idem |
| Recall por limiar | Fechamentos de ≥1 s → `microssono`; ≥3 s → `sono`; ≥6 s → `nao_responsivo` (`drowsiness.py:71-75`) | idem |
| Zona cinzenta | Fechamentos anotados entre 0,8 e 1,2 s não contam nem como acerto nem como falso positivo do microssono. Reportar **com e sem** a zona | idem |

**Por quadro** (estado contínuo):

| Métrica | Definição |
|---|---|
| Olho fechado por quadro | Matriz de confusão aberto × fechado contra os intervalos anotados (precisão, recall, F1) |
| PERCLOS | Erro absoluto médio do PERCLOS por janela de 60 s, anotado × medido |
| Celular | Matriz 4×4 por quadro (já existe em `avaliar_celular.py`) + recall por evento para os alarmes (≥2 s na mão ou no ouvido) |
| Piscada | F1 com tolerância de 0,25 s (já existe em `avaliar_piscadas.py`) |

**Por vídeo ou janela** (sono real, UL-DD e UTA-RLDD): precisão, recall e F1 por janela (já existe em
`avaliar_dataset.py`), mais **AUC** por sessão alerta × sonolenta e latência até o primeiro alarme na sessão
sonolenta.

**Cardio (bpm):**

| Métrica | Definição |
|---|---|
| MAE e RMSE (bpm) | Entre o bpm mostrado e a referência, em janelas de 10 s alinhadas |
| Pearson r | Por sessão e no total |
| PTE6 | % de janelas com erro < 6 bpm (a métrica do MR-NIRP; ver a pesquisa rPPG do repositório, linhas 325-333) |
| **Cobertura** | % do tempo em que o app mostra número (o resto é "sinal fraco", "movimento" ou "medindo"). Erro e cobertura **sempre juntos**: dá para ter MAE baixo mostrando número só 10% do tempo |
| Bland-Altman | Viés e limites de concordância (gráfico no relatório) |
| Atraso | Atraso entre rPPG e referência por correlação cruzada (oxímetros mostram média de alguns batimentos). **Hipótese**: alguns segundos; medir |

**Intervalo de confiança em tudo:**
- Wilson para precisão e recall. Exemplo de teste: 9 de 10 dá [0,596; 0,982].
- Bootstrap **por sujeito** (reamostra pessoas, não janelas) para F1, MAE e falsos alarmes por hora.
- O aviso que já existe em `avaliar_dataset.py` (janelas sobrepostas são otimistas) passa a ter números.

**Tamanho de amostra (para não prometer o que não dá para medir):**

| Quer afirmar | Precisa de |
|---|---|
| Recall 0,90 ± 0,10 (95%) | ~35 eventos |
| Recall 0,90 ± 0,05 | ~140 eventos |
| Falsos alarmes ≤ 1/h, vendo 0 | ≥ 3 h de vídeo negativo |
| Falsos alarmes ≤ 0,5/h, vendo 0 | ≥ 6 h de vídeo negativo |
| MAE de bpm por pessoa | ≥ 10 pessoas, ≥ 5 min cada (**Hipótese**: ordem de grandeza) |

### 2.3 Verdade de referência a partir das anotações

| Fonte | O que vem pronto | Como virar verdade |
|---|---|---|
| NITYMED | Pasta (bocejo ou microssono) e "3 bocejos por vídeo" | Anotar `inicio_s;fim_s;evento` (bocejo, olhos_fechados, falando, olhando_lado). Conferir 3 bocejos por vídeo como checagem automática do anotador |
| YawDD | Tipo pelo nome do arquivo (normal, falando/cantando, bocejando) | Vídeos "normal" e "falando/cantando" valem como **negativos inteiros** (todo bocejo detectado é falso positivo). Vídeos "bocejando": anotar os intervalos |
| UL-DD | KSS a cada 4 min (10 por sessão); FC 1 Hz | Janela de 4 min com KSS ≤ 5 = alerta; ≥ 7 = sonolento; 6 = fora (zona cinzenta). Sessão alerta inteira = tempo negativo para falsos alarmes/h (só de "sono", não de celular). FC 1 Hz = referência do cardio |
| UTA-RLDD (se autorizado) | 0/5/10 por vídeo | Já suportado: `avaliar_dataset.py` com `--baixa-vigilancia` |
| Eyeblink8 | Arquivos `.tag` com piscada por quadro e por olho (**Hipótese** de formato; conferir no zip) | Conversor `.tag` → `quadro_inicio;quadro_fim` e `avaliar_piscadas.py --fps` |
| Gravação própria | Registro de **sinais do roteiro** (`roteiro_log.csv`, §3.3) | O anotador só ajusta início e fim; 20% anotado por duas pessoas, com concordância medida (F1 entre anotadores ≥ 0,9 para os eventos; kappa por quadro) |

**Vocabulário único** das anotações (CSV com ponto e vírgula, como os modelos que já existem em
`ferramentas/anotacoes/`):

```
video;sujeito;inicio_s;fim_s;evento;condicao;anotador;obs
```

- **Eventos positivos:** `piscada`, `olhos_fechados` (a duração define 1/3/6 s), `bocejo`, `bocejo_com_mao`,
  `cabeceio`, `olhos_esfregados`, `celular_ouvido`, `celular_mao`, `olhando_celular`.
- **Negativos:** `celular_colo`, `celular_suporte`, `mao_no_ouvido_sem_celular`, `falando`, `cantando`, `comendo`,
  `ajustando_oculos`, `olhando_retrovisor`, `rosto_fora`.
- **Condições:** `sem_acessorio`, `oculos`, `oculos_escuros`, `bone`, `pouca_luz`, `contraluz`, `ir`.

### 2.4 Como rodar com o que já existe e o que falta

**Hoje dá para rodar** (por vídeo):

```bash
python ferramentas/analisar_video.py video.mp4 --celular --saida resultados/        # _quadros, _piscadas, _janelas, _eventos, _gestos
python ferramentas/avaliar_piscadas.py resultados/video_piscadas.csv anot_piscadas.csv --tolerancia 0.25
python ferramentas/avaliar_gestos.py resultados/video_gestos.csv anot_gestos.csv
python ferramentas/avaliar_celular.py anot_celular.csv --resultados resultados/
python ferramentas/avaliar_dataset.py extrair lista.csv --saida avaliacao/ && python ferramentas/avaliar_dataset.py avaliar avaliacao/ --classificador
```

**O que falta, por ordem de impacto:**

| # | Lacuna | Onde | Consequência |
|---|---|---|---|
| F1 | Vídeo curto nunca sai da calibração: `max(30.0, duration / 3)` dá 30 s para um clipe de 20 s | `ferramentas/analisar_video.py:184` | NITYMED (bocejos de 15–25 s) e YawDD curtos não geram **nenhum** evento. Solução: `--perfil` de outro vídeo do mesmo motorista (já existe), ou um novo `--perfil-padrao` (perfil populacional, marcado no relatório) |
| F2 | O tempo é `index / fps` | `analisar_video.py:213`, `avaliar_dataset.py:130` | Vídeo de celular costuma ter fps variável: o tempo escorrega e a latência sai errada. Usar `CAP_PROP_POS_MSEC` ou um arquivo de horários por quadro |
| F3 | Não há avaliador **por evento** de alarme (microssono, sono, não responsivo, bocejo, cabeceio, celular), com latência e falsos alarmes por hora | — | Sem número para O1 e O4. Criar `avaliar_eventos.py`, que lê o `_eventos.csv` (`analisar_video.py:313-318`) |
| F4 | O casamento é **pelo centro** com tolerância | `caixa/vision/evaluation.py:47` | Bom para piscada; ruim para fechamento de 3–6 s e bocejo (a detecção sai no meio ou no fim). Acrescentar o casamento "detecção dentro de `[início, fim + margem]`" |
| F5 | Bocejos e cabeceios não saem por episódio (só contagem em 10 min na janela) | `drowsiness.py:394` e `:303` guardam só o instante | Gravar `_bocejos.csv` e `_cabeceios.csv` (instante, e duração quando houver) |
| F6 | Sem saída de cardio | `analisar_video.py` não tem `--cardio` | Gravar `_cardio.csv` (`tempo_s, estado, bpm, confianca, snr_db, canal`) e criar `avaliar_cardio.py`. **Atenção RNF-16**: é dado de saúde; o CSV fica só na máquina de avaliação, nunca no git |
| F7 | Sem intervalos de confiança | `evaluation.py:104-118` (taxa e latência sem IC) | Números de pitch sem barra de erro. Acrescentar Wilson, Poisson exato e bootstrap por sujeito |
| F8 | Sem simulação do Pi | — | `MIN_FPS_FOR_DURATION = 24` (`drowsiness.py:46`) desliga os sinais de duração de piscada abaixo de 24 fps, e o RNF-02 prevê ~10 fps no Pi. Acrescentar `--fps-alvo 12 --largura 640` (subamostragem) e reportar 30 × 12 fps |
| F9 | Relatório sem identificação | `_resumo.json` tem `versao_drivesafe` (`analisar_video.py:364`), mas não o commit | Gravar commit (`git rev-parse HEAD`), flag de árvore suja, versões de Python, MediaPipe e OpenCV, hash dos argumentos e dos limiares, hash do manifesto do dataset |
| F10 | Sem conversores de anotação | — | Label Studio (JSON), CVAT (XML "for video") e ELAN (texto tabulado) → CSV padrão; Eyeblink8 `.tag` → CSV |
| F11 | `avaliar_dataset` só faz janelas sobrepostas | `avaliar_dataset.py` (60 s a cada 10 s) | Opção de janelas sem sobreposição e agregação por vídeo e sessão, para AUC |

### 2.5 Relatório reprodutível: `docs/validacao/AAAA-MM-DD-<tema>.md`

Um arquivo por rodada, gerado por script (proposta: `ferramentas/relatorio_validacao.py`) a partir dos JSONs. O
JSON bruto fica ao lado, em `docs/validacao/AAAA-MM-DD-<tema>.json`, **só com números agregados** (sem quadro, sem
pontos do rosto, sem bpm por pessoa nomeada).

```markdown
---
data: 2026-10-26
tema: nitymed-yawdd-bocejo-microssono
commit: <sha>  (árvore limpa: sim)
python: 3.14.x · mediapipe: x.y.z · opencv: x.y.z
maquina: notebook <modelo>, CPU <…>, sem GPU
fps_processado: 30 (e 12 no modo Pi)
limiares: hash <sha256 de vision/*.py constantes> · arquivo: limiares.json
dataset: NITYMED 720p, licença CC BY (cópia em docs/validacao/licencas/nitymed.txt, baixada em 2026-10-20)
manifesto: lista.csv (sha256 <…>), 128 vídeos, 21 sujeitos, 0,0 h de vídeo negativo
divisao: desenvolvimento = sujeitos 1-10; teste = 11-21 (congelado antes de rodar)
plano_pre_registrado: docs/validacao/plano-pre-registrado.md (commit <sha>)
comando: python ferramentas/relatorio_validacao.py --config validacao/nitymed.toml
---

# Resultado
| Evento | n anotado | Precisão [IC95] | Recall [IC95] | F1 | Latência mediana / p95 | FA/h [IC95] |
…
# Por condição (óculos, noite, pele Monk 1-3 / 4-7 / 8-10)
# Pior sujeito e pior condição
# Falhas típicas (tempo e motivo, sem imagem de pessoa)
# O que NÃO foi verificado (Pi, IR NoIR, sono real, caminhão)
# Licença e atribuição
```

Regras:
1. **Pré-registrar** metas e divisão de sujeitos **antes** de rodar o conjunto de teste (VAL-02).
2. Limiar ajustado só nos sujeitos de desenvolvimento. Teste rodado uma vez; nova rodada = novo relatório, com o
   motivo escrito.
3. Duas rodadas com o mesmo commit e o mesmo manifesto geram o **mesmo JSON** (teste de determinismo).
4. Todo número do pitch aponta para um relatório e um commit (VAL-13).

---

## 3. Protocolo de gravação própria (sem Raspberry Pi)

### 3.1 Segurança e local

- **Nunca gravar olho fechado, bocejo encenado ou celular com o carro em movimento.** Carro parado (motor desligado,
  freio de mão) ou mesa com volante. É a regra que o DMD também seguiu ("activities that are considered as
  illegal/dangerous […] were made with the car stopped").
- Câmera na **posição da caixa**: painel ou coluna A, 60–80 cm do rosto, um pouco abaixo da linha dos olhos.
- Gravar com **duas câmeras ao mesmo tempo**:
  - webcam do notebook a 30 fps (é a câmera do RotaGuard Teste);
  - celular no painel a 30 fps, com fps fixo se o app permitir. Celular costuma gravar com fps variável; ver F2.
- Formato: 1280×720 ou 640×480, bitrate alto (≥ 8 Mb/s) ou sem perdas. Travar exposição e foco quando der
  (**Hipótese**: compressão forte prejudica mais o rPPG que o sono).

### 3.2 Quantas pessoas e quanto tempo

- **Fase A: 12 a 15 pessoas** (equipe, familiares e amigos). Variar:
  - tom de pele, registrado pela escala Monk de 10 tons ([skintone.google](https://skintone.google/); CC BY 4.0
    segundo fonte secundária);
  - sexo e idade;
  - barba, óculos de grau, maquiagem.
- **~30 min por pessoa**, totalizando ~6–7 h, das quais ~4 h negativas. Isso dá:
  - falsos alarmes/h com limite superior de ~0,75/h se não houver nenhum alarme falso;
  - ≥ 60 eventos de cada tipo principal.
- **Fase B**, depois da fase A: 20+ pessoas e situações de turno real, por exemplo depois de um plantão. Só com
  revisão jurídica e, se for virar artigo, comitê de ética (CEP). **Hipótese**: avaliar com o advogado se teste de
  produto exige CEP.

### 3.3 Roteiro (com registro de sinais para acelerar a anotação)

Um script de roteiro (proposta: `ferramentas/roteiro_gravacao.py`) toca uma voz ou bipe ("feche os olhos por três
segundos… agora") e grava `roteiro_log.csv` com o horário de cada comando. A anotação vira "ajustar início e fim"
em vez de "procurar o evento". **Hipótese**: cai de 3–5× para 1,5–2× o tempo do vídeo.

Abrir e fechar cada bloco com **sincronia**: palma + flash da lanterna do celular, visível nas duas câmeras e na
câmera do oxímetro.

**Bloco 1: base, 8 min, sem acessório, luz boa**

| Min | Cena | Rótulo |
|---|---|---|
| 0–5 | Olhar para a "estrada", piscar normal, falar um pouco (calibração e negativo) | `falando`, negativo |
| 5–8 | 10 piscadas normais e 3 piscadas longas (~0,5 s) | `piscada` |

**Bloco 2: sono encenado, 8 min**

| Cena | Repetições | Rótulo |
|---|---|---|
| Olhos fechados ~1,2 s | 5 | `olhos_fechados` (≥1 s) |
| Olhos fechados ~0,8 s (zona cinzenta, testa falso positivo) | 3 | `olhos_fechados` |
| Olhos fechados ~3,5 s | 3 | idem |
| Olhos fechados ~6,5 s | 2 | idem |
| Bocejo sem mão / com mão | 2 / 1 | `bocejo`, `bocejo_com_mao` |
| Cabeceio (cabeça cai e volta) | 3 | `cabeceio` |
| Esfregar os olhos | 2 | `olhos_esfregados` |

**Bloco 3: celular e negativos, 8 min.** Testar com 2 aparelhos diferentes no total (com e sem capinha).

| Cena | Repetições, ≥3 s cada | Rótulo |
|---|---|---|
| Celular no ouvido (D e E) | 3 | `celular_ouvido` |
| Celular na mão, na altura do peito ou queixo | 3 | `celular_mao` |
| Digitando e olhando o celular | 2 | `olhando_celular` |
| Celular no colo | 3 | `celular_colo` (negativo) |
| Celular no suporte | 2 | `celular_suporte` (negativo) |
| **Mão no ouvido sem celular** | 3 | `mao_no_ouvido_sem_celular` (negativo) |
| Fone de ouvido, carteira, copo, ajustar óculos, coçar o nariz, comer | 1 cada | negativos |
| Cantar, rir, olhar retrovisores | 1 min | `cantando`, `olhando_retrovisor` (negativo do bocejo e do cabeceio) |

**Bloco 4: condições, ~2 min cada, versão curta do bloco 2** (2 fechamentos de 1,2 s, 1 de 3,5 s, 1 bocejo e 1
celular no ouvido em cada):
1. óculos de grau (quem usa);
2. **óculos escuros**;
3. **boné** com aba baixa;
4. **pouca luz** (garagem ou noite, só a luz do painel);
5. **contraluz** (sol ou janela atrás, ou lanterna apontada para a câmera).

Rodar a ordem das condições entre pessoas (quadrado latino), para cansaço e aprendizado não se confundirem com a
condição.

**Bloco 5: cardio, ~6 min, com oxímetro**

| Min | Cena |
|---|---|
| 0–2 | Parado, olhando para a frente |
| 2–3 | 20 agachamentos fora do carro (sobe a FC; mesma ideia do jogo de matemática do UBFC) |
| 3–5 | Parado de novo (FC descendo; testa o rastreio) |
| 5–6 | Falando e girando a cabeça (deve virar "movimento" ou "sinal fraco", não um número errado) |

### 3.4 Oxímetro de dedo como referência do bpm

- **Modelo:** de preferência um com **saída USB e software de registro**, da mesma família CONTEC CMS50E usada no
  UBFC, no PURE e no BUAA (UBFC e BUAA conferidos). Conferir no manual se ele grava a FC por segundo e a onda.
  **Hipótese**: a linha CMS50D+/CMS50E tem software de PC que registra por segundo.
- **Precisão:** ver o manual. **Hipótese**: costuma ser ±2 bpm ou ±2%. Registrar o valor no relatório, porque erro
  do rPPG menor que o erro da referência não tem sentido.

**Sincronia, opção A (preferida):** oxímetro e webcam no mesmo notebook.
1. Um script grava o vídeo e um CSV com `time.time()` de cada quadro.
2. O software do oxímetro grava com o relógio do mesmo PC.
3. Os dois ficam no mesmo relógio, e o atraso fica só o do aparelho.

**Sincronia, opção B:** um segundo celular filma o visor do oxímetro.
1. Sincronizar pelo evento de palma + flash, visível nas duas gravações.
2. Ler a FC a cada 1 s, à mão ou por OCR.
3. Mostrar no visor do notebook um relógio grande também ajuda.

**Cuidados:**
- O oxímetro vai na mão parada, apoiada na coxa; com movimento, ele também erra. Dedo frio dá leitura ruim:
  aquecer as mãos antes.
- O atraso do aparelho (o visor mostra média de alguns batimentos) é estimado por correlação cruzada na sessão e
  aplicado igual a todos. Reportar o valor.

**Privacidade (RNF-16):**
- O bpm é **dado de saúde** (LGPD art. 5º, II).
- O CSV de referência e o `_cardio.csv` ficam na pasta cifrada de gravações, nunca no git.
- No relatório entram só números agregados (MAE, RMSE etc.), sem a FC de uma pessoa identificável.

### 3.5 Consentimento por escrito (modelo curto)

Base legal: dado biométrico e de saúde é **sensível** (LGPD, [art. 5º, II](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)).
O consentimento precisa ser "**de forma específica e destacada, para finalidades específicas**" (art. 11, I) e
"pode ser revogado a qualquer momento" (art. 8º, §5º). Os três trechos foram conferidos no Planalto. **Precisa de
revisão do advogado antes da primeira gravação.**

> **Termo de consentimento: gravação para testes do RotaGuard**
>
> Eu, ______________________ (CPF ___________), maior de 18 anos, concordo em participar da gravação de testes do
> RotaGuard, organizada por Matheus Cortes (contato: ____________).
>
> **O que será gravado:** vídeo do meu rosto e das minhas mãos por cerca de 30 minutos, com o carro **parado**,
> encenando piscadas, olhos fechados, bocejos, movimentos de cabeça e uso de celular. Opcionalmente, minha
> frequência cardíaca por um oxímetro de dedo.
>
> **Para que:** só para medir e melhorar a detecção de sinais de sono, de uso de celular e a estimativa de
> frequência cardíaca do RotaGuard. Não é exame médico, e nenhum resultado será usado para avaliar meu trabalho.
>
> **Dados sensíveis:** imagem do rosto (dado biométrico) e frequência cardíaca (dado de saúde).
>
> **Onde fica e quem vê:**
> - os arquivos ficam num disco cifrado, sem nuvem pública;
> - só a equipe técnica do projeto (nomes: ______) tem acesso;
> - nenhuma imagem minha vai para a internet, site, redes sociais ou repositório de código, salvo se eu marcar a
>   opção (d).
>
> **Por quanto tempo:** até ___/___/____ ou até o fim do projeto, o que vier primeiro. Depois os vídeos são
> apagados, e o apagamento é registrado.
>
> **Marque o que autoriza** (cada item é independente; posso não marcar nenhum além do primeiro):
> - [ ] (a) Gravação e uso interno para desenvolvimento e testes (obrigatório para participar)
> - [ ] (b) Uso da minha frequência cardíaca medida pelo oxímetro, só como referência de comparação
> - [ ] (c) Citação de **números agregados** (por exemplo, "acertou 95% dos eventos") em apresentações e no pitch,
>   sem imagem e sem meu nome
> - [ ] (d) Uso de **trechos ou imagens** do meu rosto em apresentações ou no pitch
>
> **Meus direitos:**
> - posso desistir a qualquer momento, durante ou depois, sem dar motivo e sem prejuízo nenhum;
> - posso pedir acesso, correção ou apagamento pelo contato acima (LGPD art. 18);
> - se eu desistir, meus vídeos são apagados em até ___ dias.
>
> **Participação voluntária:** não recebo pagamento, e não participar não muda nada na minha relação com a equipe.
>
> Local e data: ____________ Assinatura: ____________
> Responsável pela gravação: ____________ Assinatura: ____________

- **Equipe subordinada:** o consentimento de funcionário pode ser questionado como "não livre". Por isso a cláusula
  de participação voluntária, sem efeito na avaliação de trabalho, e a preferência por voluntários fora da relação de
  emprego (**Hipótese jurídica**).
- **Guardar o termo assinado separado dos vídeos**, com o ID do participante (P01, P02…). Os nomes de arquivo e as
  anotações usam só o ID.

### 3.6 Anotar rápido: ferramentas livres

| Ferramenta | Licença (conferida) | Melhor para | Observação |
|---|---|---|---|
| **ELAN** (MPI) | GPL-3 ([archive.mpi.nl/tla/elan](https://archive.mpi.nl/tla/elan)) | **Intervalos de tempo** (olho fechado, bocejo, celular), atalhos de teclado, várias trilhas por vídeo | Programa de desktop; exporta texto tabulado → conversor para o CSV padrão. **Recomendado para eventos** |
| **Label Studio** | Apache-2.0 (API do GitHub) | Vídeo com a tag `TimelineLabels` ("classify video frames […] a single frame or a span of frames", [docs](https://labelstud.io/tags/timelinelabels)) | `pip install`, roda local; exporta JSON |
| **CVAT** | MIT (API do GitHub) | **Caixas** (celular, mão) e rastreio quadro a quadro; tags por intervalo | Mais pesado (Docker); bom se for treinar ou calibrar o tamanho da caixa do celular |

Usar só a instalação **local**, sem a nuvem dessas ferramentas: vídeo de rosto não sai da máquina.

**Fluxo:**
1. Pré-anotação pelo `roteiro_log.csv`.
2. Ajuste no ELAN.
3. Segunda anotação cega em 20% dos vídeos.
4. `concordancia.py` (proposta) mede o F1 entre anotadores; abaixo de 0,9, rever a definição do evento.

**Definições que precisam ficar escritas** (em `docs/validacao/guia-de-anotacao.md`):
- **olho fechado**: do primeiro quadro em que a pálpebra cobre a pupila até o primeiro quadro em que a pupila
  reaparece;
- **bocejo**: da boca começando a abrir além da fala até fechar;
- **celular no ouvido**: aparelho encostado ou a menos de ~5 cm da orelha.

---

## 4. Testes automatizados de regressão com vídeo

### 4.1 Onde guardar clipes sem dado pessoal no git

| Opção | Licença e privacidade | Prós | Contras | Uso |
|---|---|---|---|---|
| **Avatar 3D no Blender com MPFB2** | Assets **CC0**, e "no limitation on what you can do with this combined output" ([LICENSE.md do MPFB2](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md), conferido). O código do MPFB é GPL-3, mas não vai no produto | Roteiro exato (fechamento de 1,2/3,5/6,5 s, bocejo de 3 s, cabeceio de 20°); verdade perfeita; pode ir para o git ou para uma release pública | **Hipótese crítica**: o Face Landmarker do MediaPipe precisa achar o rosto do avatar em ≥ 95% dos quadros, e o EAR do avatar precisa cair como o de gente. Testar primeiro (VAL-09a). Pele sintética não serve para rPPG realista | **CI a cada push** |
| Sinal sintético de cardio injetado no avatar (verde da textura da pele modulado a 72 bpm) | idem | Testa o pipeline vídeo → ROI → POS de ponta a ponta | Compressão mata o sinal: salvar sem perdas (FFV1 ou PNG) e pequeno (320×240, 15 s) | CI |
| Clipes de dataset **CC BY** (NITYMED) | CC BY permite redistribuir com atribuição | Gente de verdade, carro de verdade | Rosto de terceiros num repositório: por cortesia, pedir aos autores; nunca de quem negou imagem (YawDD "No"). **Hipótese**: aceitável com atribuição | Release com SHA-256, não no histórico do git |
| Gravação própria com consentimento (d) | Dado biométrico com direito de revogação | Pessoas brasileiras, cenas exatas | **Git é para sempre**: se a pessoa revogar, o histórico teria de ser reescrito. **Nunca no git** | Pasta cifrada local (`ROTAGUARD_CLIPES_PRIVADOS`); teste "pulado" quando não houver |
| Traços de medidas (EAR, abertura, mandíbula, pitch por quadro) de gravações próprias | Ainda é dado pessoal ligado a uma pessoa (**Hipótese**: baixo risco, mas não anônimo) | Regressão rápida das regras sem rodar o MediaPipe | Pontos do rosto (478) podem identificar: não salvar pontos crus | Pasta privada; no git só traços **sintéticos** (os testes atuais já fazem assim) |

**Recomendação:**
- **camada 1 no git**: testes com séries sintéticas (já existem: `tests/test_detector.py`, `tests/test_cardio.py`);
- **camada 2 no git ou em release**: clipes de avatar MPFB2 + arquivos "dourados" com os eventos esperados;
- **camada 3 fora do git**: clipes reais (próprios ou CC BY), rodados na máquina de avaliação e antes de cada
  versão.

**Guardrail sugerido** (regra 2b.6 do CLAUDE.md, "avaliar se vira hook"): hook do projeto que bloqueia
`git add` de `*.mp4|*.avi|*.mkv|*.mov` fora de `tests/dados/sinteticos/`, com casos de teste. Vídeo de rosto real no
git é um erro que não tem volta.

Hoje o workflow de CI só roda em tag `teste-v*` e em disparo manual (`.github/workflows/app-teste.yml:5-8`). Para
regressão, falta um workflow `validacao.yml` em push e pull request rodando `tests/test_*.py`, com os clipes do
avatar baixados da release e conferidos por SHA-256.

### 4.2 Limiares a travar no CI

Todos com o ID no nome do teste, no padrão SDD.

| Teste | Limiar travado | Por quê |
|---|---|---|
| Avatar, 60 s de piscadas normais (100–400 ms) | **0 alarmes** e 0 eventos de microssono | Falso alarme é o O4 |
| Avatar, fechamento de 1,2 s | 1 `microssono`, latência desde o início entre **1,0 e 1,3 s** | `MICROSLEEP_S = 1.0` (`drowsiness.py:28`) + no máximo ~0,3 s de atraso (**Hipótese**; fixar o valor medido na primeira rodada) |
| Avatar, fechamento de 0,8 s | **0** `microssono` | Zona cinzenta, lado de baixo |
| Avatar, fechamentos de 3,5 s e 6,5 s | `sono` e `nao_responsivo` com a mesma regra de latência | `drowsiness.py:29-30` |
| Avatar, bocejo de 3 s e fala de 30 s | 1 bocejo no primeiro, 0 no segundo | `YAWN_MIN_S = 2.0` (`drowsiness.py:50`) |
| Avatar, cabeceio de 20° | 1 cabeceio | `NOD_MIN_DEG = 15.0` (`drowsiness.py:56`) |
| **Arquivo dourado** por clipe | Lista de eventos igual ao JSON dourado (tipo e contagem iguais; tempo ±0,1 s) | Qualquer mudança de comportamento aparece; atualizar o dourado exige justificativa no commit |
| Cardio no avatar com pulso injetado | Erro ≤ 3 bpm e estado `pronto` em ≤ 15 s | Coerente com CAR-01/02 |
| Desempenho | Não travar ms por quadro no runner do GitHub (varia muito). Comparar com a referência local; CAR-14 continua local | Evita teste instável |

**Fora do CI** (máquina com os dados, antes de cada versão), registrando em `docs/validacao/linhas-de-base.json`:
- **não piorar** o F1 de piscada no Eyeblink8 (queda máxima de 0,02);
- recall de microssono e bocejo no NITYMED (queda máxima de 0,03);
- falsos alarmes/h no YawDD normal + falando (aumento máximo de 0,1/h);
- MAE do cardio na gravação própria (aumento máximo de 0,5 bpm).

Meta absoluta é decisão do Matheus (VAL-02). O CI garante "não piorou".

---

## 5. Lista priorizada

| ID | O quê | Critério de aceite testável | Depende de |
|---|---|---|---|
| **VAL-01** | Pedir acesso e autorização **hoje**: UL-DD (pedido no Zenodo), NITYMED (formulário + e-mail de cortesia), YawDD (confirmar uso comercial em número agregado), UBFC-Phys (resolver o conflito CC BY × CC BY-NC-SA), UTA-RLDD, MR-NIRP, Eyeblink8 (GPL-3 vale para os vídeos?). Criar `docs/validacao/licencas/` | Para cada dataset: arquivo com o texto da licença, data, link e status (`permitido`, `pendente` ou `negado`). Nenhum dataset `pendente` ou `negado` aparece em relatório de pitch (teste que confere os relatórios) | — |
| **VAL-02** | **Metas pré-registradas** do O4 e do O1 (decisão do Matheus), mais a divisão de sujeitos em desenvolvimento e teste | `docs/validacao/plano-pre-registrado.md` com commit **anterior** ao primeiro relatório de teste. Sugestão para ele decidir: microssono recall ≥ 0,95 e precisão ≥ 0,90; ≤ 0,5 falso alarme sonoro/h; latência p95 ≤ 1,5 s depois do limiar de 1 s; cardio MAE ≤ 5 bpm parado em RGB, com cobertura ≥ 60% | — |
| **VAL-03** | `avaliar_eventos.py` + extensões em `vision/evaluation.py`: casamento por intervalo, fusão de detecções repetidas, latência, falsos alarmes/h por tempo negativo, IC de Wilson, Poisson exato e bootstrap por sujeito, zona cinzenta | Testes com a biblioteca padrão: Wilson(9/10) = [0,596; 0,982]; 0 alarmes em 3 h dá limite superior de 0,999/h (unilateral 95%); lista conhecida de detecções e anotações dá acertos, falsos positivos e perdidos exatos; detecção dentro de `[início, fim + 0,5]` casa e fora não casa | — |
| **VAL-04** | `analisar_video.py`: tempo por `CAP_PROP_POS_MSEC` (F2), `--perfil-padrao` para clipe curto (F1), `_bocejos.csv` e `_cabeceios.csv` (F5), `--cardio` → `_cardio.csv` (F6), `--fps-alvo` e `--largura` (F8), commit e versões no `_resumo.json` (F9) | Vídeo sintético com fps variável: erro de tempo < 5 ms. Clipe de 20 s com `--perfil-padrao` gera eventos. `--fps-alvo 12` num vídeo de 30 fps processa 12 ± 0,5 fps. O `_resumo.json` tem `commit` e `arvore_suja` | — |
| **VAL-05** | Conversores: ELAN, Label Studio, CVAT e Eyeblink8 `.tag` → CSV padrão (§2.3), mais `guia-de-anotacao.md` | Um arquivo de exemplo de cada formato em `tests/dados/` vira o CSV esperado, byte a byte | — |
| **VAL-06** | Primeiro relatório: **NITYMED + YawDD** (bocejo, microssono, falsos alarmes com fala e canto, óculos escuros), a 30 e 12 fps | `docs/validacao/AAAA-MM-DD-nitymed-yawdd.md` gerado por um comando; duas rodadas dão o mesmo JSON (hash igual); todo número com IC e n | VAL-01, 03, 04, 05 |
| **VAL-07** | Gravação própria, fase A (§3): 12–15 pessoas, ~6 h, roteiro, oxímetro, termo assinado | Manifesto com n de pessoas, horas negativas (≥ 4 h), eventos por tipo (≥ 60 fechamentos ≥1 s, ≥ 40 bocejos, ≥ 40 de celular no ouvido, ≥ 40 de mão no ouvido sem celular); 100% dos termos guardados; concordância entre anotadores (F1 de eventos) ≥ 0,9 em 20% dos vídeos | VAL-05; revisão jurídica do termo |
| **VAL-08** | `avaliar_cardio.py`: leitores (oxímetro próprio, UL-DD FC 1 Hz, UBFC `ground_truth.txt`), atraso por correlação cruzada, MAE, RMSE, r, PTE6, cobertura e Bland-Altman | Referência sintética com atraso de 3 s e ruído: atraso estimado em 3 ± 0,5 s; MAE igual ao cálculo à mão; janela sem número entra na cobertura e fica fora do MAE | VAL-04 |
| **VAL-09** | Regressão em vídeo no CI: (a) prova de que o MediaPipe acha o avatar MPFB2; (b) clipes e JSON dourado; (c) `validacao.yml` em push e PR | (a) rosto detectado em ≥ 95% dos quadros e EAR fechado < 50% do aberto; se falhar, trocar para clipes CC BY em release. (b) e (c) todos os limiares do §4.2 passando no GitHub Actions; o hook que bloqueia vídeo fora de `tests/dados/sinteticos/` passa nos seus casos de teste | VAL-03, 04 |
| **VAL-10** | Relatório da **gravação própria** (sono, celular, cardio) por condição e por grupo de pele Monk | Tabela por condição e por grupo Monk (1–3, 4–7, 8–10). Qualquer grupo com recall 0,10 abaixo do total aparece como **alerta** no topo do relatório | VAL-06, 07, 08 |
| **VAL-11** | **UL-DD** (quando liberar): falsos alarmes/h na sessão alerta, AUC alerta × sonolento, latência na sessão sonolenta e **rPPG em IR** contra a FC 1 Hz | Relatório com as 4 medidas e IC por sujeito (bootstrap); diz que a referência é pulseira e não ECG | VAL-01, 03, 08 |
| **VAL-12** | **Modo Pi** em tudo: 12 fps, 640×480, IR quando houver; efeito do `MIN_FPS_FOR_DURATION = 24` | Cada relatório tem a coluna 30 fps × 12 fps; uma piora maior que 0,05 no recall abre pendência (spec 005) | VAL-04 |
| **VAL-13** | **Folha de números do pitch**: só números de relatórios cujos datasets estão `permitido` + gravação própria, com IC, e a lista do que **não** foi medido (Pi, NoIR, caminhão real, sono real em estrada, cardio na caixa) | Teste confere que cada número da folha tem link para um relatório e um commit, e que nenhum dataset `pendente` ou `negado` é citado | VAL-01, 06, 10 |

---

## 6. Fontes consultadas (19/10/2026)

- **Sono:**
  - [NTHU-DDD](http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/) e [EULA](http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/NTHU-DDD-LicenseAgreement.pdf)
  - [UTA-RLDD](https://sites.google.com/view/utarldd/home)
  - [DROZY](http://www.drozy.ulg.ac.be/)
  - [YawDD](https://ieee-dataport.org/open-access/yawdd-yawning-detection-dataset) e DataCite 10.21227/e1qm-hb90
  - [Termos do IEEE DataPort](https://ieee-dataport.org/ieee-dataport-terms-use)
  - [CEW](https://parnec.nuaa.edu.cn/_upload/tpl/02/db/731/template731/pages/xtan/ClosedEyeDatabases.html)
  - [MRL Eye](https://mrl.cs.vsb.cz/eyedataset.html)
  - [blinkingmatters (Eyeblink8, ZJU, Researcher's night)](https://www.blinkingmatters.com/research)
  - [RT-BENE (Zenodo)](https://zenodo.org/records/3685316) e [rt_gene](https://github.com/Tobias-Fischer/rt_gene)
  - [DMD](https://dmd.vicomtech.org/) e [GitHub](https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset)
  - [SUST-DDD (artigo no Zenodo)](https://zenodo.org/records/6519933)
  - [NITYMED](https://datasets.esdalab.ece.uop.gr/), [DataPort](https://ieee-dataport.org/documents/nitymed) e DataCite 10.21227/85xe-3f88
  - [UL-DD (Zenodo)](https://zenodo.org/records/17978727) e [arXiv 2507.13403](https://arxiv.org/abs/2507.13403)
  - [3MDAD](https://hal.archives-ouvertes.fr/hal-03321535)
- **Distração:**
  - [State Farm (regras, não legíveis sem login)](https://www.kaggle.com/competitions/state-farm-distracted-driver-detection/rules)
  - [AUC](https://heshameraqi.github.io/distraction_detection)
  - [Drive&Act](https://www.driveandact.com/) e [suplemento ICCV 2019](https://openaccess.thecvf.com/content_ICCV_2019/supplemental/Martin_DriveAct_A_Multi-Modal_ICCV_2019_supplemental.pdf)
- **rPPG:**
  - [UBFC-rPPG](https://sites.google.com/view/ybenezeth/ubfcrppg)
  - [UBFC-Phys](https://sites.google.com/view/ybenezeth/ubfc-phys) e DataCite 10.21227/5da0-7344 e 10.25666/dataubfc-2022-05-05
  - [PURE](https://www.tu-ilmenau.de/universitaet/fakultaeten/fakultaet-informatik-und-automatisierung/profil/institute-und-fachgebiete/institut-fuer-technische-informatik-und-ingenieurinformatik/fachgebiet-neuroinformatik-und-kognitive-robotik/data-sets-code/pulse-rate-detection-dataset-pure)
  - [MMPD](https://github.com/McJackTang/MMPD_rPPG_dataset)
  - [MR-NIRP](https://computationalimaging.rice.edu/mr-nirp-dataset/)
  - [VIPL-HR](https://vipl.ict.ac.cn/resources/databases/201811/t20181129_32716.html)
  - [COHFACE](https://www.idiap.ch/en/scientific-research/data/cohface) e [Zenodo 4081054](https://zenodo.org/record/4081054)
  - [BUAA-MIHR](https://github.com/xilin-x/Large-scale-Multi-illumination-HR-Database)
  - [IMVIA-NIR](https://sites.google.com/view/ybenezeth/imvia-nir)
  - [SCAMPS](https://github.com/danmcduff/scampsdataset)
- **Ferramentas e regras:**
  - [MPFB2 LICENSE](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md)
  - CVAT (MIT) e Label Studio (Apache-2.0), licenças pela API do GitHub
  - [Label Studio TimelineLabels](https://labelstud.io/tags/timelinelabels)
  - [ELAN](https://archive.mpi.nl/tla/elan)
  - [LGPD (Planalto)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
  - [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/legalcode)
  - [Monk Skin Tone (Google)](https://blog.google/technology/ai/monk-skin-tone-scale/)
- **Repositório (lido):**
  - `ferramentas/analisar_video.py`, `avaliar_dataset.py`, `avaliar_piscadas.py`, `avaliar_gestos.py`, `avaliar_celular.py`
  - `ferramentas/anotacoes/*.csv`, `caixa/vision/evaluation.py`, `caixa/vision/drowsiness.py`
  - `docs/produto/PRD.md` (O1, O4, RNF-02, RNF-16), `docs/specs/022-cardio-pela-face.md`
  - `docs/pesquisa/2026-10-19-pulso-pela-camera-rppg.md`, `.github/workflows/app-teste.yml`
- **Vault (lida):** `10 - Validacao com gravacoes (etapa 2).md`, `06 - Testes, desempenho e pendencias.md`,
  `05 - Privacidade, licencas e model cards.md`, `12 - Cardio pela face (rPPG).md`.
