"""Spec 023: tela do RotaGuard Script, antes RotaGuard Teste (servidor local, estado, resumo, malha e pacote).
TEL-01 a TEL-24; painel ao lado do vídeo refeito em 20/10 (PAI-01 a PAI-03); nome e versão (NOM-01, VER-01).

Precisa de numpy, opencv e mediapipe (caixa/requirements.txt). O pywebview não é usado aqui (a janela não abre):
    python tests/test_tela_teste.py
"""
import http.client
import importlib.util
import inspect
import json
import logging
import re
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "caixa"))
import app_teste  # noqa: E402
import run_monitor  # noqa: E402
from tela_teste import PASTA_WEB  # noqa: E402
from tela_teste import estado as estado_mod  # noqa: E402
from tela_teste import resumo as resumo_mod  # noqa: E402
from tela_teste.servidor import ServidorTela  # noqa: E402
from tela_teste.sessao import SessaoTeste, listar_cameras  # noqa: E402
from vision import driver_monitor  # noqa: E402

checks = 0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def pedir(servidor, caminho, metodo="GET", corpo=None, cabecalhos=None, token=True, ler=True):
    conexao = http.client.HTTPConnection("127.0.0.1", servidor.porta, timeout=10)
    if token is True:
        separador = "&" if "?" in caminho else "?"
        caminho = f"{caminho}{separador}t={servidor.token}"
    elif isinstance(token, str):
        separador = "&" if "?" in caminho else "?"
        caminho = f"{caminho}{separador}t={token}"
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    cabecalhos = dict(cabecalhos or {})
    if dados is not None:
        cabecalhos.setdefault("Content-Type", "application/json")
    conexao.request(metodo, caminho, body=dados, headers=cabecalhos)
    resposta = conexao.getresponse()
    if not ler:
        return resposta, conexao
    conteudo = resposta.read()
    conexao.close()
    return resposta.status, dict(resposta.getheaders()), conteudo


def estado(servidor):
    status, _, conteudo = pedir(servidor, "/estado")
    assert status == 200, status
    return json.loads(conteudo)


def agir(servidor, nome, **dados):
    origem = f"http://127.0.0.1:{servidor.porta}"
    status, _, conteudo = pedir(servidor, "/acao", "POST", {"acao": nome, **dados}, {"Origin": origem})
    return status, json.loads(conteudo or b"{}")


def esperar(condicao, limite=30.0, passo=0.05):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        valor = condicao()
        if valor:
            return valor
        time.sleep(passo)
    return condicao()


def video_sintetico(pasta: Path, segundos=4.0, fps=15) -> Path:
    caminho = pasta / "sintetico.avi"
    escritor = cv2.VideoWriter(str(caminho), cv2.VideoWriter_fourcc(*"MJPG"), fps, (320, 240))
    for i in range(int(segundos * fps)):
        quadro = np.zeros((240, 320, 3), dtype=np.uint8)
        quadro[:, :, 1] = (np.arange(320) + i * 7) % 256
        cv2.circle(quadro, (40 + (i * 5) % 240, 120), 30, (200, 200, 200), -1)
        escritor.write(quadro)
    escritor.release()
    return caminho


CAMERAS_FALSAS = [{"valor": "0", "nome": "Câmera 1", "situacao": "livre"},
                  {"valor": "1", "nome": "Câmera 2", "situacao": "ocupada"}]


def subir(pasta: Path, **opcoes):
    sessao = SessaoTeste(pasta, listar_cameras=lambda: list(CAMERAS_FALSAS), **opcoes)
    servidor = ServidorTela(sessao)
    servidor.iniciar()
    return sessao, servidor


def descer(sessao, servidor):
    sessao.encerrar()
    servidor.parar()


# ---------------------------------------------------------------- servidor: endereço, token, origem e estado inicial
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    sessao, servidor = subir(pasta)
    try:
        # TEL-01 · só 127.0.0.1, porta livre escolhida na hora
        assert servidor.httpd.server_address[0] == "127.0.0.1", servidor.httpd.server_address
        assert servidor.porta > 0 and servidor.url.startswith(f"http://127.0.0.1:{servidor.porta}/?t=")
        assert len(servidor.token) >= 32, "token de secrets.token_urlsafe(24) tem 32 caracteres"
        ok("TEL-01 servidor só em 127.0.0.1, porta escolhida na hora e token aleatório na URL")

        # TEL-02 · sem token ou com token errado: 403 em todas as rotas
        for caminho in ("/", "/index.html", "/app.css", "/app.js", "/estado", "/video.mjpg", "/legal"):
            assert pedir(servidor, caminho, token=False)[0] == 403, caminho
            assert pedir(servidor, caminho, token="errado")[0] == 403, caminho
        assert pedir(servidor, "/acao", "POST", {"acao": "malha", "modo": "completa"}, token=False)[0] == 403
        status, cabecalhos, conteudo = pedir(servidor, "/estado", token=False,
                                             cabecalhos={"X-RotaGuard-Token": servidor.token})
        assert status == 200, "o token também vale no cabeçalho"
        status, cabecalhos, conteudo = pedir(servidor, "/")
        assert status == 200 and b"<html" in conteudo.lower() and servidor.token.encode() in conteudo
        assert "default-src 'self'" in cabecalhos.get("Content-Security-Policy", "")
        assert pedir(servidor, "/../caixa/app_teste.py")[0] == 404
        assert pedir(servidor, "/estado", cabecalhos={"Host": "rotaguard.exemplo:80"})[0] == 403, "Host de fora"
        ok("TEL-02 sem token ou com token errado responde 403; token por query ou cabeçalho; só arquivos conhecidos")

        # TEL-03 · POST de outra origem: 403
        for origem in ("http://exemplo.com", f"http://127.0.0.1:{servidor.porta + 1}", "null"):
            status, _, _ = pedir(servidor, "/acao", "POST", {"acao": "malha", "modo": "completa"}, {"Origin": origem})
            assert status == 403, (origem, status)
        assert estado(servidor)["malha"] == "discreta", "spec 029: a malha começa discreta"
        status, resposta = agir(servidor, "malha", modo="completa")
        assert status == 200 and resposta.get("malha") == "completa", resposta
        assert estado(servidor)["malha"] == "completa"
        status, resposta = agir(servidor, "malha", modo="arco-iris")
        assert status == 400, "modo de malha desconhecido"
        status, resposta = agir(servidor, "nao-existe")
        assert status == 400
        ok("TEL-03 POST /acao com Origin de outro endereço responde 403; ações conhecidas e validadas")

        # MAL-08 · os modos antigos "pontos" e "essencial" saíram da tela e do /acao
        for antigo in ("pontos", "essencial"):
            status, resposta = agir(servidor, "malha", modo=antigo)
            assert status == 400, (antigo, status, resposta)
        atual = estado(servidor)
        assert atual["modos_malha"] == ["discreta", "completa", "desligada"], atual["modos_malha"]
        assert [m["rotulo"] for m in atual["modos_malha_rotulos"]] == ["Discreta", "Completa", "Só o rosto"]
        pagina = pedir(servidor, "/")[2].decode("utf-8")
        script = pedir(servidor, "/app.js")[2].decode("utf-8")
        for antigo in ('data-valor="pontos"', 'data-valor="essencial"', ">Pontos<", ">Essencial<"):
            assert antigo not in pagina, antigo
        assert '"pontos"' not in script and '"essencial"' not in script and "só pontos" not in script
        for rotulo in (">Discreta<", ">Completa<", ">Só o rosto<"):
            assert rotulo in pagina, rotulo
        ok("MAL-08 'Pontos' e 'Essencial' não aparecem na tela nem passam no /acao; modos Discreta, Completa e Só o rosto")

        # TEL-04 · antes de iniciar: fase inicio, câmeras, opções, pasta
        atual = estado(servidor)
        assert atual["fase"] == "inicio", atual["fase"]
        assert esperar(lambda: not estado(servidor)["cameras"]["procurando"], 5)
        atual = estado(servidor)
        assert atual["cameras"]["lista"] == CAMERAS_FALSAS, atual["cameras"]
        assert atual["opcoes"]["camera"] == "auto" and atual["opcoes"]["cardio"] is True
        assert atual["pasta"] == str(pasta) and atual["malha"] in driver_monitor.MESH_MODES
        assert {"Privacidade", "LGPD", "Termos de uso", "Licenças"} <= {
            secao["titulo"] for secao in json.loads(pedir(servidor, "/legal")[2])["secoes"]}
        ok("TEL-04 /estado antes de iniciar: fase inicio com a lista de câmeras, opções, pasta e textos legais")
    finally:
        descer(sessao, servidor)


# Câmeras de verdade: a primeira que abre e manda imagem é "livre"; aberta sem imagem é "ocupada"; as outras somem
class CameraFalsa:
    def __init__(self, fonte, largura, altura, avisar=True):
        self.fonte = fonte
        self.aberta = fonte in ("0", "2")
        self.liberada = False

    def read(self):
        return (True, np.zeros((2, 2, 3), dtype=np.uint8)) if self.fonte == "0" else (False, None)

    def release(self):
        self.liberada = True


lista = listar_cameras(indices=range(4), factory=CameraFalsa, pausa=0)
assert lista == [{"valor": "0", "nome": "Câmera 1", "situacao": "livre"},
                 {"valor": "2", "nome": "Câmera 3", "situacao": "ocupada"}], lista
ok("TEL-04 lista de câmeras: índices 0 a 4, livre ou ocupada, sem as que não abrem")


# ---------------------------------------------------------------- de ponta a ponta com um vídeo sintético
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    video = video_sintetico(Path(tmp), segundos=6.0)
    sessao, servidor = subir(pasta)
    try:
        status, resposta = agir(servidor, "iniciar", opcoes={"camera": str(video), "celular": False, "som": False,
                                                             "calibracao_rapida": True, "cardio": True})
        assert status == 200, resposta
        assert estado(servidor)["fase"] in ("abrindo", "calibrando", "rodando")
        rodando = esperar(lambda: estado(servidor)["fase"] in ("calibrando", "rodando"), 60)
        atual = estado(servidor)
        assert rodando, atual.get("mensagem")
        for chave in ("risco", "olhos", "cabeca", "boca", "cardio", "celular", "atencao", "desempenho", "eventos",
                      "series", "sessao", "calibracao"):
            assert chave in atual, chave
        assert esperar(lambda: estado(servidor)["desempenho"]["fps"] is not None, 10), "fps depois de alguns quadros"
        atual = estado(servidor)
        assert atual["risco"]["nivel"] in (0, 1, 2, 3) and atual["risco"]["nome"]
        assert "abertura" in atual["olhos"] and "perclos_60s" in atual["olhos"]
        assert "inclinacao" in atual["cabeca"] and "giro" in atual["cabeca"]
        assert "estado" in atual["cardio"] and atual["cardio"]["aviso"] == "estimativa pela câmera, não é medida médica"
        assert atual["desempenho"]["latencia_ms"] is not None
        assert atual["sessao"]["camera"] == "Vídeo sintetico.avi", atual["sessao"]
        ok("TEL-05 vídeo de teste: iniciar leva a calibrando/rodando e /estado traz risco, olhos, cabeça, cardio e desempenho")

        # TEL-12 · anúncio do script aberto (spec 018) enquanto roda
        anuncio = pasta / "em_execucao.json"
        assert anuncio.exists(), "em_execucao.json gravado ao iniciar"
        assert json.loads(anuncio.read_text(encoding="utf-8"))["camera"] == "Vídeo sintetico.avi"

        # TEL-06 · MJPEG com JPEG válido
        resposta_video, conexao = pedir(servidor, "/video.mjpg", ler=False)
        assert resposta_video.status == 200
        tipo = resposta_video.getheader("Content-Type")
        assert tipo.startswith("multipart/x-mixed-replace") and "boundary=" in tipo, tipo
        fronteira = tipo.split("boundary=", 1)[1].encode()
        lido = b""
        quadros = []
        fim = time.monotonic() + 10
        while len(quadros) < 2 and time.monotonic() < fim:
            lido += resposta_video.read1(65536)
            for parte in lido.split(b"--" + fronteira)[1:-1]:
                cabeca, _, corpo = parte.partition(b"\r\n\r\n")
                if b"image/jpeg" in cabeca and corpo.rstrip(b"\r\n"):
                    quadros.append(corpo.rstrip(b"\r\n"))
        conexao.close()
        assert len(quadros) >= 2, "pelo menos dois quadros no fluxo"
        imagem = cv2.imdecode(np.frombuffer(quadros[0], dtype=np.uint8), cv2.IMREAD_COLOR)
        assert imagem is not None and imagem.shape[1] >= 640, "JPEG válido, ampliado para a malha ficar nítida"
        ok("TEL-06 /video.mjpg entrega quadros JPEG válidos em multipart/x-mixed-replace")

        # TEL-07 · parar encerra a thread, libera a câmera e mostra o resumo
        status, _ = agir(servidor, "parar")
        assert status == 200
        assert esperar(lambda: estado(servidor)["fase"] == "resumo", 15), estado(servidor)["fase"]
        assert not sessao.rodando, "thread do monitor encerrada"
        assert sessao.ultima_camera is not None and sessao.ultima_camera.liberada, "câmera liberada"
        resumo_atual = estado(servidor)["resumo"]
        assert resumo_atual["duracao_s"] > 0 and resumo_atual["quadros"] > 0, resumo_atual
        assert resumo_atual["camera"] == "Vídeo sintetico.avi"
        ok("TEL-07 parar encerra a thread, libera a câmera e leva a fase a resumo com o resumo da sessão")
        assert not anuncio.exists(), "em_execucao.json apagado ao parar"
        ok("TEL-12 em_execucao.json gravado ao iniciar e apagado ao parar (spec 018)")

        # TEL-09 · salvar o resumo grava JSON e CSV só na pasta de dados
        antes_fora = sorted(p.name for p in Path(tmp).iterdir())
        status, resposta = agir(servidor, "salvar_resumo")
        assert status == 200, resposta
        json_salvo, csv_salvo = Path(resposta["json"]), Path(resposta["csv"])
        for arquivo in (json_salvo, csv_salvo):
            assert arquivo.exists() and arquivo.parent == pasta / "resumos", arquivo
        dados = json.loads(json_salvo.read_text(encoding="utf-8"))
        assert dados["formato"] == "rotaguard-resumo-teste/1" and dados["duracao_s"] > 0
        texto_csv = csv_salvo.read_text(encoding="utf-8-sig")
        assert texto_csv.splitlines()[0] == "medida;valor" and "duracao_s;" in texto_csv
        assert sorted(p.name for p in Path(tmp).iterdir()) == antes_fora, "nada criado fora da pasta de dados"
        ok("TEL-09 salvar o resumo grava JSON e CSV em pasta_dados/resumos e nada fora dela")

        # Novo teste volta para o início; apagar dados só com o teste parado e só na pasta do app
        status, _ = agir(servidor, "novo_teste")
        assert status == 200 and estado(servidor)["fase"] == "inicio"
    finally:
        descer(sessao, servidor)
    assert not sessao.rodando


# ---------------------------------------------------------------- TEL-13 · sem câmera: erro explicado, app aberto
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    sessao, servidor = subir(pasta)
    try:
        status, _ = agir(servidor, "iniciar", opcoes={"camera": "9", "celular": False, "cardio": False})
        assert status == 200
        assert esperar(lambda: estado(servidor)["fase"] == "erro", 40), estado(servidor)["fase"]
        atual = estado(servidor)
        texto = (atual["erro"]["titulo"] + " " + atual["erro"]["detalhe"]).lower()
        assert "câmera" in texto and ("ocupada" in texto or "não abriu" in texto or "nenhuma" in texto), atual["erro"]
        assert atual["erro"]["dicas"], "dicas do que conferir"
        assert not (pasta / "em_execucao.json").exists()
        status, _ = agir(servidor, "novo_teste")
        assert status == 200 and estado(servidor)["fase"] == "inicio", "o app continua aberto e aceita outro teste"
        ok("TEL-13 sem câmera: fase erro com a mensagem de câmera ausente ou ocupada, sem fechar o app")
    finally:
        descer(sessao, servidor)


# ---------------------------------------------------------------- TEL-08 · resumo: eventos por tipo e bpm só "pronto"
def estado_falso(t, eventos=(), cardio=None, nivel=0, perclos=None, abertura=0.8):
    return SimpleNamespace(
        metrics=SimpleNamespace(timestamp=t, face_found=True, landmarks=None, eye_points=None),
        drowsiness=SimpleNamespace(openness=abertura, perclos_60s=perclos, calibrating=False, fps=30.0,
                                   blinks_last_minute=0, closed_for=0.0),
        risk=SimpleNamespace(level=nivel, name=("normal", "atencao", "alto", "critico")[nivel], reasons=[]),
        events=[SimpleNamespace(alert_type=tipo, risk_level=3, duration=1.2, details={}) for tipo in eventos],
        cardio=cardio, phone=None, window={},
    )


def leitura(estado_cardio, bpm):
    return SimpleNamespace(estado=estado_cardio, bpm=bpm, confianca=0.8, snr_db=6.0, respiracao_rpm=None,
                           rmssd_ms=None, progresso=1.0, onda=[0.0], historico_bpm=[], canal="rgb", rois={},
                           ultimo_bpm=bpm)


resumo = resumo_mod.ResumoSessao(camera="Câmera 1")
sequencia = [
    (0.0, ["microssono"], leitura("medindo", 150.0), 0, None),
    (1.0, [], leitura("pronto", 70.0), 0, 0.02),
    (2.0, ["microssono", "celular_na_mao"], leitura("pronto", 80.0), 3, 0.04),
    (3.0, [], leitura("sinal_fraco", 40.0), 1, 0.06),
    (4.0, ["olhos_esfregados"], leitura("pronto", 75.0), 0, None),
    (5.0, [], leitura("movimento", 200.0), 0, None),
]
for t, eventos, cardio, nivel, perclos in sequencia:
    resumo.quadro(estado_falso(t, eventos, cardio, nivel, perclos), t)
resumo.finalizar(5.0)
dados = resumo.dados()
assert dados["eventos_por_tipo"] == {"microssono": 2, "celular_na_mao": 1, "olhos_esfregados": 1}, dados
assert dados["total_eventos"] == 4
cardio = dados["frequencia_cardiaca"]
assert cardio["leituras"] == 3 and cardio["media"] == 75.0 and cardio["minima"] == 70.0 and cardio["maxima"] == 80.0, cardio
assert cardio["observacao"] == "estimativa pela câmera, não é medida médica"
assert abs(dados["perclos_medio"] - 0.04) < 1e-9, dados["perclos_medio"]
assert dados["duracao_s"] == 5.0 and dados["quadros"] == 6
assert set(dados["tempo_por_nivel_s"]) == {"normal", "atencao", "alto", "critico"}
assert abs(sum(dados["tempo_por_nivel_s"].values()) - 5.0) < 1e-6
sem_pronto = resumo_mod.ResumoSessao()
sem_pronto.quadro(estado_falso(0.0, cardio=leitura("medindo", 90.0)), 0.0)
assert sem_pronto.dados()["frequencia_cardiaca"]["media"] is None
for numero in range(12):  # piscadas pelo ouvinte do DrowsinessMonitor, só as completas
    resumo.piscada(numero, SimpleNamespace(min_openness=0.1 if numero % 4 else 0.9, duration=0.2))
assert resumo.piscadas == 9
ok("TEL-08 resumo soma eventos por tipo e calcula média, mínimo e máximo do bpm só com leituras pronto")


# ---------------------------------------------------------------- TEL-10 / TEL-11 · desenho da malha
def rosto_sintetico(largura=640, altura=480, raio=110.0):
    gerador = np.random.default_rng(23)
    centro = np.array([largura / 2, altura / 2], dtype=np.float32)
    angulos = gerador.uniform(0, 2 * np.pi, 478)
    raios = raio * np.sqrt(gerador.uniform(0, 1, 478))
    pontos = centro + np.stack([np.cos(angulos) * raios * 0.8, np.sin(angulos) * raios], axis=1)
    return pontos.astype(np.float32)


def rosto_anatomico(cx=320.0, cy=250.0, largura=190.0, altura=230.0, semente=29):
    """478 pontos com a anatomia do Face Mesh nos lugares que a malha usa: contorno, sobrancelhas, olhos e íris, boca e
    as regiões do pulso (vision/cardio.py). O resto é aleatório dentro do rosto, inclusive perto dos olhos (pior caso)."""
    from vision.cardio import ROI_BOCHECHA_DIR, ROI_BOCHECHA_ESQ, ROI_TESTA
    dm = driver_monitor
    gerador = np.random.default_rng(semente)
    a, b = largura / 2, altura / 2
    angulos = gerador.uniform(0, 2 * np.pi, 478)
    raios = np.sqrt(gerador.uniform(0, 1, 478)) * 0.92
    pts = np.stack([cx + np.cos(angulos) * raios * a, cy + np.sin(angulos) * raios * b], axis=1)

    def anel(indices, ccx, ccy, ra, rb, fase=np.pi):
        for k, indice in enumerate(indices):
            angulo = fase + 2 * np.pi * k / len(indices)
            pts[indice] = (ccx + ra * np.cos(angulo), ccy + rb * np.sin(angulo))

    anel(dm.FACE_OVAL_PATH, cx, cy, a, b, -np.pi / 2)
    olho_dir, olho_esq = (cx - 0.21 * largura, cy - 0.1 * altura), (cx + 0.21 * largura, cy - 0.1 * altura)
    for caminho, (ex, ey) in zip(dm.BROW_PATHS, (olho_dir, olho_dir, olho_esq, olho_esq)):
        for k, indice in enumerate(caminho):
            pts[indice] = (ex - 0.11 * largura + k * 0.055 * largura, ey - 0.12 * altura)
    anel(ROI_TESTA, cx, cy - 0.34 * altura, 0.16 * largura, 0.06 * altura)
    anel(ROI_BOCHECHA_ESQ, cx - 0.24 * largura, cy + 0.08 * altura, 0.07 * largura, 0.06 * altura)
    anel(ROI_BOCHECHA_DIR, cx + 0.24 * largura, cy + 0.08 * altura, 0.07 * largura, 0.06 * altura)
    anel(dm.RIGHT_EYE_PATH, *olho_dir, 0.1 * largura, 0.04 * largura)
    anel(dm.LEFT_EYE_PATH, *olho_esq, 0.1 * largura, 0.04 * largura)
    for (anel_iris, centro), (ex, ey) in zip(dm.IRISES, (olho_dir, olho_esq)):
        pts[centro] = (ex, ey)
        anel(anel_iris, ex, ey, 0.033 * largura, 0.033 * largura, 0.0)
    anel(dm.LIPS_OUTER_PATH, cx, cy + 0.27 * altura, 0.17 * largura, 0.06 * altura)
    anel(dm.LIPS_INNER_PATH, cx, cy + 0.27 * altura, 0.12 * largura, 0.025 * altura)
    rois_rosto = {"testa": pts[list(ROI_TESTA)].tolist(), "bochecha_esq": pts[list(ROI_BOCHECHA_ESQ)].tolist(),
                  "bochecha_dir": pts[list(ROI_BOCHECHA_DIR)].tolist()}
    return pts.astype(np.float32), rois_rosto


def pele(altura=480, largura=640):
    """Fundo com cor e textura de pele (o desenho tem de aparecer e ser medido sobre ela, não sobre cinza liso)."""
    gerador = np.random.default_rng(7)
    y, x = np.mgrid[0:altura, 0:largura]
    imagem = np.empty((altura, largura, 3), dtype=np.float32)
    imagem[..., 0] = 110 + 20 * np.sin(x / 37.0)
    imagem[..., 1] = 140 + 18 * np.cos(y / 29.0)
    imagem[..., 2] = 185 + 15 * np.sin((x + y) / 53.0)
    imagem += gerador.normal(0, 4, imagem.shape)
    return np.clip(imagem, 0, 255).astype(np.uint8)


def mascara_poligono(poligono, forma) -> np.ndarray:
    mascara = np.zeros(forma[:2], dtype=np.uint8)
    cv2.fillPoly(mascara, [np.round(np.asarray(poligono) * 16).astype(np.int32)], 1, cv2.LINE_8, 4)
    return mascara.astype(bool)


def alterados(antes, depois) -> np.ndarray:
    return np.any(antes != depois, axis=2)


pontos, rois = rosto_anatomico()
cardio_pronto = SimpleNamespace(estado="pronto", bpm=72.0, onda=list(np.sin(np.linspace(0, 12, 180))), rois=rois)
maos = [np.array([(120 + 4 * i, 300 + 3 * (i % 5)) for i in range(21)], dtype=np.float32)]
estado_malha = SimpleNamespace(
    metrics=SimpleNamespace(face_found=True, landmarks=pontos, eye_points=pontos[[33, 160, 158, 133, 153, 144]],
                            timestamp=1.0),
    cardio=cardio_pronto,
    drowsiness=SimpleNamespace(openness=0.9),
    phone=SimpleNamespace(boxes=[(60, 60, 140, 200)], state="celular_na_mao"),
)
base = pele()
assert driver_monitor.MESH_MODES == ("discreta", "completa", "desligada"), driver_monitor.MESH_MODES
assert driver_monitor.MESH_LABELS == {"discreta": "Discreta", "completa": "Completa", "desligada": "Só o rosto"}
assert driver_monitor.WINDOW_MESH_MODE == "discreta"
assert driver_monitor.next_mesh_mode("discreta") == "completa" and driver_monitor.next_mesh_mode("desligada") == "discreta"
olhos_poligonos = [pontos[list(driver_monitor.RIGHT_EYE_PATH)], pontos[list(driver_monitor.LEFT_EYE_PATH)]]
x0, y0 = np.floor(pontos.min(axis=0)).astype(int)
x1, y1 = np.ceil(pontos.max(axis=0)).astype(int)
caixa_rosto = (slice(y0, y1 + 1), slice(x0, x1 + 1))
fracoes = {}
for modo in ("discreta", "completa"):
    for fechado, abertura in ((False, 0.9), (True, 0.05)):
        estado_malha.drowsiness.openness = abertura
        quadro = base.copy()
        driver_monitor.draw_face_mesh(quadro, estado_malha, modo, hands=maos)
        mudou = alterados(base, quadro)
        assert mudou.sum() > 150, (modo, "a malha aparece")
        # MAL-01 · nada dentro do olho, com o olho aberto ou fechado e com a mão perto
        for poligono in olhos_poligonos:
            dentro = mascara_poligono(poligono, base.shape)
            assert dentro.sum() > 100, "olho sintético com área"
            assert not mudou[dentro].any(), (modo, fechado, int(mudou[dentro].sum()))
        # MAL-02 · nenhum preenchimento: menos de 3% de cada região do pulso alterada
        for nome, poligono in rois.items():
            dentro = mascara_poligono(poligono, base.shape)
            fracao = mudou[dentro].mean()
            assert fracao < 0.03, (modo, nome, round(float(fracao), 4))
        if not fechado:
            quadro_sem_maos = base.copy()
            estado_sem_celular = SimpleNamespace(**{**vars(estado_malha), "phone": None})
            driver_monitor.draw_face_mesh(quadro_sem_maos, estado_sem_celular, modo)
            fracoes[modo] = alterados(base, quadro_sem_maos)[caixa_rosto].mean()
estado_malha.drowsiness.openness = 0.9
ok("MAL-01 nenhum pixel dentro dos olhos é alterado, nos dois modos, com o olho aberto ou fechado e com mãos e celular")
ok("MAL-02 sem preenchimento: menos de 3% de cada região do pulso alterada")
# MAL-03 · Discreta < 1,5% e Completa < 6% da caixa do rosto
assert fracoes["discreta"] < 0.015, fracoes
assert fracoes["completa"] < 0.06, fracoes
assert fracoes["completa"] > fracoes["discreta"], "a completa mostra mais que a discreta"
ok(f"MAL-03 caixa do rosto alterada: discreta {fracoes['discreta'] * 100:.2f}% (< 1,5%), completa "
   f"{fracoes['completa'] * 100:.2f}% (< 6%)")
# MAL-04 · "Só o rosto" não altera nenhum pixel
quadro = base.copy()
driver_monitor.draw_face_mesh(quadro, estado_malha, "desligada", hands=maos)
assert np.array_equal(quadro, base), "Só o rosto (desligada) não altera o quadro"
ok("MAL-04 'Só o rosto' não altera nenhum pixel, nem com mãos e celular na imagem")
for antigo in ("pontos", "essencial"):
    try:
        driver_monitor.draw_face_mesh(base.copy(), estado_malha, antigo)
    except ValueError:
        pass
    else:
        raise AssertionError(f"modo antigo {antigo} ainda desenha")
sem_pontos = SimpleNamespace(metrics=SimpleNamespace(face_found=True, landmarks=None,
                                                     eye_points=np.array([(300, 200), (340, 200)], dtype=np.float32)),
                             cardio=None, phone=None)
quadro = base.copy()
driver_monitor.draw_face_mesh(quadro, sem_pontos, "discreta")
mudou = alterados(base, quadro)
assert mudou.any(), "sem os 478 pontos (YuNet) ainda marca os olhos"
for cx_olho in (300, 340):
    assert not mudou[196:205, cx_olho - 4:cx_olho + 5].any(), "YuNet: marca ao lado do olho, nunca em cima do centro"
ok("TEL-10 malha: sem os 478 pontos (YuNet) marca os olhos por fora; modos antigos recusados")

# MAL-06 · custo como no timeit: 5 rodadas de 50 quadros, a melhor (a menos perturbada por outros programas)
quadro = base.copy()
for _ in range(20):
    driver_monitor.draw_face_mesh(quadro, estado_malha, "completa", hands=maos)
custos = {}
for modo in ("completa", "discreta"):
    rodadas = []
    for tentativa in range(3):  # a carga de outros programas vem em rajadas: até 3 vezes, com pausa entre elas
        for _ in range(5):
            inicio = time.perf_counter()
            for _ in range(50):
                driver_monitor.draw_face_mesh(quadro, estado_malha, modo, hands=maos)
            rodadas.append((time.perf_counter() - inicio) / 50 * 1000)
        if min(rodadas) < 3.0:
            break
        time.sleep(2)
    custos[modo] = (min(rodadas), max(rodadas))
    assert custos[modo][0] < 3.0, f"malha {modo} custou {custos[modo][0]:.2f} ms por quadro"
ok(f"MAL-06 desenho em 640×480: completa {custos['completa'][0]:.2f} ms, discreta {custos['discreta'][0]:.2f} ms "
   f"por quadro na melhor rodada (limite 3 ms)")


# ---------------------------------------------------------------- janela antiga do OpenCV continua desenhando (caixa)
from vision.drowsiness import Assessment  # noqa: E402
from vision.engine import DriverState  # noqa: E402
from vision.face import FaceMetrics  # noqa: E402
from vision.risk import RiskAssessment  # noqa: E402
from vision.visibility import Visibility  # noqa: E402

for pupila, qualidade in ((0.42, "ok"), (None, "camera_rgb")):
    metricas = FaceMetrics(timestamp=1.0, face_found=True, pupil_ratio=pupila, pupil_quality=qualidade,
                           eye_points=pontos[[33, 160, 158, 133, 153, 144]])
    metricas.landmarks = pontos
    estado_real = DriverState(metricas, Assessment(face_found=True, openness=0.8, fps=30.0, calibrating=True,
                                                   calibration_progress=0.4),
                              RiskAssessment(level=2, name="alto", reasons=["microssono"]), Visibility())
    for modo in driver_monitor.MESH_MODES:
        janela = driver_monitor.draw_overlay(base, estado_real, {"media_ms": 12.0, "p95_ms": 20.0, "max_ms": 30.0},
                                             mesh_mode=modo, hands=maos)
        assert janela.shape == base.shape and not np.array_equal(janela, base)
ok("TEL-10 janela antiga do OpenCV (--janela-opencv e caixa) desenha malha e textos em todos os modos, com e sem pupila")


# ---------------------------------------------------------------- resumo: total da sessão, não o máximo de 10 min
def estado_janela(t, bocejos, cabeceios, esfregados, mao):
    falso = estado_falso(t)
    falso.window = {"bocejos_10min": bocejos, "cabeceios_10min": cabeceios}
    falso.phone = SimpleNamespace(state="sem_celular", face_touch=SimpleNamespace(rubs_10min=esfregados,
                                                                                touches_10min=mao))
    return falso


total = resumo_mod.ResumoSessao()
# 3 bocejos em 10 min, um sai da janela, mais 2 chegam: 5 na sessão (o máximo da janela seria 4).
for t, (bocejos, cabeceios, esfregados, mao) in enumerate([(0, 0, 0, 0), (1, 1, 0, 1), (2, 1, 1, 1), (3, 2, 1, 1),
                                                          (2, 1, 1, 0), (3, 2, 2, 1), (4, 2, 2, 1)]):
    total.quadro(estado_janela(float(t), bocejos, cabeceios, esfregados, mao), float(t))
dados_total = total.dados()
assert (dados_total["bocejos"], dados_total["cabeceios"], dados_total["olhos_esfregados"],
        dados_total["mao_no_rosto"]) == (5, 3, 2, 2), dados_total
ok("TEL-08 resumo conta bocejos, cabeceios e gestos da sessão inteira, não o máximo da janela de 10 min")


# ---------------------------------------------------------------- spec 029 · resumo em formato de relatório (TEL-21 a 23)
TECNICOS = re.compile(r"\b(PERCLOS|EAR|KSS|AVR|RMSSD|SNR)\b")
SITUACOES = {"Normal", "Atenção", "Alto", "Crítico", "Acima do seu normal", "Bem acima do seu normal", "Medindo",
             "Em pausa", "Desligado", "Leitura boa", "Leitura fraca", "Sinal fraco", "Parado", "Sem rosto",
             "Fora do comum", "Experimental", "Aprendendo", "Indisponível", "Lento"}

assert dados["frase"] == "Teste de 5 s: 3 alertas de sono e 1 de celular.", dados["frase"]
calmo = resumo_mod.ResumoSessao()
for t in range(0, 721, 30):
    calmo.quadro(estado_falso(float(t), ["calibracao_concluida"] if t == 60 else [], perclos=0.02), float(t))
calmo.finalizar()
assert calmo.dados()["frase"] == "Nenhum alerta em 12 min.", calmo.dados()["frase"]
assert calmo.dados()["alertas"] == [], "aviso do sistema (calibração) não é alerta"
um = resumo_mod.ResumoSessao()
um.quadro(estado_falso(0.0), 0.0)
um.quadro(estado_falso(65.0, ["olhando_celular"]), 65.0)
um.finalizar()
assert um.dados()["frase"] == "Teste de 1 min 05 s: 1 alerta de celular.", um.dados()["frase"]
ok("TEL-21 o resumo começa com uma frase que conta os alertas por tipo e a duração do teste")

com_video = resumo_mod.ResumoSessao()
com_video.quadro(estado_falso(0.0), 0.0)
evento_com_trecho = estado_falso(12.0, ["microssono"])
evento_com_trecho.events[0].details = {"trecho_uid": "ab" * 16, "fechado_s": 1.2}
com_video.quadro(evento_com_trecho, 12.0)
com_video.quadro(estado_falso(20.0, ["calibracao_concluida", "celular_no_ouvido"]), 20.0)
com_video.finalizar()
relatorio = com_video.dados()
alertas = relatorio["alertas"]
assert [a["tipo"] for a in alertas] == ["microssono", "celular_no_ouvido"], alertas
for alerta in alertas:
    assert re.fullmatch(r"\d\d:\d\d:\d\d", alerta["hora"]) and alerta["duracao_s"] == 1.2 and alerta["situacao"], alerta
assert alertas[0]["trecho_uid"] == "ab" * 16 and alertas[1]["trecho_uid"] is None
script_resumo = (PASTA_WEB / "app.js").read_text(encoding="utf-8")
assert "Ver vídeo" in script_resumo and "trecho_uid" in script_resumo
linhas = {linha["id"]: linha for linha in relatorio["como_estava"]}
assert {"olho_fechado", "piscadas", "bocejos", "cabeceios", "celular", "pulso"} <= set(linhas), list(linhas)
for linha in relatorio["como_estava"]:
    assert linha["nome"] and not TECNICOS.search(linha["nome"]), linha
    assert linha["o_que_e"].endswith(".") and linha["faixa_normal"] and linha["situacao"] in SITUACOES, linha
ok("TEL-22 resumo com a lista de alertas (hora, duração, vídeo quando houver) e a tabela 'Como a pessoa estava' com "
   "explicação e faixa normal")

indice_web = (PASTA_WEB / "index.html").read_text(encoding="utf-8")
detalhes_resumo = re.search(r"<details[^>]*id=\"r-detalhes\"[^>]*>", indice_web)
assert detalhes_resumo and " open" not in detalhes_resumo.group(0), "detalhes técnicos recolhidos por padrão"
assert re.search(r'id="r-detalhes"[^>]*>\s*<summary[^>]*>(?:<[^>]+>)*Detalhes técnicos', indice_web)
assert re.search(r"<details[^>]*id=\"detalhes\"[^>]*>", indice_web) and not re.search(
    r"<details[^>]*id=\"detalhes\"[^>]*\sopen", indice_web), "na tela do teste, Detalhes também começa recolhido"
ok("TEL-23 detalhes técnicos do resumo (e da tela do teste) começam recolhidos")


# ---------------------------------------------------------------- vídeo: JPEG 4:4:4 (o 4:2:0 apaga o lima da malha)
def amostragem_jpeg(dados: bytes) -> list:
    inicio = dados.index(b"\xff\xc0")
    componentes = dados[inicio + 9]
    return [dados[inicio + 10 + 3 * i + 1] for i in range(componentes)]


from tela_teste.sessao import desenhar_jpeg  # noqa: E402

jpeg, _ = desenhar_jpeg(base, estado_malha, maos, "completa")
assert amostragem_jpeg(jpeg) == [0x11, 0x11, 0x11], [hex(v) for v in amostragem_jpeg(jpeg)]
ok("TEL-06 quadro do vídeo em JPEG 4:4:4: o lima fino da malha não perde a cor")

# MAL-05 · o gravador de trechos recebe o quadro LIMPO (sem malha); a tela recebe o quadro com a malha
from tela_teste.sessao import Renderizador  # noqa: E402

liso = cv2.GaussianBlur(base, (0, 0), 3)  # imagem lisa: a diferença do JPEG fica pequena e a malha, se houvesse, não
entregues = []
renderizador = Renderizador(lambda: "completa")
renderizador.ouvinte = lambda t, jpeg_limpo: entregues.append((t, jpeg_limpo))
try:
    for numero in range(4):
        estado_quadro = SimpleNamespace(**{**vars(estado_malha), "metrics": SimpleNamespace(
            **{**vars(estado_malha.metrics), "timestamp": 10.0 + numero * 0.2})})
        renderizador.entregar(liso, estado_quadro, maos)
        assert esperar(lambda: len(entregues) > numero, 5), "o gravador recebe um quadro por entrega (até 15 por s)"
finally:
    renderizador.parar()
limpo = cv2.imdecode(np.frombuffer(entregues[0][1], np.uint8), cv2.IMREAD_COLOR)
assert limpo.shape == liso.shape, (limpo.shape, liso.shape)
diferenca_limpo = np.abs(limpo.astype(int) - liso.astype(int))[caixa_rosto].mean()
tela = cv2.imdecode(np.frombuffer(renderizador.jpeg, np.uint8), cv2.IMREAD_COLOR)
tela = cv2.resize(tela, (liso.shape[1], liso.shape[0]), interpolation=cv2.INTER_AREA)
diferenca_tela = np.abs(tela.astype(int) - liso.astype(int))[caixa_rosto].mean()
assert diferenca_limpo < 1.5, f"o quadro do trecho tem de ser o original (diferença média {diferenca_limpo:.2f})"
assert diferenca_tela > diferenca_limpo + 0.3, (diferenca_tela, diferenca_limpo)
assert [t for t, _ in entregues] == [10.0, 10.2, 10.4, 10.6]
ok(f"MAL-05 o gravador de trechos recebe o quadro sem malha (diferença média {diferenca_limpo:.2f} só do JPEG) e a "
   f"tela, o quadro com a malha ({diferenca_tela:.2f})")


# ---------------------------------------------------------------- /estado: o que o script mede e a tela mostrava menos
toque = SimpleNamespace(gesture=None, rubs_10min=1, touches_10min=0, eye_covered=True, face_hidden=False)
estado_completo = SimpleNamespace(
    metrics=SimpleNamespace(timestamp=5.0, face_found=True, pitch=4.0, yaw=-8.0, roll=1.0, jaw_open=0.1,
                            gaze_x=0.1, gaze_y=0.0, infrared=False, pupil_ratio=None, pupil_quality="camera_rgb"),
    drowsiness=Assessment(face_found=True, openness=None, frame_source="rosto_virado", fps=29.0, perclos_60s=0.05),
    risk=RiskAssessment(level=1, name="atencao", reasons=["fechamento_longo"]),
    visibility=Visibility(eyes_ok=False, reason="oculos_escuros", hidden_for=4.2),
    window={"perclos_3min": 0.07, "duracao_mediana_ms": 236, "duracao_base_ms": 200, "razao_duracao": 1.18,
            "perclos_base": 0.03, "avr_fechamento_ms": 41.0, "avr_fechamento_base_ms": 35.0,
            "razao_avr_fechamento": 1.17, "fechamentos_longos_5min": 1},
    context={"madrugada": True, "direcao_continua_h": 1.5, "limite_direcao_excedido": False},
    activation=SimpleNamespace(state="sinais_leves", index=0.4, confidence=0.6, confidence_label="média"),
    phone=SimpleNamespace(state="sem_celular", duration=0.0, phone_score=None, hands=1, face_touch=toque),
    cardio=None,
)
calibrador = SimpleNamespace(valid_seconds=38.0, min_seconds=60.0, max_seconds=120.0, live_blinks=7, target_blinks=15)
medido = estado_mod.medidas(estado_completo, None, None, calibrador=calibrador, baixa_em_s=42.4)
olhos = medido["olhos"]
assert olhos["perclos_3min"] == 0.07 and olhos["medida"] == "rosto_virado" and olhos["mao_no_olho"] is True
assert olhos["pausa"] == "Mão no olho: medidas do olho em pausa", olhos["pausa"]
toque.eye_covered = False
assert estado_mod.medidas(estado_completo)["olhos"]["pausa"] == "Olhos não visíveis (óculos escuros?): abertura em pausa"
estado_completo.visibility = Visibility()
assert estado_mod.medidas(estado_completo)["olhos"]["pausa"] == "Rosto virado: abertura em pausa"
assert olhos["comparacao"]["razao_duracao"] == 1.18 and olhos["comparacao"]["perclos_base"] == 0.03
assert medido["rosto"]["olhos_ocultos_s"] == 4.2
assert {chave: medido["contexto"][chave] for chave in ("madrugada", "direcao_continua_h", "limite_direcao_excedido")} ==     {"madrugada": True, "direcao_continua_h": 1.5, "limite_direcao_excedido": False}
assert medido["risco"]["baixa_em_s"] == 42
assert medido["calibracao"]["segundos"] == 38.0 and medido["calibracao"]["minimo_s"] == 60.0
assert medido["calibracao"]["piscadas"] == 7 and medido["calibracao"]["piscadas_alvo"] == 15
avancado = medido["avancado"]
assert avancado["aviso"] == "sinais compatíveis, não é diagnóstico"
assert avancado["ativacao"]["estado"] == "sinais_leves" and avancado["pupila"]["razao"] is None
assert "Câmera comum" in avancado["pupila"]["qualidade"]
assert medido["rosto"]["pontos_disponiveis"] is True
yunet = estado_mod.medidas(estado_completo, pontos_rosto=False)
assert yunet["rosto"]["pontos_disponiveis"] is False
script_web = (PASTA_WEB / "app.js").read_text(encoding="utf-8")
assert "Malha indisponível neste modo de câmera" in script_web
coracao_yunet = next(c for c in yunet["painel"]["cartoes"] if c["id"] == "coracao")
assert "Pulso indisponível neste modo de câmera" in coracao_yunet["principal"]["espera"], coracao_yunet["principal"]
ok("TEL-05 /estado traz PERCLOS de 3 min, comparação com a calibração, motivo da pausa, mão no olho, contexto, "
   "tempo até o risco baixar, calibração em detalhe e sinais avançados")


# ---------------------------------------------------------------- estado: serialização e textos
reading = SimpleNamespace(estado="pronto", bpm=71.6, confianca=0.82, snr_db=7.3, respiracao_rpm=14.2, rmssd_ms=None,
                          progresso=1.0, onda=[0.1, -0.2], historico_bpm=[70.0, 71.6], canal="rgb", rois=rois,
                          ultimo_bpm=71.6)
texto = json.dumps(estado_mod.cardio_json(reading))
assert '"bpm": 72' in texto and '"estado": "pronto"' in texto and "rois" not in texto, texto
assert estado_mod.cardio_json(None)["estado"] == "desligado"
assert estado_mod.rotulo_evento("microssono").startswith("Microssono") and estado_mod.rotulo_evento("x_y") == "X y"
assert estado_mod.texto_motivo("olhos_no_celular") == "Olhos no celular"
ok("TEL-05 estado do cardio sem os polígonos e com bpm arredondado; rótulos de evento e motivo em português")


# ---------------------------------------------------------------- spec 029 · tela do teste por pergunta (TEL-17 a 20)
def estado_tela(abertura=0.92, fechado=0.0, janela=None, celular="sem_celular", celular_s=0.0, rosto=True,
                calibrando=False, nivel=0, motivos=(), risco_sono=0, risco_distracao=0, cardio=None, distracao=None,
                fps=30.0):
    risco = RiskAssessment(level=nivel, name=("normal", "atencao", "alto", "critico")[nivel], reasons=list(motivos))
    risco.risco_sono, risco.risco_distracao = risco_sono, risco_distracao
    return SimpleNamespace(
        metrics=SimpleNamespace(timestamp=50.0, face_found=rosto, pitch=4.0, yaw=-3.0, roll=1.0, jaw_open=0.1,
                                gaze_x=0.02, gaze_y=0.01, infrared=False, pupil_ratio=None, pupil_quality="camera_rgb"),
        drowsiness=Assessment(face_found=rosto, openness=abertura if rosto else None, closed_for=fechado, fps=fps,
                              calibrating=calibrando, calibration_progress=0.4 if calibrando else 1.0,
                              perclos_60s=0.02, blinks_last_minute=12),
        risk=risco, visibility=Visibility(), window=dict(janela or {}),
        context={}, activation=None,
        phone=SimpleNamespace(state=celular, duration=celular_s, phone_score=0.8 if celular != "sem_celular" else None,
                              hands=1, face_touch=SimpleNamespace(gesture=None, rubs_10min=0, touches_10min=0,
                                                                  eye_covered=False, face_hidden=False)),
        cardio=cardio, distraction=distracao,
    )


def todas_as_medidas(painel):
    for cartao in painel["cartoes"]:
        yield cartao["id"], cartao["principal"]
        for medida in cartao["medidas"]:
            yield cartao["id"], medida
    for grupo in painel["detalhes"]:
        for medida in grupo["medidas"]:
            yield grupo["id"], medida


JANELA_CALIBRADA = {"perclos_3min": 0.021, "perclos_base": 0.015, "duracao_mediana_ms": 236, "duracao_base_ms": 200,
                    "razao_duracao": 1.18, "piscadas_por_min": 14.2, "piscadas_5min": 40, "bocejos_10min": 0,
                    "cabeceios_10min": 0, "fechamentos_longos_5min": 0}
pulso = SimpleNamespace(estado="pronto", bpm=71.6, confianca=0.82, snr_db=7.3, respiracao_rpm=14.2, rmssd_ms=None,
                        progresso=1.0, onda=[0.1, -0.2], historico_bpm=[70.0, 71.6], canal="rgb", rois=rois,
                        ultimo_bpm=71.6)
painel = estado_mod.medidas(estado_tela(janela=JANELA_CALIBRADA, cardio=pulso), {"media_ms": 12.0, "p95_ms": 20.0},
                            1.1)["painel"]
assert [c["id"] for c in painel["cartoes"]] == ["sono", "atencao", "coracao"], [c["id"] for c in painel["cartoes"]]
assert [c["titulo"] for c in painel["cartoes"]] == ["Sono", "Atenção na estrada", "Coração (estimativa)"]
vistas = list(todas_as_medidas(painel))
assert len(vistas) >= 20, "nada do que a tela mostrava some: o que não é essencial vai para Detalhes"
for grupo, medida in vistas:
    assert medida["nome"] and not TECNICOS.search(medida["nome"]), (grupo, medida["nome"])
    assert medida["situacao"] in SITUACOES, (grupo, medida["nome"], medida["situacao"])
    assert medida["o_que_e"].endswith(".") and len(medida["o_que_e"]) >= 20, (grupo, medida["nome"], medida["o_que_e"])
    if medida["valor"] is None:
        assert medida["espera"] and "--" not in medida["espera"], (grupo, medida["nome"], medida)
    else:
        assert "--" not in medida["valor"], (grupo, medida["nome"], medida["valor"])
        assert medida["unidade"] or re.search(r"[A-Za-zÀ-ú]", medida["valor"]), (grupo, medida["nome"], medida)
script_web = (PASTA_WEB / "app.js").read_text(encoding="utf-8")
assert "o_que_e" in script_web and ".title = medida.o_que_e" not in script_web, "a frase de 'o que é' fica visível"
ok("TEL-17 toda medida tem nome simples, valor com unidade (ou o que falta medir), situação e a frase de 'o que é'")

for cartao in painel["cartoes"]:
    assert cartao["pergunta"].endswith("?") and cartao["situacao"] and cartao["resumo"].endswith("."), cartao
    assert not TECNICOS.search(cartao["titulo"] + cartao["pergunta"]), cartao["titulo"]
for grupo in painel["detalhes"]:
    assert not TECNICOS.search(grupo["titulo"]), grupo["titulo"]
tecnicos = {m["tecnico"] for _, m in vistas if m.get("tecnico")}
assert {"PERCLOS de 3 min", "Escala de Karolinska (KSS)"} <= tecnicos, tecnicos
indice_web = (PASTA_WEB / "index.html").read_text(encoding="utf-8")
for etiqueta in re.findall(r"<(?:h1|h2|h3|summary)[^>]*>(.*?)</(?:h1|h2|h3|summary)>", indice_web, re.S):
    assert not TECNICOS.search(re.sub(r"<[^>]+>", "", etiqueta)), etiqueta
ok("TEL-19 PERCLOS, EAR e KSS nunca são título: ficam só como nota técnica pequena da medida")

sono = painel["cartoes"][0]
por_id = {m["id"]: m for _, m in vistas}
assert por_id["olho_fechado_3min"]["seu_normal"] == "seu normal: 1,5%", por_id["olho_fechado_3min"]
assert por_id["olho_fechado_3min"]["valor"] == "2,1" and por_id["olho_fechado_3min"]["situacao"] == "Normal"
assert por_id["duracao_piscada"]["seu_normal"] == "seu normal: 200 ms", por_id["duracao_piscada"]
assert por_id["duracao_piscada"]["situacao"] == "Acima do seu normal" and por_id["duracao_piscada"]["nivel"] == 1
sem_calibracao = estado_mod.medidas(estado_tela(janela={"perclos_3min": 0.02, "piscadas_5min": 6}, fps=30.0))["painel"]
sem_base = {m["id"]: m for _, m in todas_as_medidas(sem_calibracao)}
assert sem_base["olho_fechado_3min"]["seu_normal"] is None
assert sem_base["duracao_piscada"]["valor"] is None and "faltam 9 piscadas" in sem_base["duracao_piscada"]["espera"]
lento = {m["id"]: m for _, m in todas_as_medidas(estado_mod.medidas(estado_tela(janela={}, fps=18.0))["painel"])}
assert "24" in lento["duracao_piscada"]["espera"] and "18" in lento["duracao_piscada"]["espera"]
ok("TEL-20 medidas comparadas com a calibração dizem 'seu normal: X'; sem medida, a tela diz o que falta")

casos = [
    (estado_tela(), "Tudo normal", 0),
    (estado_tela(abertura=0.05, fechado=1.43, nivel=3, risco_sono=3, motivos=["microssono"]), "Olhos fechados há 1,4 s", 3),
    (estado_tela(celular="celular_na_mao", celular_s=4.2, nivel=2, risco_distracao=2), "Celular na mão há 4 s", 2),
    (estado_tela(rosto=False), "Procurando o rosto", 0),
    (estado_tela(calibrando=True), "Aprendendo o seu normal", 0),
    (estado_tela(nivel=1, risco_sono=1, motivos=["piscadas_mais_longas"]), "Sinais leves de sono", 1),
]
for estado_caso, frase, nivel_caso in casos:
    agora = estado_mod.medidas(estado_caso)["painel"]["agora"]
    assert agora["frase"] == frase, (agora, frase)
    assert agora["nivel"] == nivel_caso and agora["situacao"] in SITUACOES and agora["detalhe"].endswith("."), agora
    assert re.search(r"[A-Za-zÀ-ú]{3}", agora["frase"]), "frase, nunca só um número"
assert "Piscadas mais longas" in estado_mod.medidas(casos[-1][0])["painel"]["agora"]["detalhe"]
assert 'id="agora-frase"' in indice_web and "chip-risco" not in indice_web and "risk-scale" not in indice_web
ok("TEL-18 o topo mostra uma frase do estado atual (normal, olho fechado, celular, sem rosto, calibrando, sinais leves) "
   "e o risco aparece num lugar só")


# ---------------------------------------------------------------- 20/10 · painel ao lado do vídeo enxuto (PAI-01 a PAI-03)
# Pedido do Matheus: "o menu lateral que aparece do lado da câmera não está legal, tudo está muito junto e confuso".
cartoes = {c["id"]: c for c in painel["cartoes"]}
assert [m["id"] for m in [cartoes["sono"]["principal"], *cartoes["sono"]["medidas"]]] == ["olho_aberto",
                                                                                       "olho_fechado_3min"]
assert [m["id"] for m in [cartoes["atencao"]["principal"], *cartoes["atencao"]["medidas"]]] == [
    "para_onde_olha", "celular", "olhos_esfregados"]
assert [m["id"] for m in [cartoes["coracao"]["principal"], *cartoes["coracao"]["medidas"]]] == ["pulso", "confianca"]
grupos = {g["id"]: [m["id"] for m in g["medidas"]] for g in painel["detalhes"]}
assert list(grupos)[0] == "sono" and {"duracao_piscada", "piscadas_min", "bocejos", "cabeceios",
                                      "fechamentos_longos"} <= set(grupos["sono"]), grupos
assert "tempo_fora" in grupos["olhar"], grupos
for cartao in painel["cartoes"]:
    for medida in [cartao["principal"], *cartao["medidas"]]:
        assert len(medida["nome"]) <= 32, medida["nome"]
        if medida["valor"] is None:
            assert medida["espera_curta"] and len(medida["espera_curta"]) <= 40, medida
sem_perclos = estado_mod.medidas(estado_tela(janela={}))["painel"]
espera_curta = {m["id"]: m for _, m in todas_as_medidas(sem_perclos)}["olho_fechado_3min"]["espera_curta"]
assert espera_curta == "Pronto em 1 min e meio", espera_curta
ok("PAI-01 blocos de cima enxutos: Sono com 2 números, Atenção com 3 linhas, Coração com pulso e confiança; o resto em "
   "Ver mais detalhes, com nomes curtos e o que falta medir em poucas palavras")

assert 'id="detalhes"' in indice_web and "Ver mais detalhes" in indice_web
pos_agora, pos_cartoes = indice_web.index('id="agora"'), indice_web.index('id="cartoes"')
assert indice_web.index('id="leituras"') < pos_agora < pos_cartoes < indice_web.index('id="detalhes"'), \
    "a frase do agora é o topo do painel ao lado do vídeo, antes dos blocos e dos detalhes"
assert "O que os números de cima querem dizer" in script_web and "espera_curta" in script_web
assert "status-word" in script_web and "medida.nivel === 0" in script_web, "linha normal sem palavra colorida (ISA-101)"
ok("PAI-02 painel ao lado do vídeo: frase do agora no topo, depois os 3 blocos e Ver mais detalhes recolhido, que "
   "começa explicando cada número de cima")


def coracao_de(**campos):
    leitura = SimpleNamespace(estado="medindo", bpm=None, confianca=0.0, snr_db=None, respiracao_rpm=None,
                              rmssd_ms=None, progresso=0.0, onda=[], historico_bpm=[], canal="rgb", rois=rois,
                              ultimo_bpm=None)
    for chave, valor in campos.items():
        setattr(leitura, chave, valor)
    cartao = next(c for c in estado_mod.medidas(estado_tela(cardio=leitura))["painel"]["cartoes"] if c["id"] == "coracao")
    return cartao, json.dumps(cartao, ensure_ascii=False)


# Aquecimento: anel com o progresso e "faltam ~N s"; sem o campo novo, o tempo sai do progresso (15 s de sinal bom).
cartao, texto_cartao = coracao_de(estado="medindo", progresso=0.4)
medicao = cartao["medicao"]
assert medicao["ativa"] and medicao["progresso"] == 0.4 and medicao["faltam_s"] == 9, medicao
assert medicao["texto"] == "Medindo seu pulso, faltam ~9 s" and medicao["motivo"] is None, medicao
assert "luz" not in texto_cartao.lower(), "sem motivo do cardio, nada de falar de luz"
cartao, _ = coracao_de(estado="medindo", progresso=0.4, segundos_para_medida=4.2)
assert cartao["medicao"]["texto"] == "Medindo seu pulso, faltam ~5 s", cartao["medicao"]
# Perdeu o sinal: medindo de novo, último valor bom esmaecido e o motivo só quando o cardio diz.
cartao, texto_cartao = coracao_de(estado="movimento", ultimo_bpm=72.4, progresso=1.0)
medicao = cartao["medicao"]
assert medicao["ativa"] and medicao["ultimo"] == "72" and medicao["texto"] == "Medindo de novo", medicao
assert medicao["motivo"] == "Fique parado por alguns segundos" and "luz" not in texto_cartao.lower(), medicao
assert cartao["principal"]["valor"] == "72" and "último valor" in cartao["principal"]["unidade"], cartao["principal"]
cartao, texto_cartao = coracao_de(estado="sinal_fraco", ultimo_bpm=70.0, segundos_para_medida=6.0, progresso=0.5)
assert cartao["medicao"]["texto"] == "Medindo de novo, faltam ~6 s" and cartao["medicao"]["progresso"] == 0.5
assert cartao["medicao"]["motivo"] is None and "luz" not in texto_cartao.lower(), cartao["medicao"]
for motivo, esperado in (("mexendo", "Fique parado por alguns segundos"), ("pouca_luz", "Pouca luz no rosto"),
                         ("luz_estourada", "Luz forte demais no rosto")):
    cartao, _ = coracao_de(estado="sinal_fraco", motivo=motivo, ultimo_bpm=70.0)
    assert cartao["medicao"]["motivo"] == esperado, (motivo, cartao["medicao"])
cartao, _ = coracao_de(estado="medindo", progresso=0.2, motivo="camera_lenta", fps=12.0)
assert cartao["medicao"]["motivo"] == "Câmera lenta (12 quadros/s)", cartao["medicao"]
cartao, _ = coracao_de(estado="pronto", bpm=71.6, confianca=0.82, progresso=1.0, ultimo_bpm=71.6)
assert not cartao["medicao"]["ativa"] and cartao["principal"]["valor"] == "72", cartao
assert estado_mod.cardio_json(SimpleNamespace(estado="medindo"))["motivo"] is None, "sem os campos novos, None"
assert "heart-progress" in script_web and "último valor" in script_web and "girando" in script_web
ok("PAI-03 coração com andamento: anel e 'faltam ~N s' no aquecimento e ao medir de novo, último valor esmaecido, "
   "motivo só quando o cardio diz (luz nunca sem ele)")


# ---------------------------------------------------------------- spec 031 · nome visível e linha da versão (NOM-01)
from tela_teste import app as tela_app  # noqa: E402
from tela_teste import sessao as sessao_mod  # noqa: E402

assert tela_app.NOME_APP == "RotaGuard Script"
visiveis = [PASTA_WEB / "index.html", PASTA_WEB / "app.js", RAIZ / "caixa" / "textos_legais.py",
            RAIZ / "caixa" / "tela_teste" / "central.py", RAIZ / "caixa" / "tela_teste" / "sessao.py"]
for arquivo in visiveis:
    assert "RotaGuard Teste" not in arquivo.read_text(encoding="utf-8"), arquivo.name
assert "<title>RotaGuard Script</title>" in indice_web
ok("NOM-01 tela, textos legais e envio para a empresa dizem RotaGuard Script; 'RotaGuard Teste' não aparece mais")

assert sessao_mod.linha_de_versao(congelado=False) == "versão de desenvolvimento"
with tempfile.TemporaryDirectory() as pasta_exe:
    exe = Path(pasta_exe) / "RotaGuardScript.exe"
    exe.write_bytes(b"")
    from vision import __version__ as versao_atual  # noqa: E402
    assert sessao_mod.linha_de_versao(congelado=True, executavel=str(exe)) == f"RotaGuard Script {versao_atual}", \
        "sem versao.txt ao lado do executável: o nome e a versão, sem quebrar"
    (Path(pasta_exe) / "versao.txt").write_text("RotaGuard Script 0.3.0 · compilação e94ca11 · 20/10/2026 13:10\n",
                                                encoding="utf-8")
    assert sessao_mod.linha_de_versao(congelado=True, executavel=str(exe)) == \
        "RotaGuard Script 0.3.0 · compilação e94ca11 · 20/10/2026 13:10"
    (Path(pasta_exe) / "versao.txt").write_bytes(b"")
    assert sessao_mod.linha_de_versao(congelado=True, executavel=str(exe)).startswith("RotaGuard Script")
assert 'id="compilacao-inicio"' in indice_web and 'id="compilacao-legal"' in indice_web
assert "dados.compilacao" in script_web and "textosLegais.compilacao" in script_web
ok("VER-01 linha da versão: lê versao.txt ao lado do executável no pacote, 'versão de desenvolvimento' fora dele, e "
   "aparece no rodapé do início e na janela de privacidade")


# ---------------------------------------------------------------- privacidade do cardio e dos resumos (spec 022 e 023)
import textos_legais  # noqa: E402

secoes_legais = dict(textos_legais.secoes(Path("/dados/RotaGuard/Teste"), ""))
privacidade = secoes_legais["Privacidade"]
for esperado in ("frequência cardíaca", "estimada pela câmera", "só neste computador", "não é medição médica",
                 "nem diagnóstico", "desligada nas opções", "art. 11", "resumos", "salvar resumo", "127.0.0.1"):
    assert esperado in privacidade.lower(), esperado
assert "não é gravada nem enviada" in privacidade, "o pulso não é gravado nem enviado (fora do resumo salvo)"
tudo_legal = "\n".join(secoes_legais.values())
assert "conforme a LGPD" not in tudo_legal, "sem parecer jurídico não se escreve 'conforme a LGPD'"
assert "não é medida médica" in secoes_legais["Termos de uso"]
assert "pywebview" in secoes_legais["Licenças"] and "Tkinter" not in secoes_legais["Licenças"]
# Spec 026: o que vai para a empresa quando o computador é conectado com um código
for esperado in ("conectar à empresa", "trechos de vídeo", "16 s", "a frequência cardíaca nunca", "desconectar",
                 "central.json", "trechos", "enviar para a empresa"):
    assert esperado in privacidade.lower(), esperado
assert "a empresa passa a ser a controladora" in secoes_legais["LGPD"].lower()
assert textos_legais.VERSAO_TEXTOS == "19/10/2026"
ok("TEL-04 privacidade cita o pulso estimado só aqui, não gravado nem enviado, sem ser medição médica, e os resumos")


# ---------------------------------------------------------------- TEL-14 · web/ funciona offline
arquivos_web = sorted(PASTA_WEB.iterdir())
assert {p.name for p in arquivos_web} >= {"index.html", "app.css", "app.js"}, arquivos_web
for arquivo in arquivos_web:
    conteudo = arquivo.read_text(encoding="utf-8")
    externo = re.findall(r"https?://[^\s\"')]+", conteudo)
    assert not externo, (arquivo.name, externo[:3])
    assert "—" not in conteudo, f"{arquivo.name}: travessão em texto de interface"
    assert "fonts.googleapis" not in conteudo and "@import" not in conteudo
indice = (PASTA_WEB / "index.html").read_text(encoding="utf-8")
assert "não é medida médica" in indice and 'lang="pt-BR"' in indice
estilo = (PASTA_WEB / "app.css").read_text(encoding="utf-8").lower()
assert "prefers-reduced-motion" in estilo
# Cores de risco medidas (contraste AA e daltonismo, pesquisa de 19/10): normal sem cor; lima nunca é estado.
for cor in ("#f0cc5c", "#f08c4a", "#ff6b81", "#946a00", "#9c3d0c", "#b0204f"):
    assert cor in estilo, cor
assert "sinais compatíveis, não é diagnóstico" in indice
ok("TEL-14 web/ sem nenhum endereço http(s):// externo, sem travessão e com o aviso do cardio")


# ---------------------------------------------------------------- TEL-15 · app_teste: tela nova e argumentos antigos
assert inspect.signature(app_teste.main).parameters["tela"].default is app_teste.abrir_tela_teste
chamadas = []
assert app_teste.main([], rodar=lambda a: chamadas.append(("monitor", a)) or 0,
                      tela=lambda: chamadas.append(("tela",)) or 0) == 0
assert app_teste.main(["--monitor", "--camera", "2"], rodar=lambda a: chamadas.append(("monitor", a)) or 0) == 0
assert app_teste.main(["--janela-opencv"], rodar=lambda a: chamadas.append(("opencv", a)) or 0) == 0
assert chamadas[0] == ("tela",) and chamadas[1] == ("monitor", ["--camera", "2"]), chamadas
nome, argumentos = chamadas[2]
assert nome == "opencv" and "--window" in argumentos and "--sem-servidor" in argumentos and "--cardio" in argumentos
assert run_monitor.parse_args(["--janela-opencv"]).window is True
assert run_monitor.parse_args([]).cardio is False, "cardio desligado na caixa"
assert run_monitor.parse_args(["--cardio"]).cardio is True and run_monitor.parse_args(["--sem-cardio"]).cardio is False
tela_args = app_teste.argumentos_monitor(app_teste.OpcoesTeste(), Path("/tmp/rg"), janela=False)
assert "--no-window" in tela_args and "--window" not in tela_args and "--cardio" in tela_args
assert "--sem-cardio" in app_teste.argumentos_monitor(app_teste.OpcoesTeste(cardio=False), Path("/tmp/rg"))
ok("TEL-15 sem argumentos abre a tela nova; --monitor, --janela-opencv e os argumentos antigos continuam valendo")


# ---------------------------------------------------------------- TEL-16 · pacote leva web/ e o build confere a tela
especificacao = (RAIZ / "implantacao" / "app-teste" / "rotaguard-script.spec").read_text(encoding="utf-8")
assert '"tela_teste" / "web"' in especificacao and '"tela_teste/web"' in especificacao
assert "webview" in especificacao and "pywebview" in especificacao
especificacao_build = importlib.util.spec_from_file_location("build_app_teste", RAIZ / "implantacao" / "app-teste" / "build.py")
build_app = importlib.util.module_from_spec(especificacao_build)
especificacao_build.loader.exec_module(build_app)
assert callable(build_app.teste_da_tela)
fonte_build = inspect.getsource(build_app)
assert "--verificar-tela" in fonte_build and "tela_teste" in fonte_build
raiz_registro = logging.getLogger()
manipuladores_antes, nivel_antes = list(raiz_registro.handlers), raiz_registro.level
with tempfile.TemporaryDirectory() as tmp:
    try:
        assert app_teste.main(["--verificar-tela", "--data-dir", str(Path(tmp) / "RotaGuard" / "Teste")]) == 0
        registro = (Path(tmp) / "RotaGuard" / "Teste" / "registro-teste.log").read_text(encoding="utf-8")
        assert "Verificação da tela OK" in registro
    finally:
        for manipulador in list(raiz_registro.handlers):
            if manipulador not in manipuladores_antes:
                manipulador.close()
                raiz_registro.removeHandler(manipulador)
        raiz_registro.setLevel(nivel_antes)
ok("TEL-16 o pacote leva tela_teste/web e o pywebview; o build roda a verificação da tela (--verificar-tela)")

# ---------------------------------------------------------------- spec 027 pacote 1 · alarme com 4 sinais e textos
class AlarmeFalso:
    def __init__(self):
        self.chamadas = []

    def update(self, risco):
        self.chamadas.append(("update", risco.alarm_kind))

    def trigger(self, *args):
        self.chamadas.append(("trigger",))


def monitor_com_risco(risco, alarme):
    estado_risco = SimpleNamespace(events=[], alarm=getattr(risco, "alarm", False), risk=risco)
    return DriverMonitorP1(analyzer=SimpleNamespace(analyze=lambda q, t=None: SimpleNamespace(timestamp=1.0)),
                           engine=SimpleNamespace(update=lambda m, f: estado_risco), alarm=alarme, events=None)


from vision.driver_monitor import DriverMonitor as DriverMonitorP1  # noqa: E402

alarme = AlarmeFalso()
monitor_com_risco(SimpleNamespace(alarm_kind="sonolencia", parar_alarme=False, alarm=True), alarme).process_frame(base)
monitor_com_risco(SimpleNamespace(alarm_kind=None, parar_alarme=True, alarm=False), alarme).process_frame(base)
monitor_com_risco(SimpleNamespace(alarm=True), alarme).process_frame(base)  # risco da versão antiga
assert alarme.chamadas == [("update", "sonolencia"), ("update", None), ("trigger",)], alarme.chamadas
monitor_com_risco(SimpleNamespace(alarm_kind="critico", alarm=True), None).process_frame(base)  # sem alarme: não quebra
fonte_monitor = (RAIZ / "caixa" / "run_monitor.py").read_text(encoding="utf-8")
assert "autoteste" in fonte_monitor and fonte_monitor.index("Alarm(") < fonte_monitor.index("autoteste")
ok("ALM monitor chama alarm.update(risco) com o tipo do sinal, trigger na versão antiga, e o autoteste do som ao ligar")

risco_p1 = RiskAssessment(level=2, name="alto", reasons=["microssono"])
for chave, valor in (("mensagem", "Sinais de sono. Procure um local seguro para parar."), ("risco_sono", 2),
                     ("risco_distracao", 1), ("sem_visao", True), ("memoria_sonolencia", True),
                     ("sono_estimado", {"nivel": 2, "faixa": "sinais compatíveis com KSS ≥ 8", "confianca": "media",
                                        "aviso": "estimativa, não é medida de KSS nem diagnóstico"}),
                     ("alarm_kind", "sonolencia")):
    setattr(risco_p1, chave, valor)
estado_completo.risk = risco_p1
estado_completo.context = {"madrugada": True, "circadiano": "forte", "tempo_com_rosto_h": 1.25,
                           "direcao_continua_h": None, "limite_direcao_excedido": None}
medido = estado_mod.medidas(estado_completo)
risco_json = medido["risco"]
assert risco_json["mensagem"].startswith("Sinais de sono") and risco_json["risco_sono"] == 2
assert risco_json["risco_distracao"] == 1 and risco_json["sem_visao"] and risco_json["memoria_sonolencia"]
assert risco_json["sono_estimado"]["faixa"].endswith("KSS ≥ 8")
assert risco_json["sono_estimado"]["aviso"] == "estimativa, não é medida de KSS nem diagnóstico"
assert medido["contexto"]["circadiano"] == "forte" and medido["contexto"]["tempo_com_rosto_h"] == 1.25
for tipo in ("pausa_sugerida", "pausa_detectada", "estado_aparelho", "distracao_longa", "distracao_repetida",
             "sono_rosto_perdido", "fora_da_posicao"):
    assert tipo in estado_mod.EVENTOS, tipo
assert "sirene_critico.wav" in secoes_legais["Privacidade"] or "sirene_critico.wav" in "\n".join(
    t for _, t in textos_legais.secoes(Path("/dados/RotaGuard/Teste"), ""))
ok("ALM /estado traz a mensagem ao motorista, risco de sono e de distração, sem visão, memória, sono estimado "
   "com o aviso, circadiano e tempo com o rosto; eventos novos com rótulo")


# ---------------------------------------------------------------- spec 026 · conectar à empresa e enviar
sys.path.insert(0, str(RAIZ / "tests"))
from central_falsa import TOKEN, Central  # noqa: E402  (servidor de mentira da central)

from tela_teste import central as central_mod  # noqa: E402
from vision.driver_monitor import DriverMonitor  # noqa: E402

# Gancho do monitor: detalhes extras entram no evento antes de ele ir para a fila local
guardados = []


class FilaFalsa:
    def add(self, alert_type, risk_level, duration, details=None):
        guardados.append((alert_type, details))
        return "u" * 32


monitor = DriverMonitor(analyzer=SimpleNamespace(analyze=lambda quadro, t=None: SimpleNamespace(timestamp=3.0)),
                        engine=SimpleNamespace(update=lambda m, f: SimpleNamespace(
                            events=[SimpleNamespace(alert_type="microssono", risk_level=3, duration=1.2,
                                                    details={"fechado_s": 1.2})], alarm=False)),
                        alarm=None, events=FilaFalsa())
monitor.event_hooks.append(lambda evento, t: {"sessao_uid": "s" * 32, "trecho_uid": "t" * 32})
monitor.process_frame(np.zeros((4, 4, 3), np.uint8))
assert guardados == [("microssono", {"fechado_s": 1.2, "sessao_uid": "s" * 32, "trecho_uid": "t" * 32})], guardados
ok("TRE-07 gancho do monitor põe sessao_uid e trecho_uid nos detalhes do evento antes da fila local")

with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    falsa = Central().subir()
    sessao, servidor = subir(pasta)
    try:
        atual = estado(servidor)["central"]
        assert atual["conectado"] is False and atual["endereco"] == central_mod.ENDERECO_PADRAO, atual
        status, resposta = agir(servidor, "conectar", endereco=falsa.url, codigo="zzzz-9999")
        assert status == 400 and "inválido" in resposta["erro"], resposta
        status, resposta = agir(servidor, "conectar", endereco="ftp://exemplo", codigo="ABCD-2345")
        assert status == 400, "só https (ou o próprio computador, para teste)"
        status, resposta = agir(servidor, "conectar", endereco=falsa.url, codigo="abcd-2345")
        assert status == 200, resposta
        atual = estado(servidor)["central"]
        assert atual["conectado"] and atual["empresa"] == "Transportes Exemplo" and atual["enviar"] is True, atual
        texto_estado = pedir(servidor, "/estado")[2].decode()
        assert TOKEN not in texto_estado and "dsk_" not in texto_estado, "o token nunca sai para a página"
        salvo = json.loads((pasta / "central.json").read_text(encoding="utf-8"))
        assert salvo["token"] == TOKEN and salvo["empresa"]["nome"] == "Transportes Exemplo"

        # Um teste com o vídeo sintético: a sessão (início e fim com o resumo, sem cardio) vai para a central
        video = video_sintetico(Path(tmp), segundos=3.0)
        agir(servidor, "iniciar", opcoes={"camera": str(video), "celular": False, "cardio": True})
        assert esperar(lambda: estado(servidor)["fase"] == "resumo", 90), estado(servidor)["fase"]
        assert esperar(lambda: any(s.get("encerrada_em") for s in falsa.sessoes.values()), 20), falsa.sessoes
        enviada = next(iter(falsa.sessoes.values()))
        assert "frequencia_cardiaca" not in json.dumps(enviada) and enviada["resumo"]["duracao_s"] > 0, enviada
        assert enviada["programa"].startswith("RotaGuard Script") and enviada["camera"] == "Vídeo sintetico.avi"
        assert "frequencia_cardiaca" in estado(servidor)["resumo"], "o resumo local continua com o cardio"
        assert any(p[1] == "/api/devices/heartbeat" for p in falsa.pedidos), "sinal de vida enviado"
        assert esperar(lambda: estado(servidor)["central"]["situacao"] == "em_dia", 15)
        ok("TRE-07 tela: conectar com o código, enviar a sessão com o resumo sem cardio e o sinal de vida")

        # Trecho no resumo com player: o arquivo é servido só com o token
        trecho_uid = "a1" * 16
        pasta_trecho = pasta / "trechos" / ("b2" * 16)
        pasta_trecho.mkdir(parents=True)
        (pasta_trecho / f"{trecho_uid}.webm").write_bytes(b"\x1a\x45\xdf\xa3" + b"0" * 2000)
        (pasta_trecho / f"{trecho_uid}.json").write_text(json.dumps({"uid": trecho_uid, "formato": "webm",
                                                                     "arquivo": f"{trecho_uid}.webm"}), "utf-8")
        status, cabecalhos, corpo = pedir(servidor, f"/trecho/{trecho_uid}")
        assert status == 200 and cabecalhos["Content-Type"] == "video/webm" and len(corpo) == 2004
        status, cabecalhos, corpo = pedir(servidor, f"/trecho/{trecho_uid}", cabecalhos={"Range": "bytes=4-13"})
        assert status == 206 and corpo == b"0" * 10 and cabecalhos["Content-Range"] == "bytes 4-13/2004"
        assert pedir(servidor, f"/trecho/{trecho_uid}", token=False)[0] == 403
        assert pedir(servidor, "/trecho/..%2F..%2Fcentral.json")[0] == 404
        assert pedir(servidor, f"/trecho/{'c3' * 16}")[0] == 404
        ok("TRE-05 tela: o trecho do resumo é servido (com Range para o player) só com o token")

        # Desligar o envio para; desconectar apaga o token e mantém a fila e os arquivos
        status, _ = agir(servidor, "enviar", ligado=False)
        assert status == 200 and estado(servidor)["central"]["enviar"] is False
        assert estado(servidor)["central"]["situacao"] == "desligado"
        status, _ = agir(servidor, "desconectar")
        assert status == 200 and estado(servidor)["central"]["conectado"] is False
        assert not (pasta / "central.json").exists() or "token" not in (pasta / "central.json").read_text("utf-8")
        assert (pasta / "central" / "fila.db").exists() and (pasta_trecho / f"{trecho_uid}.webm").exists()
        ok("TRE-08 tela: desligar o envio para e desconectar apaga o token, sem apagar o que é local")

        # A empresa revoga o token (401/403): a tela mostra "desconectado pela empresa" e para, sem apagar nada local
        status, _ = agir(servidor, "conectar", endereco=falsa.url, codigo="ABCD2345")
        assert status == 200 and estado(servidor)["central"]["conectado"]
        falsa.forcar["/api/devices/heartbeat"] = (401, {})
        assert esperar(lambda: not estado(servidor)["central"]["conectado"], 20), estado(servidor)["central"]
        atual = estado(servidor)["central"]
        assert "desconectou" in (atual.get("aviso") or ""), atual
        assert "token" not in (pasta / "central.json").read_text("utf-8")
        assert (pasta / "central" / "fila.db").exists() and (pasta_trecho / f"{trecho_uid}.webm").exists()
        del falsa.forcar["/api/devices/heartbeat"]
        ok("TRE-08 tela: token revogado pela empresa vira 'desconectado pela empresa', sem apagar nada local")

        # Apagar dados com o registro e a fila da central abertos pelo próprio processo (no Windows, arquivo aberto
        # não se apaga): solta os arquivos, apaga tudo e o registro continua funcionando depois.
        raiz_log = logging.getLogger()
        antes_handlers = list(raiz_log.handlers)
        caminho_log = app_teste.configurar_registro(pasta)
        logging.getLogger("drivesafe").info("antes de apagar")
        status, _ = agir(servidor, "conectar", endereco=falsa.url, codigo="ABCD2345")
        assert status == 200 and (pasta / "central" / "fila.db").exists()
        status, resposta = agir(servidor, "apagar_dados")
        try:
            assert status == 200 and resposta["removidos"] >= 3, resposta
            assert not (pasta / "central.json").exists() and not (pasta / "central" / "fila.db").exists()
            assert not list((pasta / "trechos").rglob("*.webm")), "trechos apagados"
            assert estado(servidor)["central"]["conectado"] is False
            logging.getLogger("drivesafe").info("depois de apagar")
            for manipulador in raiz_log.handlers:
                manipulador.flush()
            assert "depois de apagar" in caminho_log.read_text(encoding="utf-8")
        finally:
            for manipulador in list(raiz_log.handlers):
                if manipulador not in antes_handlers:
                    manipulador.close()
                    raiz_log.removeHandler(manipulador)
        ok("APT-22 tela: apagar dados com o registro e a fila abertos apaga tudo, desconecta e o registro segue")
    finally:
        descer(sessao, servidor)
        falsa.descer()

print(f"\n{checks} verificações OK")
