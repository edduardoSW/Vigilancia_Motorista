# -*- coding: utf-8 -*-
# Gera o HTML da lista de compras do RotaGuard (caixa com Raspberry Pi 4, bancada e VPS).
# Precos pesquisados em 17/09/2026: lojas brasileiras, paginas oficiais, APIs publicas de preco e AliExpress Brasil
# (lido com navegador automatizado, variante exata, frete e imposto estimado pela regra da propria pagina).
# uso: python gerar_lista_de_compras.py saida.html
import sys, html, math

SAIDA = sys.argv[1]
DATA = "17/09/2026"
E = html.escape

def brl(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s

def link(rotulo, url): return f'<a href="{E(url)}">{E(rotulo)}</a>'

# ------------------------------------------------------------------ AliExpress: imposto e escolha
# Regra mostrada na pagina de cada produto em 17/09/2026 (Portaria MF 1.342/2026, de 12/05/2026):
#   pedido ate US$ 50: sem Imposto de Importacao; acima: 60% com desconto de US$ 30; ICMS de 17% a 20% "por dentro".
# A base e o preco mais o frete. O cambio de R$ 5,55 reproduz as estimativas de imposto das proprias paginas.
CAMBIO_ALI = 5.55
ICMS = 0.20          # pior caso (17% a 20% conforme o estado)
ECONOMIA_MIN = 0.15  # o AliExpress so entra na conta se sair pelo menos 15% mais barato

def imposto_ali(base):
    ii = max(0.0, 0.60 * base - 30 * CAMBIO_ALI) if base / CAMBIO_ALI > 50 else 0.0
    return ii + (base + ii) * ICMS / (1 - ICMS)

# TAX-01 e TAX-02: a conta tem de bater com a estimativa que a pagina mostrou (sem frete) em 17/09/2026
assert abs(imposto_ali(386.59) - 178.46) < 0.10, "TAX-01: acima de US$ 50 nao bate com o AliExpress"
assert abs(imposto_ali(160.52) - 40.15) < 0.10, "TAX-02: ate US$ 50 nao bate com o AliExpress"

def A(item_id, loja, var, preco, frete, dias, pacote=1, obs="", lista=False):
    # lista=True: preco lido na lista de busca (variante mais barata, frete nao confirmado), porque a loja passou a bloquear a pagina do produto
    return dict(url=f"https://pt.aliexpress.com/item/{item_id}.html", loja=loja, var=var, preco=preco, frete=frete, dias=dias,
                pacote=pacote, obs=obs, lista=lista)

# ------------------------------------------------------------------ itens
# grupo: "caixa" (uma por veiculo), "montagem" (placa de controle da caixa), "kit" (compra unica), "banc" (bancada), "opc" (opcional)
# escolha: None = automatica (AliExpress so com economia de 15% ou mais); "br" = fica no Brasil mesmo mais caro (motivo na nota)
def I(nome, modelo, qtd, preco, onde, nota, grupo, preco_txt=None, ref=False, estoque="", ali=None, escolha=None):
    return dict(nome=nome, modelo=modelo, qtd=qtd, preco=preco, onde=onde, nota=nota, grupo=grupo, preco_txt=preco_txt,
                ref=ref, estoque=estoque, ali=ali, escolha=escolha)

COMPUTADOR = [
    I("Computador", "Raspberry Pi 4 Model B 4 GB", 1, 1436.90,
      link("MakerHero", "https://www.makerhero.com/produto/raspberry-pi-4-model-b/"),
      "Único revendedor aprovado brasileiro na lista oficial, versão Anatel. Alternativa nacional: Saravati R$ 1.349,91 à vista (não é revendedor aprovado). "
      "Produção garantida até pelo menos janeiro de 2034.", "caixa", estoque="em estoque",
      ali=A("1005007384599192", "Seeedstudio", "Pi4 4GB", 651.08, 35.10, "13 a 26",
            obs="Seeed é revendedora oficial da Raspberry Pi. Só 2 em estoque. Sem selo Anatel.")),
    I("Cartão de memória", "SanDisk MAX Endurance 64 GB (SDSQQVR-064G) ou Samsung PRO Endurance 64 GB (MB-MJ64K)", 1, 265.00,
      link("KaBuM (referência: Kingston High Endurance 64 GB)", "https://www.kabum.com.br/produto/478660"),
      "Os dois primeiros têm as maiores horas de gravação e garantia (30.000 a 35.040 h; 3 a 5 anos). Não achei os dois com estoque e nota no Brasil; "
      "o preço é do Kingston High Endurance 64 GB, sem estoque no dia. Não compre cartão comum: a caixa grava o tempo todo. "
      "No AliExpress fica fora da conta: nas buscas não apareceu loja oficial da SanDisk ou da Samsung, e cartão falsificado perde o registro da viagem.",
      "caixa", ref=True, estoque="sem estoque", escolha="br",
      ali=A("1005012838161374", "ByteGear Global Store", "SanDisk MAX 64 GB", 168.59, 30.68, "13 a 26",
            obs="Loja sem ligação com a marca: risco de falsificação.")),
    I("Relógio (RTC)", "Módulo RTC DS3231 para Raspberry Pi (encaixa no GPIO)", 1, 15.10,
      link("RoboCore", "https://www.robocore.net/outros-componentes-eletronicos/rtc-ds3231-raspberry-pi"),
      "Obrigatório no Pi 4, que não tem relógio: sem ele o registro perde a hora entre a viagem e a coleta (spec 003). "
      "Confira a bateria: módulo com circuito de carga não pode usar CR2032. Dispensável se a placa de energia SH-RPi for usada (ela já traz RTC).",
      "caixa", estoque="em estoque",
      ali=A("1005007143542894", "Realpoy Module", "mini, com bateria", 6.99, 0, "10 a 22")),
]
CAMERA = [
    I("Câmera", "Raspberry Pi Camera Module 3 NoIR, lente padrão (66° na horizontal)", 1, 313.93,
      link("Amazon.com.br (importado, R$ 305,03 + frete R$ 8,90)", "https://www.amazon.com.br/dp/B0BRY3L9H7"),
      "Sem filtro infravermelho: mede a pupila de dia e de noite. A 70 cm enquadra ~70 × 52 cm em 640×480 e põe ~1,8× mais pixels no olho que a versão Wide. "
      "Com nota e estoque nacional: Loja do Jangão R$ 1.298,00. Não compre a versão comum (com filtro IR) nem câmera com IR-CUT automático: de dia o filtro fecha e a pupila deixa de ser medida.",
      "caixa", estoque="4 em estoque",
      ali=A("1005007870760347", "Seeedstudio", "Camera 3 NoIR", 160.52, 34.28, "13 a 26",
            obs="Revendedora oficial. Só 3 em estoque; confira que a variante é NoIR.")),
    I("Iluminação infravermelha", "LED Vishay TSAL6200, 940 nm, 5 mm", 6, 1.50,
      link("AutoCore Robótica", "https://www.autocorerobotica.com.br/tsal6200-emissor-ir"),
      "940 nm não brilha para o motorista e sofre menos com o sol. A Vishay classifica o LED como isento na IEC 62471; 4 a 6 LEDs somam ~3 W/m² a 50 cm, bem abaixo do limite de 100 W/m². "
      "Montar fora do eixo da lente, com difusor. Se a imagem ficar escura, testar 850 nm (TSHG6200).",
      "caixa", estoque="disponível",
      ali=A("1005006903094424", "IBUW Electronic", "TSAL6200 5 mm, pacote com 10", 6.99, 0, "10 a 22", pacote=10,
            obs="Marca Vishay não garantida: a segurança ocular vale para o LED original.")),
    I("Cabo da câmera", "Cabo flat 15 vias, 50 cm (15 pinos, 1 mm)", 1, 11.99,
      link("Casa da Robótica", "https://www.casadarobotica.com/placas-embarcadas/raspberry-pi/acessorios/cabo-flat-para-camera-raspberry-pi-b-b-de-15-vias-50cm"),
      "A câmera já vem com 200 mm. Use 30 a 50 cm, longe dos fios de 12/24 V. A Raspberry Pi não garante nada acima do cabo original e, acima de 1 m, a imagem corrompe em ambiente com ruído.",
      "caixa", estoque="44 em estoque",
      ali=A("1005004271000319", "MrZone", "50 cm, passo 1 mm", 9.03, 0, "11 a 26")),
    I("Suporte da câmera", "Suporte de acrílico ajustável para câmera Raspberry Pi", 1, 4.99,
      link("Casa da Robótica", "https://www.casadarobotica.com/placas-embarcadas/raspberry-pi/acessorios/suporte-acrilico-ajustavel-para-montagem-de-camera-de-raspberry"),
      "Furação do Camera Module 3 igual à do 2; a lente é mais alta, confira o encaixe.", "caixa",
      ali=A("32966722953", "DIYzone", "parafusos de metal", 9.03, 0, "10 a 22")),
]
ENERGIA = [
    I("Conversor 12/24 V para 5 V", "MZHOU M32J5V3A1SA, 8–32 V para 5 V 3 A, IP67, saída USB-A", 1, 72.78,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B0D41GR1L2"),
      "Protege contra inversão e curto. Precisa de cabo USB-A para USB-C curto e grosso. Meça 5,1 V no Pi com carga: abaixo de ~4,63 V o Pi acusa subtensão. "
      "Produção: Mean Well DDR-30G-5 (9–36 V, 12 V) ou DDR-30L-5 (18–75 V, 24 V), com saída ajustável; sem preço no Brasil. Versão com desligamento seguro: SH-RPi, na seção 7.",
      "caixa", estoque="disponível",
      ali=A("1005007820939213", "Shop911934595", "12/24 V para 5 V 3 A, saída USB-C", 16.52, 0, "10 a 22",
            obs="Genérico, sem ficha técnica: medir a tensão com carga na bancada antes de instalar.")),
]
ALARME = [
    I("Alarme", "Sirene de ré DNI 4127, bivolt 12/24 V, ~110 dB, 60 mA", 1, 27.40,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B08Q2FZTMY"),
      "Cabine de caminhão em rodovia tem 88 a 92 dB(A); o alarme precisa ficar ~15 dB acima (ISO 7731). A mesma peça serve 12 e 24 V e tem redutor para ~80 dB. "
      "Ligada pelo GPIO através de um transistor ou MOSFET. Instale a ~1 m do motorista e meça na cabine; não use sirene de 120 dB (NR-15 proíbe acima de 115 dB(A)). "
      "A genérica do AliExpress fica fora da conta: não informa corrente nem tem redutor, e a economia é de poucos reais.",
      "caixa", escolha="br",
      ali=A("1005005789519942", "Dynoracing", "105 dB, 12–24 V, um tom", 18.01, 0, "10 a 22")),
]
CAIXA = [
    I("Caixa", "Patola PB-150, ABS preto, 100 × 150 × 214 mm", 1, 95.79,
      link("Patola Store", "https://www.patolastore.com.br/caixa-gabinete-patola-modelo-pb-150-cx-e-tp-abs-preto/p"),
      "Tem altura para conversor de trilho DIN. Sem conversor DIN: Patola PB-119 (65 × 112 × 190 mm, R$ 75,07, esgotada) ou PB-115 (50 × 112 × 160 mm, R$ 44,30 na Usinainfo). "
      "Faça furos de ventilação.", "caixa",
      ali=A("1005008657422765", "AIRLGEE", "ABS 200 × 150 × 100 mm, IP67", 70.41, 42.87, "13 a 26")),
    I("Dissipação", "Case de alumínio para Raspberry Pi 4 com duplo cooler", 1, 109.90,
      link("Smart Kits", "https://www.smartkits.com.br/case-de-aluminio-para-raspberry-pi-4-com-duplo-cooler"),
      "O Pi 4 é garantido só até 50 °C de ambiente e reduz a velocidade a partir de 80 °C no chip. Painel ao sol chega a ~69 °C: dissipação passiva não basta. "
      "Alternativa nacional: Armor Case Saravati R$ 132,90.", "caixa", estoque="imediata",
      ali=A("1005003572003721", "A+A+A Store", "Pi 4, ventilador duplo", 32.99, 0, "10 a 22")),
    I("Passagem de cabo", "Prensa-cabo PG7 IP67 (cabo de 3,5 a 6,5 mm)", 2, 2.56,
      link("Usinainfo", "https://www.usinainfo.com.br/conectores-e-adaptadores/prensa-cabo-pg7-ip67-14-para-condutor-de-35-a-65mm-5043.html"),
      "Um para a energia e outro para a sirene.", "caixa",
      ali=A("1005003593198702", "Waterproof box socket box", "PG7 preto, 10 peças", 6.22, 18.77, "13 a 26", pacote=10)),
]
MONTAGEM = [
    I("Leitura da ignição", "Módulo optoacoplador PC817, 1 canal, entrada 12/24 V", 1, None, "",
      "Para o GPIO saber que a chave desligou sem ligar 12/24 V no pino. O software ainda filtra alguns segundos.", "montagem",
      ali=A("1005010188147556", "ver anúncio", "1 canal, 3 a 24 V", 7.33, 0, "10 a 26", lista=True)),
    I("Acionar a sirene e os LEDs", "Módulo MOSFET D4184 (substitui relé)", 2, None, "",
      "Um para a sirene e outro para os LEDs. O GPIO do Pi fornece no máximo 16 mA por pino: conferir na bancada que o módulo conduz totalmente com 3,3 V.", "montagem",
      ali=A("1005012756873468", "ver anúncio", "módulo D4184", 3.76, 0, "10 a 26", lista=True)),
    I("Placa dos LEDs", "Placa perfurada dupla face", 1, None, "",
      "Base dos LEDs infravermelhos, fora do eixo da lente.", "montagem",
      ali=A("1005004865405791", "ver anúncio", "placa universal dupla face", 5.61, 0, "10 a 26", lista=True)),
    I("Resistores", "Kit de resistores de filme metálico 1/4 W, 30 valores", 1, None, "",
      "Resistores dos LEDs, calculados pela tensão e pela corrente de trabalho.", "montagem",
      ali=A("1005006706508149", "ver anúncio", "600 peças, 30 valores, 1%", 11.14, 0, "10 a 26", lista=True)),
    I("Difusor", "Placa de acrílico leitoso", 1, None, "",
      "Espalha a luz dos LEDs e evita ponto brilhante no olho.", "montagem",
      ali=A("1005010619726761", "ver anúncio", "acrílico leitoso, chapa fina", 15.49, 0, "10 a 26", lista=True)),
    I("Cabos internos", "Jumpers fêmea-fêmea para o GPIO", 1, None, "",
      "Ligação do GPIO ao optoacoplador, aos módulos MOSFET e ao relógio.", "montagem",
      ali=A("1005006124543445", "ver anúncio", "40 vias, 20 cm", 9.33, 0, "10 a 26", lista=True)),
    I("Fio fino", "Fio flexível de silicone 22 AWG, cobre estanhado", 1, None, "",
      "Para os LEDs e a sirene dentro da caixa.", "montagem",
      ali=A("1005008153169841", "ver anúncio", "silicone, variante mais curta", 6.99, 0, "10 a 26", lista=True)),
    I("Proteção de 24 V", "Diodo supressor TVS da série 5KP (modelo a definir no teste)", 1, None, "",
      "Só em veículo de 24 V: o pico ao desconectar a bateria chega a 58 V (seção 9). O modelo e a ligação saem do teste de bancada.", "montagem",
      ali=A("1005005850891497", "ver anúncio", "5 peças da série 5KP", 3.56, 0, "10 a 26", lista=True)),
]
KITS = [
    I("Derivação da caixa de fusíveis", "Kit MuHize: 5 derivadores mini, 5 porta-fusíveis em linha e 120 fusíveis de 2 a 35 A", 1, 121.57,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B0F9WGMX6W"),
      "Pegue o positivo pós-chave (ACC). Fusível de 3 A em 12 V e de 2 A em 24 V. Para 24 V, prefira derivador vendido para 32 V.", "kit",
      ali=A("1005012918214810", "Stone's Store", "mini, 5 peças, para 32 V", 15.85, 0, "12 a 26",
            obs="Só os derivadores: fusíveis mini de 2 e 3 A à parte.")),
    I("Cabo de alimentação", "DNI HFX 1 mm² preto, 100 m (cobre)", 1, 170.11,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B076QK4SJK"),
      "Não compre o DNI HYB (liga de cobre com alumínio). Vermelho HFX: preço não encontrado. "
      "No AliExpress fica fora da conta: não dá para conferir cobre puro nem cabo antichama.", "kit", escolha="br"),
    I("Conector para soltar a caixa", "Conector automotivo Superseal 2 vias com terminais (kit com 5)", 1, 36.00,
      link("Plugshop", "https://www.plugshop.com.br/conector-automotivo-superseal-2-vias-terminais-5-kits"),
      "IP67, −40 a 125 °C, fio de 0,5 a 1,0 mm². Serve 5 caixas.", "kit", estoque="2 em estoque",
      ali=A("4000624697255", "RiccoDi AutoAccessories", "macho e fêmea, 5 conjuntos", 6.99, 0, "12 a 26")),
    I("Espaçadores", "Kit com 320 espaçadores M2.5 de nylon, parafusos e porcas", 1, 106.26,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B06XKWDSPT"),
      "Preço lido na lista de busca (a página pediu captcha).", "kit",
      ali=A("1005005263472533", "NINDEJIN Official Store", "M2.5, 240 peças com parafusos e porcas", 24.10, 0, "10 a 22")),
    I("Fita dupla-face", "3M VHB 5952, 19 mm (0,75\") × 5 jardas", 1, 117.31,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B007Y7H5GO"),
      "A 5952 é a indicada para painel de plástico. Para superfície lisa e metal: VHB 4910 (Adecil, R$ 99,10 por 20 m, até 93 °C).", "kit",
      ali=A("1005009403544095", "Chemical Global Brands Authority Store", "5952, 20 mm × 3 m", 31.69, 34.28, "13 a 26",
            obs="Conferir embalagem e lote na chegada: fita falsa solta a caixa no calor.")),
    I("Terminais", "Kit com 1250 terminais ilhós pré-isolados (0,5 a 10 mm²)", 1, 37.90,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B0H5VV2PLN"), "", "kit",
      ali=A("1005010172368560", "ver anúncio", "1200 peças, 0,08 a 16 mm²", 49.29, 0, "10 a 26", lista=True)),
    I("Abraçadeiras", "Nylon 3,5 × 200 mm com proteção UV, 100 unidades", 1, 15.50,
      link("SmartProjects Brasil", "https://www.smartprojectsbrasil.com.br/abracadeira-nylon-100-unidades-3.5mm-x-200mm"), "", "kit",
      ali=A("4000235072438", "ver anúncio", "100 peças, 5 × 300 e 3 × 200 mm", 10.69, 0, "10 a 26", lista=True)),
    I("Termorretrátil", "Kit com 164 tubos em 5 cores (−55 a 125 °C)", 1, 12.90,
      link("Eletrogate", "https://www.eletrogate.com/kit-tubo-termo-retratil-colorido-com-164-unidades-em-5-cores"), "", "kit",
      ali=A("1005008803649984", "ver anúncio", "127 ou 164 peças, 2:1", 10.99, 0, "10 a 26", lista=True)),
]
BANCADA = [
    I("Fonte de bancada", "Fonte oficial Raspberry Pi 15 W USB-C (5,1 V 3 A)", 1, 85.40,
      link("RoboCore", "https://www.robocore.net/acessorios-raspberry-pi/fonte-raspberry-pi-15w-usb-c"),
      "Para desenvolver e testar fora do veículo. 65 em estoque. MakerHero: R$ 89,90.", "banc", estoque="65 em estoque",
      ali=A("1005002910420124", "ver anúncio", "fonte oficial 5 V 3 A, USB-C", 66.99, 0, "10 a 26", lista=True,
            obs="Anunciada como original; a economia não chega a 15%.")),
    I("Gravar o cartão", "Leitor de cartão Ugreen CM104, USB 3.0", 1, 44.65,
      link("KaBuM", "https://www.kabum.com.br/produto/715482"),
      "Para gravar o Raspberry Pi OS Lite 64-bit (Trixie, 15/09/2026) com o Raspberry Pi Imager. Dispensável se o computador já tiver leitor de microSD.", "banc",
      ali=A("1005006897972401", "ver anúncio", "Ugreen USB 3.0, SD e microSD", 22.83, 0, "10 a 26", lista=True)),
    I("Coleta pelo computador", "Cabo Ugreen US288, USB-A para USB-C, de dados, 2 m", 1, 28.18,
      link("KaBuM", "https://www.kabum.com.br/produto/819549"),
      "Liga a caixa ao computador da empresa em modo dispositivo (spec 003). Nesse modo quem alimenta o Pi é o computador: prefira cabo curto e porta de computador de mesa (ver seção 9).", "banc"),
]
OPCIONAIS = [
    I("Placa de energia com desligamento seguro", "Hat Labs SH-RPi v2 (supercapacitor, entrada 9–32 V, RTC)", 1, None,
      link("shop.hatlabs.fi", "https://shop.hatlabs.fi/products/sh-rpi"),
      "Substitui o conversor e o relógio. Aceita 12 e 24 V direto, segura o Pi de 30 a 70 s com supercapacitor quando a chave desliga (sem bateria de lítio) e já tem relógio. "
      "Importada e esgotada no dia, por isso fica fora da soma. A proteção de entrada é de 33 V: não cobre o pico de 58 V de 24 V (ver seção 9).",
      "opc", preco_txt="€ 75,30 (esgotado)"),
    I("Voz e aviso de autoteste", "Amplificador PAM8403 (5 V, 2 × 3 W)", 1, 15.15,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B0C51NMJ13"),
      "Usa a saída de áudio P2 do Pi 4 (o software toca WAV pelo aplay). Complemento: sozinho, com alto-falante pequeno, não é ouvido no caminhão.", "opc",
      ali=A("1005008704155675", "HONGWEIWEI Factory", "PAM8403 2 × 3 W", 5.00, 0, "10 a 22")),
    I("Alto-falante", "Gikfun EK1794, 40 mm, 4 Ω, par", 1, 89.49,
      link("Amazon.com.br", "https://www.amazon.com.br/dp/B01LN8ONG4"),
      "83 dB de sensibilidade; potência real de 2 W. Preço lido na lista de busca. A caixa usa um alto-falante: no AliExpress o preço é de uma unidade.", "opc",
      ali=A("1005009979197194", "Test Board Store", "4 Ω 3 W, 40 mm, 1 unidade", 16.76, 0, "11 a 26")),
    I("Monitor", "Cabo micro-HDMI para HDMI, 1,5 m", 1, 28.40,
      link("RoboCore", "https://www.robocore.net/acessorios-raspberry-pi/cabo-micro-hdmi"),
      "O Pi 4 tem micro-HDMI. Opcional porque o Raspberry Pi Imager já grava rede e acesso SSH no cartão. Mais barato: adaptador micro-HDMI para HDMI, R$ 9,40 na RoboCore.", "opc",
      ali=A("1005007362264136", "ver anúncio", "micro-HDMI para HDMI", 18.16, 0, "10 a 26", lista=True)),
    I("Teste rápido de infravermelho", "Câmera compatível Raspberry Pi NoIR 5 MP (OV5647) com 2 LEDs de 850 nm", 1, 129.90,
      link("MakerHero", "https://www.makerhero.com/produto/camera-compativel-raspberry-pi-noir-5mp/"),
      "Só para testar a detecção com infravermelho na bancada antes de a câmera principal chegar.", "opc",
      ali=A("1005004276506212", "ver anúncio", "OV5647 com 2 LEDs IR", 17.76, 0, "10 a 26", lista=True,
            obs="O anúncio tem variante com IR-CUT, que não serve: escolher a sem filtro.")),
    I("Medir o alarme", "Decibelímetro digital 30 a 130 dB", 1, None, "",
      "Para conferir o nível do alarme dentro da cabine em rodovia.", "opc",
      ali=A("32821363741", "ver anúncio", "UNI-T UT353, 30 a 130 dB", 106.23, 0, "10 a 26", lista=True)),
    I("Pen drive", "Pen drive USB 3.0 de 32 GB", 1, None, "",
      "Para a exportação por pen drive (spec 003), alternativa ao cabo USB-C.", "opc",
      ali=A("1005005842108860", "ver anúncio", "SanDisk Ultra Shift 32 GB", 44.87, 0, "10 a 26", lista=True)),
]

VPS_PLANOS = [
    ("Hostinger", "KVM 2", "2", "8 GB", "100 GB NVMe", "R$ 43,99 (24 meses; renova a R$ 77,99)", "São Paulo", "https://www.hostinger.com/br/servidor-vps"),
    ("Hostinger", "KVM 4", "4", "16 GB", "200 GB NVMe", "R$ 59,99 (renova a R$ 149,99)", "São Paulo", "https://www.hostinger.com/br/servidor-vps"),
    ("Hostinger", "KVM 8", "8", "32 GB", "400 GB NVMe", "R$ 119,99 (renova a R$ 259,99)", "São Paulo", "https://www.hostinger.com/br/servidor-vps"),
    ("Magalu Cloud", "i1-c2-r4-d40", "2", "4 GB", "40 GB", "R$ 102,99 (por hora, sem contrato)", "São Paulo", "https://magalu.cloud/precos/"),
    ("Locaweb", "VPS 4 GB", "2", "4 GB", "70 GB SSD", "R$ 53,90 (24 meses); R$ 89,90 sem contrato", "Brasil", "https://www.locaweb.com.br/servidor-vps/"),
    ("HostGator", "VPS NVMe 4", "2", "4 GB", "100 GB NVMe", "R$ 96,65 sem contrato", "Brasil", "https://www.hostgator.com.br/servidor-vps"),
    ("AWS Lightsail", "4 GB", "2", "4 GB", "80 GB SSD", "US$ 24 (≈ R$ 123,65)", "São Paulo", "https://aws.amazon.com/lightsail/pricing/"),
    ("Akamai/Linode", "Linode 4 GB", "2", "4 GB", "80 GB", "US$ 33,60 (≈ R$ 173,11)", "São Paulo", "https://api.linode.com/v4/linode/types"),
    ("Vultr", "vhp-2c-4gb", "2", "4 GB", "100 GB", "US$ 36 (≈ R$ 185,48)", "São Paulo", "https://api.vultr.com/v2/plans"),
    ("Oracle Cloud", "A1 Always Free", "2 Arm", "12 GB", "200 GB", "R$ 0 (pode recolher máquina ociosa)", "São Paulo ou Vinhedo", "https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm"),
]
VPS_ESCALA = [
    ("Piloto, 5 veículos", "Hostinger KVM 2 (2 vCPU, 8 GB, 100 GB)", "12,1 GB", "≈ R$ 55,83 (R$ 89,83 depois da renovação)"),
    ("50 veículos", "Hostinger KVM 4 (4 vCPU, 16 GB, 200 GB)", "121 GB", "≈ R$ 148,02 (R$ 238,02 depois da renovação)"),
    ("300 veículos", "Hostinger KVM 8 (8 vCPU, 32 GB, 400 GB) e pgBackRest", "726 GB", "≈ R$ 265,52 (R$ 405,52 depois da renovação)"),
]
VPS_PILOTO_MES = 55.83
VPS_PILOTO_RENOVA = 89.83
OBJETOS = [
    ("Magalu Cloud Object Storage", "R$ 0,10 por GiB", "R$ 0,10 por GiB", "Sim", "https://magalu.cloud/precos/"),
    ("Oracle Object Storage", "US$ 0,0255 por GB (10 GB grátis)", "10 TB/mês grátis", "Sim", "https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=BRL"),
    ("AWS S3 São Paulo", "US$ 0,0405 por GB", "US$ 0,15 por GB", "Sim", "https://aws.amazon.com/s3/pricing/"),
    ("Akamai/Linode", "US$ 5 com 250 GB", "US$ 0,007 por GB", "Sim", "https://techdocs.akamai.com/cloud-computing/docs/object-storage-pricing"),
    ("Cloudflare R2", "US$ 0,015 por GB", "Grátis", "Não", "https://developers.cloudflare.com/r2/pricing/"),
    ("Backblaze B2", "US$ 6,95 por TB", "Grátis até 3× o guardado", "Não", "https://www.backblaze.com/cloud-storage/pricing"),
]

ATENCAO = [
    ("Calor", "O Pi 4 e a Camera Module 3 são garantidos só de 0 a 50 °C de ambiente. Um estudo da Arizona State University mediu painel a 69 °C depois de 1 hora ao sol. "
     "A caixa fica fora do sol direto, com ventoinha, e o software registra a temperatura (RNF-08). Medir a temperatura dentro da caixa num dia de sol antes do piloto."),
    ("Pico elétrico do caminhão", "Pela ISO 16750-2, o pico ao desconectar a bateria em movimento chega a 58 V em sistema 24 V. Conversores de 9–36 V e a SH-RPi (proteção de 33 V) não cobrem esse pico: "
     "para frota 24 V, conversor de 18–75 V ou supressor na entrada. Testar também partida a frio (~8 V em 12 V)."),
    ("Bateria de lítio na cabine", "Não instalar UPS com baterias 18650 no veículo: a célula tem carga limitada a 45–50 °C e descarga recomendada até 60 °C, abaixo do painel ao sol. "
     "Usar retenção por supercapacitor. O Geekworm X728 (R$ 400,16, só entrada de 5 V) serve só na bancada."),
    ("Coleta pelo USB-C", "O USB-C do Pi 4 funciona como dispositivo, mas nesse modo quem alimenta a placa é o computador. A Raspberry Pi avisa que porta de notebook pode não dar corrente "
     "e a conexão cai. O Windows precisa de um driver instalado uma vez. Testar no computador da empresa antes de comprar em quantidade."),
    ("Pupila em 640×480", "Com a lente padrão a 70 cm, a pupila fica com só 3 a 6 pixels em 640×480. A medida da pupila precisa ser testada com captura em resolução maior e recorte da região dos olhos."),
    ("Segurança dos LEDs", "Usar LEDs com intensidade informada no datasheet e somar até ~1 W/sr. Placas de LED de \"3 W\" sem dados não podem ser classificadas. "
     "Produto vendido a clientes precisa de laudo IEC 62471 de laboratório."),
    ("Corte de energia e cartão", "Nenhum cartão \"high endurance\" promete proteção contra queda de energia. A proteção vem do projeto: gravação por acréscimo com fsync, desligamento seguro e retenção de energia (spec 001)."),
    ("Bateria do relógio", "Módulos DS3231 com circuito de carga (o comum ZS-042) não podem usar CR2032, que não é recarregável: tirar o resistor ou o diodo de carga, ou usar bateria recarregável."),
    ("Pi 4 ou Pi 5", "O PRD ainda registra a recomendação de 14/09 de trocar para o Pi 5 de 4 GB, aguardando confirmação. Esta lista segue o Pi 4, que tem saída de áudio P2, codificador H.264 no chip e "
     "USB-C que funciona como dispositivo, mas não tem relógio (por isso o DS3231). Com o Pi 5, mudam fonte (5 A), áudio, cabo da câmera (conector mini) e relógio."),
    ("Caixa removível", "A coleta prevê recolher a caixa e ligar no computador. Com cabo flat de 30 a 50 cm, a câmera fica presa na própria caixa (senão o flat precisa ser solto a cada coleta). "
     "Decidir: caixa inteira removível pelo conector Superseal, ou caixa fixa com coleta por cabo levado até um ponto acessível ou por pen drive."),
    ("Peças genéricas do AliExpress", "Conversor, módulo MOSFET, optoacoplador e LEDs vêm sem ficha técnica confiável. Antes de montar a segunda caixa, medir na bancada: tensão do conversor com carga, "
     "acionamento do MOSFET com 3,3 V e corrente dos LEDs."),
]

# ------------------------------------------------------------------ contas
def custo_br(it):
    return None if it["preco"] is None else it["preco"] * it["qtd"]

def custo_ali(it):
    a = it["ali"]
    if not a: return None
    pacotes = math.ceil(it["qtd"] / a["pacote"])
    produto = a["preco"] * pacotes
    base = produto + a["frete"]
    imp = imposto_ali(base)
    return dict(pacotes=pacotes, produto=produto, frete=a["frete"], imposto=imp, total=base + imp)

def escolha(it):
    br, ali = custo_br(it), custo_ali(it)
    if br is None and ali is None: return None
    if it["escolha"] == "br" and br is not None: return "br"
    if br is None: return "ali"
    if ali is None: return "br"
    return "ali" if ali["total"] <= br * (1 - ECONOMIA_MIN) else "br"

def custo_na_conta(it):
    e = escolha(it)
    return None if e is None else (custo_br(it) if e == "br" else custo_ali(it)["total"])

GRUPOS_NEC = [("caixa", "Caixa do veículo, uma unidade", COMPUTADOR + CAMERA + ENERGIA + ALARME + CAIXA),
              ("montagem", "Peças de montagem da caixa", MONTAGEM),
              ("kit", "Kits de instalação", KITS),
              ("banc", "Bancada", BANCADA)]

def soma(itens, modo):
    t, faltam = 0.0, 0
    for it in itens:
        v = custo_br(it) if modo == "br" else custo_na_conta(it)
        if v is None: faltam += 1
        else: t += v
    return t, faltam

T_NEC = sum(soma(l, "conta")[0] for _, _, l in GRUPOS_NEC)
T_NEC_BR = sum(soma(l, "br")[0] for _, _, l in GRUPOS_NEC)
T_OPC = soma(OPCIONAIS, "conta")[0]
T_OPC_BR = soma(OPCIONAIS, "br")[0]
SEM_PRECO_NEC = [it["nome"] for _, _, l in GRUPOS_NEC for it in l if custo_na_conta(it) is None]
TODOS = COMPUTADOR + CAMERA + ENERGIA + ALARME + CAIXA + MONTAGEM + KITS + BANCADA + OPCIONAIS
N_LISTA = sum(1 for it in TODOS if it["ali"] and it["ali"]["lista"])
ECONOMIA_NEC = sum(custo_br(it) - custo_na_conta(it) for _, _, l in GRUPOS_NEC for it in l if custo_br(it) is not None)

# ------------------------------------------------------------------ html
def celula_br(it, na_conta):
    tag = '<span class="tag">na conta</span>' if na_conta else ""
    v = custo_br(it)
    if v is None:
        return f'<span class="valor vazio">{E(it["preco_txt"] or "sem preço pesquisado")}</span>' + (f'<span class="det">{it["onde"]}</span>' if it["onde"] else "")
    det = f'{it["qtd"]} × {brl(it["preco"])}' if it["qtd"] > 1 else ""
    partes = [f'<span class="valor">{brl(v)}{tag}</span>']
    if det: partes.append(f'<span class="det">{E(det)}</span>')
    if it["ref"]: partes.append('<span class="det ref">preço de referência</span>')
    partes.append(f'<span class="det">{it["onde"]}</span>')
    if it["estoque"]: partes.append(f'<span class="det">{E(it["estoque"])}</span>')
    return "".join(partes)

def celula_ali(it, na_conta):
    a, c = it["ali"], custo_ali(it)
    if not c:
        return '<span class="valor vazio">' + ("fora da conta (ver nota)" if it["escolha"] == "br" else "não pesquisado") + '</span>'
    tag = '<span class="tag">na conta</span>' if na_conta else ""
    qtd = f'{c["pacotes"]} × ' if c["pacotes"] > 1 else ""
    frete = "frete grátis" if a["frete"] == 0 else f'frete {brl(a["frete"])}'
    partes = [f'<span class="valor">{brl(c["total"])}{tag}</span>',
              f'<span class="det">{qtd}{brl(a["preco"])} + {frete} + impostos {brl(c["imposto"])}</span>',
              f'<span class="det">{link(a["loja"], a["url"])} · {E(a["var"])}</span>',
              f'<span class="det">{E(a["dias"])} dias</span>']
    if a["lista"]: partes.append('<span class="det ref">preço da lista de busca</span>')
    if a["obs"]: partes.append(f'<span class="det risco">{E(a["obs"])}</span>')
    return "".join(partes)

def tabela(itens):
    linhas = []
    for it in itens:
        e = escolha(it)
        cls_br = "" if e == "br" else " fora"
        cls_ali = "" if e == "ali" else " fora"
        qtd = it["qtd"]
        linhas.append(
            f'<tr><td class="c-item"><b>{E(it["nome"])}</b><span>{E(it["modelo"])}</span></td>'
            f'<td class="c-qtd">{qtd}</td><td class="c-preco{cls_br}">{celula_br(it, e == "br")}</td>'
            f'<td class="c-preco{cls_ali}">{celula_ali(it, e == "ali")}</td><td class="c-nota">{E(it["nota"])}</td></tr>')
    return ('<table class="itens"><colgroup><col style="width:21%"><col style="width:4%"><col style="width:17%"><col style="width:21%"><col style="width:37%"></colgroup>'
            '<thead><tr><th>Item</th><th>Qtd</th><th>Brasil</th><th>AliExpress, com frete e impostos</th><th>Por que e atenção</th></tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table>')

DIAGRAMA = """
<svg viewBox="0 0 720 300" role="img" aria-label="Diagrama da caixa" class="diag">
  <defs><marker id="s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#5a5d63"/></marker></defs>
  <g font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="12" fill="#1c1d1f">
    <rect x="10" y="20" width="150" height="54" rx="8" fill="#f3efe6" stroke="#c9c2b3"/>
    <text x="85" y="42" text-anchor="middle" font-weight="600">Veículo 12 ou 24 V</text>
    <text x="85" y="60" text-anchor="middle" font-size="11">positivo pós-chave (ACC)</text>
    <rect x="10" y="110" width="150" height="54" rx="8" fill="#f3efe6" stroke="#c9c2b3"/>
    <text x="85" y="132" text-anchor="middle" font-weight="600">Fusível 2 a 3 A</text>
    <text x="85" y="150" text-anchor="middle" font-size="11">derivador + conector</text>
    <rect x="10" y="200" width="150" height="70" rx="8" fill="#f3efe6" stroke="#c9c2b3"/>
    <text x="85" y="224" text-anchor="middle" font-weight="600">Energia 5,1 V</text>
    <text x="85" y="242" text-anchor="middle" font-size="11">conversor 12/24 V</text>
    <text x="85" y="258" text-anchor="middle" font-size="11">(ou SH-RPi, opcional)</text>
    <rect x="260" y="95" width="200" height="110" rx="10" fill="#fff" stroke="#1c1d1f" stroke-width="1.6"/>
    <text x="360" y="125" text-anchor="middle" font-weight="700" font-size="14">Raspberry Pi 4 · 4 GB</text>
    <text x="360" y="146" text-anchor="middle" font-size="11">microSD high endurance 64 GB</text>
    <text x="360" y="163" text-anchor="middle" font-size="11">RTC DS3231 no GPIO</text>
    <text x="360" y="180" text-anchor="middle" font-size="11">case de alumínio com cooler</text>
    <rect x="540" y="20" width="170" height="60" rx="8" fill="#f3efe6" stroke="#c9c2b3"/>
    <text x="625" y="44" text-anchor="middle" font-weight="600">Camera Module 3 NoIR</text>
    <text x="625" y="62" text-anchor="middle" font-size="11">+ LEDs 940 nm, a ~70 cm</text>
    <rect x="540" y="120" width="170" height="60" rx="8" fill="#f3efe6" stroke="#c9c2b3"/>
    <text x="625" y="144" text-anchor="middle" font-weight="600">Sirene 12/24 V</text>
    <text x="625" y="162" text-anchor="middle" font-size="11">por MOSFET (GPIO)</text>
    <rect x="540" y="220" width="170" height="60" rx="8" fill="#f3efe6" stroke="#c9c2b3"/>
    <text x="625" y="244" text-anchor="middle" font-weight="600">Computador da empresa</text>
    <text x="625" y="262" text-anchor="middle" font-size="11">USB-C de dados ou pen drive</text>
    <g stroke="#5a5d63" stroke-width="1.6" fill="none">
      <path d="M85 74 V108" marker-end="url(#s)"/>
      <path d="M85 164 V198" marker-end="url(#s)"/>
      <path d="M160 235 H210 V150 H258" marker-end="url(#s)"/>
      <path d="M160 128 H258" stroke-dasharray="4 3" marker-end="url(#s)"/>
      <path d="M540 50 H500 V120 H462" marker-end="url(#s)"/>
      <path d="M462 150 H538" marker-end="url(#s)"/>
      <path d="M462 180 H500 V250 H538" marker-end="url(#s)"/>
    </g>
    <text x="172" y="121" font-size="10" fill="#5a5d63">sinal da chave</text>
    <text x="504" y="92" font-size="10" fill="#5a5d63">flat 30–50 cm</text>
  </g>
</svg>"""

def resumo():
    linhas = []
    for _, rotulo, l in GRUPOS_NEC:
        br, faltam_br = soma(l, "br")
        conta, _ = soma(l, "conta")
        br_txt = brl(br) if br else "—"
        if faltam_br: br_txt += f' <small>(sem {faltam_br} {"item" if faltam_br == 1 else "itens"})</small>'
        linhas.append(f'<tr><td>{E(rotulo)}</td><td class="num">{br_txt}</td><td class="num">{brl(conta)}</td></tr>')
    faltam_opc = soma(OPCIONAIS, "br")[1]
    return f"""
<div class="cards">
  <div class="card forte"><small>Total necessário · compra única</small><b>{brl(T_NEC)}</b><p>1 caixa completa, peças de montagem, kits de instalação e bancada. Usa o AliExpress onde ele sai 15% ou mais barato, já com frete e impostos.</p></div>
  <div class="card forte"><small>VPS necessária · por mês</small><b>≈ {brl(VPS_PILOTO_MES)}</b><p>Piloto de 5 veículos quando ligar a sincronização: Hostinger KVM 2 + Magalu + domínio. {brl(VPS_PILOTO_RENOVA)} depois da renovação.</p></div>
  <div class="card forte"><small>Protótipo custo-benefício</small><b>{brl(T_PROTO)}</b><p>Uma caixa na bancada, sem o que só serve dentro do veículo, com câmera e alarme simples (seção 5).</p></div>
  <div class="card"><small>Opcional completo</small><b>{brl(T_OPC)}</b><p>Todos os opcionais da seção 7 somados. Fora da soma: a placa SH-RPi, esgotada.</p></div>
</div>
<table class="simples totais inteiro"><thead><tr><th>Parte</th><th class="num">Só lojas brasileiras</th><th class="num">Na conta (Brasil + AliExpress)</th></tr></thead><tbody>
{"".join(linhas)}
<tr class="soma"><td>Total necessário, compra única</td><td class="num">{brl(T_NEC_BR)}</td><td class="num">{brl(T_NEC)}</td></tr>
<tr><td>VPS do piloto, por mês</td><td class="num">≈ {brl(VPS_PILOTO_MES)}</td><td class="num">≈ {brl(VPS_PILOTO_MES)}</td></tr>
<tr><td>Protótipo custo-benefício (seção 5)</td><td class="num">—</td><td class="num">{brl(T_PROTO)}</td></tr>
<tr class="opc"><td>Opcional completo</td><td class="num">{brl(T_OPC_BR)}{f' <small>(sem {faltam_opc} itens)</small>' if faltam_opc else ""}</td><td class="num">{brl(T_OPC)}</td></tr>
</tbody></table>
<p class="nota-tab">"Só lojas brasileiras" não soma as peças que não têm preço nacional pesquisado. Nos itens necessários que têm preço no Brasil, o AliExpress economiza {brl(ECONOMIA_NEC)}, com prazo de 10 a 26 dias. Como o preço do AliExpress foi calculado: seção 8.</p>"""


# ------------------------------------------------------------------ protótipo: versão custo-benefício
# Cada linha compara o que a lista completa manda comprar com o que basta para provar o programa na bancada.
def P(nome, base, alt_txt, alt_valor, muda):
    return dict(nome=nome, base=base, alt_txt=alt_txt, alt=alt_valor, muda=muda)

def _c(*itens):  # quanto esses itens custam na conta da lista completa
    return sum(custo_na_conta(it) or 0 for it in itens)

ALT_CAMERA = 22.20   # OV5647 NoIR com 2 LEDs, o mesmo anúncio do teste rápido da seção 7
ALT_CASE = 10.44     # case de ABS com ventoinha (R$ 8,35 + impostos), preço da lista de busca
ALT_BUZZER = 6.56    # buzzer ativo de 3,3 a 5 V (R$ 5,25 + impostos), preço da lista de busca

PROTOTIPO = [
    P("Computador", _c(COMPUTADOR[0]), "o mesmo Raspberry Pi 4 de 4 GB", _c(COMPUTADOR[0]),
      "Nada: é 76% do protótipo e não tem troca à altura. O Pi 5 de 4 GB aparece mais barato nos anúncios, mas muda áudio, cabo da câmera, fonte e codificador de vídeo, "
      "e a troca ainda depende da decisão registrada na seção 9."),
    P("Cartão de memória", _c(COMPUTADOR[1]), "SanDisk High Endurance 64 GB no AliExpress", 158.09,
      "Garante 5.000 h de gravação, contra 30.000 h da MAX Endurance, e a loja não tem ligação com a marca. Serve para testar; no produto, voltar para a MAX com nota fiscal."),
    P("Relógio (RTC)", _c(COMPUTADOR[2]), "o mesmo DS3231", _c(COMPUTADOR[2]),
      "Nada. Na bancada com rede o Pi pega a hora sozinho, mas por R$ 8,74 já dá para testar o comportamento da spec 003."),
    P("Câmera", _c(CAMERA[0]), "câmera OV5647 NoIR com 2 LEDs infravermelhos", ALT_CAMERA,
      "Perde foco automático, 12 MP e HDR. Dá para validar olho fechado, bocejo e o programa inteiro; a medida da pupila só fecha com a Camera Module 3."),
    P("Iluminação infravermelha", _c(CAMERA[1]), "os 2 LEDs que vêm na própria câmera", 0,
      "Perde o dado de segurança ocular da Vishay (seção 9): manter a ~70 cm no teste. Para o veículo, comprar os TSAL6200."),
    P("Cabo e suporte da câmera", _c(CAMERA[2], CAMERA[3]), "o cabo curto do próprio módulo, preso com fita", 0,
      "Na bancada não faz falta. O flat de 50 cm só é preciso quando a câmera for para o para-brisa."),
    P("Dissipação", _c(CAIXA[1]), "case de ABS com ventoinha", ALT_CASE,
      "Dissipa bem menos: serve em mesa, não no painel ao sol. Trocar antes do teste no veículo."),
    P("Alarme", _c(ALARME[0]), "buzzer ativo de 5 V", ALT_BUZZER,
      "Não dá para medir o nível dentro da cabine (ISO 7731). A sirene DNI entra junto com a instalação."),
    P("Caixa e passagem de cabo", _c(CAIXA[0], CAIXA[2]), "fica de fora", 0,
      "Nada na bancada; entra quando a caixa for para o veículo."),
    P("Energia do veículo", _c(ENERGIA[0]), "fica de fora", 0,
      "Na bancada quem alimenta o Pi é a fonte oficial de 15 W."),
    P("Peças de montagem", _c(*MONTAGEM), "só os jumpers do GPIO", custo_na_conta(MONTAGEM[5]),
      "Optoacoplador, MOSFET, placa, resistores, difusor, fio e TVS entram na montagem definitiva."),
    P("Kits de instalação", sum(custo_na_conta(it) or 0 for it in KITS), "ficam de fora", 0,
      "Só servem para instalar a caixa no veículo."),
    P("Bancada", sum(custo_na_conta(it) or 0 for it in BANCADA), "fonte oficial, leitor e cabo USB-C", sum(custo_na_conta(it) or 0 for it in BANCADA),
      "Nada. Se o computador já tiver leitor de microSD, tira R$ 28,54."),
    P("VPS", 0, "fica de fora", 0,
      "O painel roda no computador da empresa; a VPS só quando ligar a sincronização."),
]
T_PROTO = sum(r["alt"] for r in PROTOTIPO)

def secao_prototipo():
    linhas = "".join(
        f'<tr><td><b>{E(r["nome"])}</b></td>'
        f'<td class="num">{brl(r["base"]) if r["base"] else "—"}</td>'
        f'<td class="num">{brl(r["alt"]) if r["alt"] else "—"}<span class="alt">{E(r["alt_txt"])}</span></td>'
        f'<td>{E(r["muda"])}</td></tr>' for r in PROTOTIPO)
    return f"""
<section class="sec">
<h2><span>5</span> Protótipo: versão custo-benefício <em class="grupo">uma caixa, na bancada</em></h2>
<p class="lead">Para provar que o programa funciona — detecção, registro, relógio, alarme e coleta — antes de gastar com o que só serve dentro do veículo.
Sai por <b>{brl(T_PROTO)}</b>, contra {brl(T_NEC)} da lista completa: <b>{brl(T_NEC - T_PROTO)} a menos</b>.</p>
<table class="simples totais"><colgroup><col style="width:17%"><col style="width:13%"><col style="width:27%"><col style="width:43%"></colgroup>
<thead><tr><th>Item</th><th class="num">Lista completa</th><th class="num">No protótipo</th><th>O que muda</th></tr></thead>
<tbody>{linhas}
<tr class="soma"><td>Total</td><td class="num">{brl(T_NEC)}</td><td class="num">{brl(T_PROTO)}</td><td>Mais ≈ {brl(VPS_PILOTO_MES)} por mês de VPS, só quando ligar a sincronização.</td></tr>
</tbody></table>
<div class="aviso"><b>O que não vale cortar</b><p>Fonte oficial de 15 W (fonte fraca derruba o Pi por subtensão), cartão com endurance (a caixa grava o tempo todo) e o próprio Pi 4 de 4 GB.
Cortar câmera e alarme adia só a medida da pupila e o teste de nível de som, que dependem de veículo real de qualquer jeito.</p></div>
</section>"""

def secao_vps():
    planos = "".join(f'<tr><td><b>{E(a)}</b></td><td>{E(b)}</td><td>{E(c)}</td><td>{E(d)}</td><td>{E(e)}</td><td>{E(f)}</td><td>{link(g, h)}</td></tr>' for a, b, c, d, e, f, g, h in VPS_PLANOS)
    esc = "".join(f'<tr><td><b>{E(a)}</b></td><td>{E(b)}</td><td>{E(c)}</td><td>{E(d)}</td></tr>' for a, b, c, d in VPS_ESCALA)
    obj = "".join(f'<tr><td><b>{link(a, e)}</b></td><td>{E(b)}</td><td>{E(c)}</td><td>{E(d)}</td></tr>' for a, b, c, d, e in OBJETOS)
    return f"""
<section class="sec">
<h2><span>6</span> VPS e nuvem <em class="grupo">necessário</em></h2>
<p class="lead">Hoje o painel e os dados ficam no computador da empresa. A VPS entra quando as caixas e o painel passarem a sincronizar (PRD, 14/09/2026). O servidor é FastAPI com PostgreSQL 18 em Docker Compose. Entra no total como custo mensal.</p>
<div class="aviso"><b>Recomendação</b><p>VPS da <b>Hostinger em São Paulo</b> e vídeos e cópias de segurança no <b>armazenamento de objetos da Magalu Cloud</b> (São Paulo). São dois provedores diferentes, os dois com dados no Brasil (LGPD). Separar o vídeo já no piloto custa ~R$ 1,21 por mês e evita refazer tudo com 50 veículos.</p></div>
<h3>Plano por tamanho da frota</h3>
<p class="nota-tab">Premissas: 22 viagens por veículo por mês, registro de ~5 MB por viagem e, no pior caso, 110 MB de vídeo por viagem (12 trechos de 20 s) guardados 30 dias. A memória e o disco são estimativas para medir no piloto.</p>
<table class="simples"><thead><tr><th>Frota</th><th>Plano</th><th>Vídeo guardado</th><th>Custo mensal total</th></tr></thead><tbody>{esc}</tbody></table>
<h3>VPS com datacenter no Brasil</h3>
<table class="simples compacta"><thead><tr><th>Provedor</th><th>Plano</th><th>vCPU</th><th>RAM</th><th>Disco</th><th>Preço por mês</th><th>Região</th></tr></thead><tbody>{planos}</tbody></table>
<p class="nota-tab">Contabo não tem datacenter no Brasil. Dólar convertido pelo PTAX de venda de 17/09/2026 (R$ 5,1521), sem IOF.</p>
<h3>Armazenamento de objetos para vídeos e cópias</h3>
<table class="simples compacta inteiro"><thead><tr><th>Serviço</th><th>Guardar</th><th>Saída (download)</th><th>Dados no Brasil</th></tr></thead><tbody>{obj}</tbody></table>
<h3>Domínio, HTTPS e operação</h3>
<ul class="lista">
<li><b>Domínio .com.br:</b> R$ 40,00 por ano no {link("Registro.br", "https://registro.br/ajuda/precos/")}. A VPS já vem com IPv4 fixo; as caixas e o painel não precisam de IP fixo.</li>
<li><b>HTTPS:</b> certificado grátis do {link("Let's Encrypt", "https://letsencrypt.org/docs/faq/")}, renovado sozinho pelo Caddy. A validade padrão cai de 90 para 64 dias em 10/02/2027.</li>
<li><b>Sistema:</b> Debian 13 (segurança até 09/08/2028, LTS até 30/06/2030), a mesma base da imagem python:3.14-slim-trixie. Ubuntu 26.04 LTS se o provedor oferecer.</li>
<li><b>Cópia do banco:</b> pg_dump diário dentro do contêiner postgres:18, cifrado e enviado a outro provedor; guardar 7 diárias e 4 semanais e testar a restauração por mês. Acima de ~50 GB de banco, pgBackRest ou WAL-G.</li>
<li><b>Monitoramento grátis:</b> {link("UptimeRobot", "https://help.uptimerobot.com/en/articles/11604710-who-should-use-uptimerobot-s-free-plan")} (50 monitores, uso comercial permitido) e {link("Healthchecks.io", "https://healthchecks.io/pricing/")} para avisar se a cópia não rodar.</li>
<li><b>Custo zero:</b> Oracle Always Free em São Paulo existe, mas a Oracle pode recolher máquina ociosa e já reduziu a franquia em 2026. Não usar para cliente.</li>
</ul>
</section>"""

def secao_itens(num, titulo, grupo, lead, blocos, classe="sec"):
    corpo = "".join((f'<h3>{E(t)}</h3>' if t else "") + tabela(l) for t, l in blocos)
    return f'<section class="{classe}"><h2><span>{num}</span> {E(titulo)} <em class="grupo">{E(grupo)}</em></h2><p class="lead">{lead}</p>{corpo}</section>'

def secao_metodo():
    ex_pi = COMPUTADOR[0]; c = custo_ali(ex_pi)
    return f"""
<section class="sec">
<h2><span>8</span> Como o preço do AliExpress foi calculado</h2>
<p class="lead">Os preços foram lidos em {DATA} nas páginas do AliExpress Brasil, com navegador automatizado, na variante exata (memória, comprimento, tamanho do pacote). Vale a promoção do dia, sem cupom de novo usuário.</p>
<ul class="lista">
<li><b>Frete:</b> o da opção padrão mostrada na página. Itens do AliExpress Choice aparecem com frete grátis; os demais, com o valor cobrado.</li>
<li><b>Impostos:</b> pela {link("Portaria MF 1.342/2026", "https://blog.econeteditora.com.br/remessa-conforme-o-que-muda-com-a-portaria-mf-1-342-2026/")}, de 12/05/2026, e pelo texto de tributos da própria página. Pedido de até US$ 50 não paga Imposto de Importação. Acima de US$ 50 paga 60%, com desconto de US$ 30. O ICMS vai de 17% a 20% conforme o estado e é calculado por dentro; a conta usa 20%, o pior caso, o que soma 25% sobre preço e frete.</li>
<li><b>Câmbio:</b> R$ {str(CAMBIO_ALI).replace(".", ",")} por dólar, o valor que reproduz as estimativas de imposto das próprias páginas. Exemplo: câmera de R$ 386,59 com estimativa de R$ 178,46.</li>
<li><b>Um item por pedido:</b> cada item foi contado como um pedido. O imposto é calculado por pedido: juntar outro item ao pedido do Pi 4 ({brl(c["produto"] + c["frete"])} de base, acima de US$ 50) faz esse item pagar os 60% também.</li>
<li><b>Quando o AliExpress entra na conta:</b> só quando sai pelo menos {int(ECONOMIA_MIN * 100)}% mais barato que a loja brasileira, para compensar o prazo e a devolução internacional. Cartão de memória, cabo de alimentação e sirene ficam no Brasil mesmo mais caros: risco de falsificação ou falta de ficha técnica. Nos itens sem preço nacional, entra o AliExpress.</li>
<li><b>Sem nota fiscal brasileira e sem selo Anatel.</b> Para o protótipo serve. Para caixa vendida ou instalada em cliente, confirmar antes a exigência de homologação.</li>
<li><b>{N_LISTA} itens pequenos ficaram só com o preço da lista de busca</b>, marcados assim na tabela: no meio da pesquisa a loja passou a bloquear a leitura da página do produto. Neles, o preço é o da variante mais barata e o frete não foi confirmado; a conta supõe que vão juntos num pedido do Choice, com frete grátis. Conferir no carrinho antes de fechar.</li>
<li><b>Preço muda:</b> alguns itens mudaram alguns reais entre duas visitas no mesmo dia. Conferir no carrinho antes de pagar.</li>
<li>Mercado Livre, Magazine Luiza e Shopee continuam bloqueando a consulta automática: nenhum preço dessas lojas está nesta lista. Preços da Amazon marcados como importados já incluem o imposto estimado pela própria Amazon.</li>
</ul>
</section>"""

CSS = """
@page { size: A4; margin: 15mm 13mm 17mm 13mm;
  @bottom-left { content: "RotaGuard · lista de compras de hardware e VPS · 17/09/2026"; font: 7.5pt 'IBM Plex Sans', 'Segoe UI', sans-serif; color: #6b6e74; }
  @bottom-right { content: "página " counter(page) " de " counter(pages); font: 7.5pt 'IBM Plex Mono', Consolas, monospace; color: #6b6e74; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font: 9pt/1.42 'IBM Plex Sans', 'Segoe UI', Arial, sans-serif; color: #1c1d1f; background: #fff; }
a { color: #7f4c00; text-decoration: underline; text-decoration-thickness: .5pt; text-underline-offset: 1.5pt; }
h1 { font-size: 23pt; line-height: 1.08; margin: 4px 0 8px; letter-spacing: -.01em; }
h2 { font-size: 14.5pt; margin: 0 0 6px; display: flex; align-items: baseline; gap: 8px; break-after: avoid; }
h2 span { font: 600 10pt 'IBM Plex Mono', Consolas, monospace; color: #fff; background: #1c1d1f; border-radius: 4px; padding: 1px 6px; }
h2 em.grupo { font: 600 7.5pt 'IBM Plex Sans', sans-serif; font-style: normal; text-transform: uppercase; letter-spacing: .06em; color: #5a5d63; border: 1px solid #c9c2b3; border-radius: 3px; padding: 1px 5px; }
h3 { font-size: 10.5pt; margin: 14px 0 5px; break-after: avoid; }
.topo { border-bottom: 2px solid #1c1d1f; padding-bottom: 10px; margin-bottom: 12px; }
.marca { font: 600 8.5pt 'IBM Plex Mono', Consolas, monospace; letter-spacing: .12em; text-transform: uppercase; color: #7f4c00; }
.sub { font-size: 10.5pt; color: #3d4046; max-width: 170mm; margin: 0; }
.meta { font: 8pt 'IBM Plex Mono', Consolas, monospace; color: #5a5d63; margin-top: 6px; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin: 10px 0 8px; }
.card { border: 1px solid #d9d4c8; border-radius: 6px; padding: 7px 8px; background: #faf8f3; break-inside: avoid; }
.card.forte { border-color: #1c1d1f; background: #fff; }
.card small { display: block; font-size: 7.5pt; color: #5a5d63; text-transform: uppercase; letter-spacing: .04em; }
.card b { display: block; font: 600 15pt 'IBM Plex Mono', Consolas, monospace; margin: 2px 0; }
.card p { margin: 0; font-size: 7.6pt; color: #3d4046; line-height: 1.3; }
.sec { margin-top: 14px; }
.quebra + .sec, .sec.quebra { margin-top: 0; }
.lead { margin: 0 0 4px; color: #3d4046; }
.diag { width: 100%; height: auto; margin: 4px 0 2px; }
table { width: 100%; border-collapse: collapse; margin: 2px 0 6px; }
.itens { table-layout: fixed; }
.inteiro { break-inside: avoid; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { text-align: left; font-size: 7.4pt; text-transform: uppercase; letter-spacing: .05em; color: #5a5d63; border-bottom: 1.2px solid #1c1d1f; padding: 3px 4px; }
td { vertical-align: top; padding: 4px 4px; border-bottom: .6px solid #dedad2; }
.itens .c-item b { display: block; font-size: 8.3pt; } .itens .c-item span { display: block; font-size: 8.1pt; color: #2a2c30; }
.itens .c-qtd { text-align: center; font-family: 'IBM Plex Mono', Consolas, monospace; }
.itens .c-preco .valor { display: block; font: 600 8.6pt 'IBM Plex Mono', Consolas, monospace; }
.itens .c-preco .valor.vazio { font-weight: 400; font-size: 7.8pt; color: #6b6e74; }
.itens .c-preco.fora .valor { font-weight: 400; color: #6b6e74; }
.itens .c-preco .det { display: block; font-size: 7.3pt; line-height: 1.3; color: #4a4d53; overflow-wrap: anywhere; }
.itens .c-preco .det.risco { color: #8a3f00; }
.itens .c-preco .det.ref { color: #7f4c00; }
.itens .c-nota { font-size: 7.8pt; color: #2a2c30; }
.tag { display: table; margin: 1px 0; font: 600 6.4pt 'IBM Plex Sans', sans-serif; text-transform: uppercase; letter-spacing: .05em; color: #fff; background: #7f4c00; border-radius: 3px; padding: 0 4px; vertical-align: 1px; }
.simples td, .simples th { font-size: 8.2pt; } .compacta td { padding: 3px 4px; font-size: 7.9pt; }
.totais .num { text-align: right; font-family: 'IBM Plex Mono', Consolas, monospace; white-space: nowrap; }
.totais th.num { font-family: 'IBM Plex Sans', sans-serif; }
.totais small { font-family: 'IBM Plex Sans', sans-serif; font-size: 7pt; color: #6b6e74; }
.totais tr.soma td { font-weight: 700; border-top: 1.2px solid #1c1d1f; border-bottom: 1.2px solid #1c1d1f; }
.totais tr.opc td { color: #5a5d63; }
.totais .alt { display: block; font: 400 7.4pt 'IBM Plex Sans', sans-serif; color: #5a5d63; }
.nota-tab { font-size: 7.8pt; color: #5a5d63; margin: 2px 0 4px; break-after: avoid; }
.aviso { border-left: 3px solid #b86e00; background: #faf5ea; padding: 6px 9px; margin: 6px 0; break-inside: avoid; }
.aviso > b { display: block; font-size: 8.5pt; } .aviso p { margin: 2px 0 0; }
.atencao { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.atencao .aviso { margin: 0; } .atencao .aviso p { font-size: 8pt; }
.lista { margin: 4px 0; padding-left: 14px; } .lista li { margin: 2px 0; }
.passos { counter-reset: p; list-style: none; padding: 0; margin: 4px 0; }
.passos li { counter-increment: p; position: relative; padding-left: 20px; margin: 3px 0; }
.passos li::before { content: counter(p); position: absolute; left: 0; top: 0; font: 600 8pt 'IBM Plex Mono', monospace; background: #1c1d1f; color: #fff; border-radius: 3px; padding: 0 4px; }
.quebra { break-before: page; }
.fontes { font-size: 7.8pt; } .fontes h4 { font-size: 8.3pt; margin: 8px 0 2px; break-after: avoid; }
.fontes ul { margin: 0; padding-left: 12px; } .fontes li { margin: 1px 0; overflow-wrap: anywhere; }
"""

FONTES = [
    ("Raspberry Pi 4", ["https://www.raspberrypi.com/products/raspberry-pi-4-model-b/specifications/", "https://pip.raspberrypi.com/documents/RP-008344-DS-raspberry-pi-4-product-brief.pdf",
                        "https://www.raspberrypi.com/resellers/", "https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply-warnings",
                        "https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/", "https://downloads.raspberrypi.com/raspios_arm64/release_notes.txt"]),
    ("Cartões e relógio", ["https://documents.sandisk.com/content/dam/asset-library/en_us/assets/public/sandisk/product/memory-cards/max-endurance-uhs-i-microsd/data-sheet-max-endurance-uhs-i-microsd.pdf",
                           "https://download.semiconductor.samsung.com/resources/data-sheet/samsung_data_sheet_2022_pro_endurance_card_rev.1.0.pdf",
                           "https://documents.sandisk.com/content/dam/asset-library/en_us/assets/public/sandisk/product/memory-cards/high-endurance-uhs-i-microsd/data-sheet-high-endurance-uhs-i-microsd.pdf",
                           "https://www.onetransistor.eu/2019/07/zs042-ds3231-battery-charging-circuit.html", "https://raw.githubusercontent.com/raspberrypi/firmware/master/boot/overlays/README"]),
    ("Câmera e infravermelho", ["https://datasheets.raspberrypi.com/camera/camera-module-3-product-brief.pdf", "https://github.com/raspberrypi/picamera2",
                                "https://www.vishay.com/docs/81935/eyesafe.pdf", "https://lumileds.com/AB191-4-LUXEON-IR-Family-Eye-Safety-Application-Brief",
                                "https://forums.raspberrypi.com/viewtopic.php?t=262041", "https://forums.raspberrypi.com/viewtopic.php?t=368030"]),
    ("Energia, calor e som", ["https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ApplicationNotes/ApplicationNotes/Automotive-Cold-Crank-Load-Dump-Standards-DS00006186.pdf",
                              "https://www.meanwell.com/Upload/PDF/DDR-30/DDR-30-spec.pdf", "https://docs.hatlabs.fi/sh-rpi/hardware/",
                              "https://www.dnkpower.com/wp-content/uploads/2018/04/Samsung-INR18650-25R-Datasheet.pdf",
                              "https://www.diariodasaude.com.br/news.php?article=carros-sol-atingem-temperaturas-mortais-hora&id=12829",
                              "https://rosap.ntl.bts.gov/view/dot/14303/dot_14303_DS1.pdf", "https://abepro.org.br/biblioteca/enegep2012_TN_STP_160_934_20543.pdf",
                              "https://www.pfannenberg.com/fileadmin/Redakteur/Subsites/Files_Know-How/Know-How_Signaling/ISO_7731_-_Requirements_for_Sounders_EN.pdf",
                              "https://www.guiatrabalhista.com.br/legislacao/nr/nr-15-anexo-01.pdf", "https://dni.com.br/pt/dni4127-sirene-de-marcha-re-com-redutor-de-som-bivolt-12-24v/"]),
    ("Impostos de compra internacional", ["https://blog.econeteditora.com.br/remessa-conforme-o-que-muda-com-a-portaria-mf-1-342-2026/",
                                          "https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/manuais/remessas-postal-e-expressa/programa-remessa-conforme-o-que-e-como-funciona"]),
    ("VPS", ["https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/", "https://www.postgresql.org/docs/18/runtime-config-resource.html",
             "https://wiki.debian.org/LTS", "https://ubuntu.com/about/release-cycle", "https://letsencrypt.org/2025/12/02/from-90-to-45"]),
]

def documento():
    atencao = "".join(f'<div class="aviso"><b>{E(t)}</b><p>{E(d)}</p></div>' for t, d in ATENCAO)
    def curto(u):
        t = u.split("://", 1)[1]
        return t if len(t) <= 96 else t[:60] + "…" + t[-32:]
    fontes = "".join(f'<h4>{E(g)}</h4><ul>' + "".join(f"<li>{link(curto(u), u)}</li>" for u in us) + "</ul>" for g, us in FONTES)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>RotaGuard · lista de compras de hardware e VPS</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="topo">
  <div class="marca">RotaGuard · compras</div>
  <h1>Lista de compras: caixa do veículo,<br>bancada e VPS</h1>
  <p class="sub">Tudo o que é preciso comprar para montar a caixa com Raspberry Pi 4 (4 GB) e câmera infravermelha, instalar em veículos de 12 e 24 V, desenvolver na bancada, coletar os dados e, depois, hospedar o servidor.</p>
  <div class="meta">Preços pesquisados em {DATA} em lojas brasileiras, páginas oficiais e AliExpress Brasil (com frete e impostos) · confira preço e estoque no dia da compra · base: PRD RotaGuard 1.0 e specs 001 a 003</div>
</header>

<section>
<h2><span>1</span> Resumo</h2>
{resumo()}
<h3>O que comprar primeiro, para o protótipo de bancada</h3>
<ol class="passos">
<li><b>Peça primeiro o que vem do AliExpress</b> (10 a 26 dias): Raspberry Pi 4, Camera Module 3 NoIR, case com cooler, conversor, LEDs, cabo flat e peças de montagem.</li>
<li><b>Cartão high endurance 64 GB</b>, <b>fonte oficial 15 W</b> e <b>leitor de cartão</b> no Brasil: com o Pi, já dá para instalar o sistema e rodar o software da caixa.</li>
<li><b>RTC DS3231</b>, <b>sirene DNI 4127</b> e <b>cabo USB-C de dados</b>: testar relógio, calor, alarme e a coleta no computador.</li>
<li>Só depois dos testes da seção 9: caixa Patola e kits de instalação.</li>
</ol>
<h3>Como a caixa fica montada</h3>
{DIAGRAMA}
</section>

{secao_itens(2, "Caixa do veículo (uma por veículo)", "necessário", "Em cada linha, o preço da loja brasileira e o do AliExpress já com frete e impostos. A etiqueta <b>na conta</b> mostra qual dos dois entra no total. Itens com <b>preço de referência</b> não tinham o modelo recomendado em estoque: o preço é de um equivalente.",
             [("2.1 Computador, cartão e relógio", COMPUTADOR), ("2.2 Câmera e iluminação infravermelha", CAMERA),
              ("2.3 Energia do veículo", ENERGIA), ("2.4 Alarme sonoro", ALARME), ("2.5 Caixa e dissipação", CAIXA),
              ("2.6 Peças de montagem da placa de controle", MONTAGEM)])}

{secao_itens(3, "Kits de instalação (compra única)", "necessário", "Servem para instalar várias caixas. Pegue a energia do positivo pós-chave (ACC): com a chave desligada o consumo é zero, e desligar a chave vira o mesmo evento que perder energia.",
             [("", KITS)])}

{secao_itens(4, "Bancada de desenvolvimento e coleta (uma vez)", "necessário", "O painel roda no computador da empresa (Windows, app próprio). A coleta usa o USB-C da caixa ou um pen drive (spec 003).",
             [("", BANCADA)])}

{secao_prototipo()}

{secao_vps()}

{secao_itens(7, "Opcionais", "fora do total necessário", f"Não são precisos para a caixa funcionar. Somados, dão o valor opcional completo: <b>{brl(T_OPC)}</b>.",
             [("", OPCIONAIS)])}

{secao_metodo()}

<section class="sec">
<h2><span>9</span> Antes de comprar em quantidade: o que testar</h2>
<p class="lead">Estes pontos saíram das pesquisas e das specs. Nenhum foi medido em Raspberry Pi real ainda.</p>
<div class="atencao">{atencao}</div>
</section>

<section class="sec">
<h2><span>10</span> Fontes técnicas</h2>
<p class="lead">Os links de produto estão nas tabelas. Aqui ficam as fontes das especificações, normas, limites e impostos citados.</p>
<div class="fontes">{fontes}</div>
</section>
</body></html>"""

open(SAIDA, "w", encoding="utf-8").write(documento())
print("necessario", brl(T_NEC), "| so Brasil", brl(T_NEC_BR), "| prototipo", brl(T_PROTO), "| opcional", brl(T_OPC), "| VPS/mes", brl(VPS_PILOTO_MES))
if SEM_PRECO_NEC: print("AVISO: itens necessarios sem preco:", ", ".join(SEM_PRECO_NEC))
