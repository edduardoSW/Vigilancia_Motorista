"""Spec 010: app de teste do script (tela de início, modo sem servidor, fim de vídeo e registro em arquivo).

Precisa de numpy e opencv (caixa/requirements.txt):
    python tests/test_app_teste.py
"""
import logging
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
import vision.camera as camera_mod  # noqa: E402
import vision.driver_monitor as driver_monitor  # noqa: E402
from vision.camera import OpenCVCamera  # noqa: E402
from vision.driver_monitor import WINDOW_TITLE, DriverMonitor  # noqa: E402

checks = 0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


# APT-01 · pasta de dados por sistema
windows = app_teste.pasta_dados(sistema="win32", ambiente={"LOCALAPPDATA": r"C:\Users\ana\AppData\Local"}, home=Path("/h"))
assert windows == Path(r"C:\Users\ana\AppData\Local") / "RotaGuard" / "Teste", windows
assert app_teste.pasta_dados(sistema="win32", ambiente={}, home=Path("/h")) == Path("/h") / "AppData" / "Local" / "RotaGuard" / "Teste"
assert app_teste.pasta_dados(sistema="darwin", ambiente={}, home=Path("/Users/ana")) == \
    Path("/Users/ana") / "Library" / "Application Support" / "RotaGuard" / "Teste"
assert app_teste.pasta_dados(sistema="linux", ambiente={"XDG_DATA_HOME": "/dados"}, home=Path("/home/ana")) == \
    Path("/dados") / "rotaguard" / "teste"
assert app_teste.pasta_dados(sistema="linux", ambiente={}, home=Path("/home/ana")) == \
    Path("/home/ana") / ".local" / "share" / "rotaguard" / "teste"
ok("APT-01 pasta de dados em Windows, macOS e Linux (com e sem XDG_DATA_HOME)")

# APT-02 · linha do monitor montada a partir das opções da tela de início
pasta = Path("/tmp/rg")
padrao = app_teste.argumentos_monitor(app_teste.OpcoesTeste(), pasta)
for esperado in (["--camera", "auto"], ["--window"], ["--sem-servidor"], ["--data-dir", str(pasta)],
                 ["--calibration-min", "60"], ["--calibration-max", "120"], ["--camera-ir", "auto"],
                 ["--espera-camera", "15"]):
    posicao = [i for i in range(len(padrao)) if padrao[i:i + len(esperado)] == esperado]
    assert posicao, (esperado, padrao)
assert "--sem-celular" not in padrao and "--mute" not in padrao
sem_extras = app_teste.argumentos_monitor(
    app_teste.OpcoesTeste(camera="video.mp4", celular=False, som=False, calibracao_rapida=False, camera_ir="sim"), pasta)
assert "--sem-celular" in sem_extras and "--mute" in sem_extras
assert "--calibration-min" not in sem_extras and sem_extras[sem_extras.index("--camera") + 1] == "video.mp4"
assert sem_extras[sem_extras.index("--camera-ir") + 1] == "sim"
ok("APT-02 opções viram --sem-celular, --mute, calibração rápida, câmera e --sem-servidor")

# APT-03 · processo do monitor: o próprio executável empacotado, ou python app_teste.py
assert app_teste.comando_monitor(["--camera", "1"], congelado=True, executavel=r"C:\App\RotaGuardTeste.exe") == \
    [r"C:\App\RotaGuardTeste.exe", "--monitor", "--camera", "1"]
dev = app_teste.comando_monitor(["--camera", "1"], congelado=False, executavel="/usr/bin/python3")
assert dev[0] == "/usr/bin/python3" and Path(dev[1]).name == "app_teste.py" and dev[2:] == ["--monitor", "--camera", "1"]
ok("APT-03 comando do monitor empacotado e fora do pacote")

# APT-04 · main: sem argumentos abre a tela; com --monitor ou argumentos roda o monitor
chamadas = []
assert app_teste.main([], rodar=lambda a: chamadas.append(("monitor", a)) or 0, tela=lambda: chamadas.append(("tela",)) or 0) == 0
assert app_teste.main(["--monitor", "--camera", "2"], rodar=lambda a: chamadas.append(("monitor", a)) or 0,
                      tela=lambda: chamadas.append(("tela",)) or 0) == 0
assert app_teste.main(["--help"], rodar=lambda a: chamadas.append(("monitor", a)) or 7, tela=lambda: 0) == 7
assert chamadas == [("tela",), ("monitor", ["--camera", "2"]), ("monitor", ["--help"])], chamadas
ok("APT-04 main abre a tela sem argumentos e repassa --monitor e outros argumentos")

# APT-05 · --sem-servidor (opção e variável) desliga a sincronização
assert run_monitor.parse_args([]).sem_servidor is False
assert run_monitor.parse_args(["--sem-servidor"]).sem_servidor is True
import os  # noqa: E402

os.environ["DRIVESAFE_SEM_SERVIDOR"] = "1"
try:
    assert run_monitor.parse_args([]).sem_servidor is True
finally:
    del os.environ["DRIVESAFE_SEM_SERVIDOR"]
assert run_monitor.deve_sincronizar(SimpleNamespace(sem_servidor=True)) is False
assert run_monitor.deve_sincronizar(SimpleNamespace(sem_servidor=False)) is True
ok("APT-05 --sem-servidor e DRIVESAFE_SEM_SERVIDOR desligam a sincronização")


def monitor_de_teste():
    monitor = DriverMonitor(analyzer=None, engine=None, alarm=None, events=None)
    monitor.quadros = 0

    def processar(frame, ambient_lux=None):
        monitor.quadros += 1
        return SimpleNamespace()

    monitor.process_frame = processar
    return monitor


# APT-06 · arquivo de vídeo termina no fim, sem reabrir
with tempfile.TemporaryDirectory() as tmp:
    video = Path(tmp) / "curto.avi"
    escritor = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    for i in range(5):
        escritor.write(np.full((48, 64, 3), i * 40, dtype=np.uint8))
    escritor.release()
    camera = OpenCVCamera(str(video), 64, 48)
    assert camera.terminou is False
    monitor = monitor_de_teste()
    inicio = time.monotonic()
    monitor.run(camera, show_window=False)
    assert monitor.quadros == 5, monitor.quadros
    assert camera.terminou is True
    assert time.monotonic() - inicio < 2.5, "o fim do vídeo não pode esperar reaberturas"
ok("APT-06 vídeo gravado: processa os quadros e termina no fim, sem reabrir")


# APT-07 · câmera ao vivo continua tentando reabrir (sem regressão)
class CameraAoVivo:
    terminou = False

    def __init__(self, monitor):
        self.monitor = monitor
        self.aberturas = 0

    def read(self):
        return False, None

    def open(self):
        self.aberturas += 1
        self.monitor.stop()
        return True

    def describe(self):
        return "falsa"

    def ambient_lux(self):
        return None

    def release(self):
        pass


sono_original = driver_monitor.time.sleep
driver_monitor.time.sleep = lambda s: None
try:
    monitor = monitor_de_teste()
    viva = CameraAoVivo(monitor)
    monitor.run(viva, show_window=False)
    assert viva.aberturas == 1 and monitor.quadros == 0
finally:
    driver_monitor.time.sleep = sono_original
ok("APT-07 câmera ao vivo sem imagem ainda tenta reabrir")

# APT-08 · nome visível
assert "RotaGuard" in WINDOW_TITLE and "DriveSafe" not in WINDOW_TITLE
ok("APT-08 título da janela da câmera com RotaGuard")

# APT-09 · registro em arquivo, mesmo sem console (executável de janela)
with tempfile.TemporaryDirectory() as tmp:
    raiz = logging.getLogger()
    handlers_antes, nivel_antes = list(raiz.handlers), raiz.level
    saida, erro = sys.stdout, sys.stderr
    try:
        sys.stdout = sys.stderr = None
        caminho = app_teste.configurar_registro(Path(tmp))
        logging.getLogger("drivesafe").info("linha de teste do registro")
        sys.stdout, sys.stderr = saida, erro
        for h in raiz.handlers:
            h.flush()
        assert caminho == Path(tmp) / "registro-teste.log"
        assert "linha de teste do registro" in caminho.read_text(encoding="utf-8")
    finally:
        sys.stdout, sys.stderr = saida, erro
        for h in list(raiz.handlers):
            if h not in handlers_antes:
                h.close()
                raiz.removeHandler(h)
        raiz.setLevel(nivel_antes)
assert app_teste.pasta_do_argumento(["--camera", "0", "--data-dir", "/x/y"]) == Path("/x/y")
assert app_teste.pasta_do_argumento(["--data-dir=/z"]) == Path("/z")
assert app_teste.pasta_do_argumento(["--camera", "0"]) is None
ok("APT-09 registro em registro-teste.log sem console; --data-dir lido dos argumentos")

# APT-13 · câmera do Windows abre em ~1 s: sem as transformações de hardware do Media Foundation (antes ~16 s)
assert os.environ.get("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS") == "0"
ok("APT-13 run_monitor desliga as transformações de hardware do MSMF antes de abrir a câmera")


# APT-14 · câmera automática: a primeira que abre e manda imagem
class CameraFalsa:
    def __init__(self, fonte, abre, imagem):
        self.fonte, self.aberta, self.imagem, self.liberada = fonte, abre, imagem, False

    def read(self):
        return (True, np.zeros((2, 2, 3), dtype=np.uint8)) if self.imagem else (False, None)

    def release(self):
        self.liberada = True


def fabrica(abrem, com_imagem, criadas):
    def criar(fonte, largura, altura, avisar=True):
        camera = CameraFalsa(fonte, fonte in abrem, fonte in com_imagem)
        criadas.append(camera)
        return camera
    return criar


criadas = []
achada = camera_mod.find_camera(640, 480, indices=range(4), factory=fabrica({"1", "2"}, {"2"}, criadas), pausa=0)
assert achada.fonte == "2", achada.fonte
assert [c.fonte for c in criadas] == ["0", "1", "2"] and criadas[0].liberada and criadas[1].liberada
assert not criadas[2].liberada
assert issubclass(camera_mod.CameraIndisponivel, RuntimeError)
try:
    camera_mod.find_camera(640, 480, indices=range(3), factory=fabrica(set(), set(), []), pausa=0)
except camera_mod.CameraIndisponivel as exc:
    assert "Nenhuma câmera" in str(exc), exc
else:
    raise AssertionError("sem câmera, find_camera deveria levantar CameraIndisponivel")
ok("APT-14 câmera automática: usa a primeira que abre e manda imagem; sem nenhuma, erro claro")


# APT-15 · câmera sem imagem: com --espera-camera o teste termina com aviso em vez de esperar para sempre
class RelogioFalso:
    def __init__(self):
        self.agora = 0.0

    def monotonic(self):
        return self.agora

    def sleep(self, segundos):
        self.agora += segundos


class CameraMuda(CameraAoVivo):
    def __init__(self, monitor, quadros=0):
        super().__init__(monitor)
        self.quadros = quadros

    def read(self):
        if self.quadros > 0:
            self.quadros -= 1
            return True, np.zeros((48, 64, 3), dtype=np.uint8)
        return False, None

    def open(self):
        self.aberturas += 1
        return False


tempo_original = driver_monitor.time
try:
    driver_monitor.time = relogio = RelogioFalso()
    monitor = monitor_de_teste()
    muda = CameraMuda(monitor)
    monitor.run(muda, show_window=False, espera_camera_s=10.0)
    assert monitor.sem_imagem is True and 9.9 <= relogio.agora <= 10.6, relogio.agora
    assert muda.aberturas >= 2, muda.aberturas

    driver_monitor.time = relogio = RelogioFalso()
    monitor = monitor_de_teste()
    perdeu = CameraMuda(monitor, quadros=3)
    monitor.run(perdeu, show_window=False, espera_camera_s=5.0)
    assert monitor.sem_imagem is True and monitor.quadros == 3 and 4.9 <= relogio.agora <= 5.6, relogio.agora

    driver_monitor.time = RelogioFalso()
    monitor = monitor_de_teste()
    monitor.run(CameraAoVivo(monitor), show_window=False)
    assert monitor.sem_imagem is False
finally:
    driver_monitor.time = tempo_original
assert run_monitor.parse_args([]).espera_camera == 0.0
assert run_monitor.parse_args(["--espera-camera", "15"]).espera_camera == 15.0
assert run_monitor.SAIDA_SEM_CAMERA == 3 == app_teste.SAIDA_SEM_CAMERA
ok("APT-15 sem imagem por N s (nunca chegou ou parou) encerra com sem_imagem; a caixa (padrão 0) segue tentando")


# APT-16 · janela: fechar no X, Esc ou Q (maiúsculo também) encerra o teste
class CameraSempre:
    terminou = False

    def read(self):
        return True, np.zeros((48, 64, 3), dtype=np.uint8)

    def open(self):
        return True

    def describe(self):
        return "sempre"

    def ambient_lux(self):
        return None

    def release(self):
        pass


class Cv2Falso:
    error = cv2.error
    WND_PROP_VISIBLE = cv2.WND_PROP_VISIBLE

    def __init__(self, propriedade, teclas=()):
        self.propriedade, self.teclas, self.mostrados = propriedade, list(teclas), 0

    def imshow(self, titulo, imagem):
        self.mostrados += 1

    def waitKey(self, atraso):
        return self.teclas.pop(0) if self.teclas else -1

    def getWindowProperty(self, titulo, propriedade):
        return self.propriedade(self.mostrados)

    def destroyAllWindows(self):
        pass


cv2_original, desenho_original = driver_monitor.cv2, driver_monitor.draw_overlay
driver_monitor.draw_overlay = lambda quadro, estado, latencia=None: quadro
try:
    for descricao, falso, esperado in (
        ("X", Cv2Falso(lambda n: 1.0 if n <= 3 else -1.0), 4),
        ("Q sem suporte a WND_PROP_VISIBLE", Cv2Falso(lambda n: -1.0, [-1] * 5 + [ord("Q")]), 6),
        ("Esc", Cv2Falso(lambda n: 1.0, [27]), 1),
        ("q", Cv2Falso(lambda n: 1.0, [-1, ord("q")]), 2),
    ):
        driver_monitor.cv2 = falso
        monitor = monitor_de_teste()
        monitor.run(CameraSempre(), show_window=True)
        assert monitor.quadros == esperado, (descricao, monitor.quadros)
finally:
    driver_monitor.cv2, driver_monitor.draw_overlay = cv2_original, desenho_original
ok("APT-16 janela da câmera: X, Esc, q e Q encerram; backend sem WND_PROP_VISIBLE não encerra sozinho")

# APT-17 · tela de início: câmera automática, nomes amigáveis, mensagens de saída e fase do teste
assert app_teste.OpcoesTeste().camera == "auto"
assert app_teste.CAMERAS[0].startswith("Automática")
assert app_teste.camera_escolhida(app_teste.CAMERAS[0]) == "auto" and app_teste.camera_escolhida("  ") == "auto"
assert app_teste.camera_escolhida("Câmera 1") == "0" and app_teste.camera_escolhida("câmera 3") == "2"
assert app_teste.camera_escolhida("2") == "2"
assert app_teste.camera_escolhida(r"C:\videos\teste 1.mp4") == r"C:\videos\teste 1.mp4"
assert app_teste.mensagem_saida(0).startswith("Teste encerrado")
assert "Nenhuma câmera" in app_teste.mensagem_saida(app_teste.SAIDA_SEM_CAMERA)
assert "código 1" in app_teste.mensagem_saida(1)
assert app_teste.fase_do_registro("x INFO drivesafe.camera: Câmera aberta: OpenCV 0.\n") == "camera"
assert app_teste.fase_do_registro("Câmera aberta\nMonitoramento iniciado (janela: q sai, c recalibra).") == "rodando"
assert app_teste.fase_do_registro("carregando modelos") is None
ok("APT-17 tela de início: câmera automática, nomes amigáveis, mensagens de saída e fase do teste")

# APT-18 · de ponta a ponta: câmera escolhida que não existe → código 3 rápido, sem esperar a espera inteira
import socket  # noqa: E402


class Captura(logging.Handler):
    def __init__(self):
        super().__init__()
        self.linhas = []

    def emit(self, record):
        self.linhas.append(record.getMessage())


if sys.platform != "darwin":  # no macOS a câmera pede permissão e pode segurar o teste no CI
    with tempfile.TemporaryDirectory() as tmp:
        captura, raiz = Captura(), logging.getLogger()
        nivel_antes = raiz.level
        raiz.addHandler(captura)
        raiz.setLevel(logging.INFO)
        inicio = time.monotonic()
        try:
            codigo = run_monitor.main(["--camera", "9", "--espera-camera", "30", "--no-window", "--sem-servidor",
                                       "--sem-celular", "--mute", "--data-dir", tmp])
        finally:
            raiz.removeHandler(captura)
            raiz.setLevel(nivel_antes)
        assert codigo == run_monitor.SAIDA_SEM_CAMERA, codigo
        assert time.monotonic() - inicio < 25, "câmera que não abre não pode esperar os 30 s"
        assert any("não abriu" in linha for linha in captura.linhas), captura.linhas
        assert not any(socket.gethostname() in linha for linha in captura.linhas), "nome do computador no registro"
    ok("APT-18 câmera inexistente: código 3 sem esperar, aviso claro e registro sem o nome do computador")

# APT-19 · propriedades do executável no Windows: RotaGuard, nada do computador que gerou o build
import importlib.util  # noqa: E402

especificacao = importlib.util.spec_from_file_location("build_app_teste", RAIZ / "implantacao" / "app-teste" / "build.py")
build_app = importlib.util.module_from_spec(especificacao)
especificacao.loader.exec_module(build_app)
propriedades = build_app.texto_versao_windows("0.3.0")
for esperado in ("StringStruct('CompanyName', 'RotaGuard')", "StringStruct('ProductName', 'RotaGuard Teste')",
                 "StringStruct('OriginalFilename', 'RotaGuardTeste.exe')", "filevers=(0, 3, 0, 0)"):
    assert esperado in propriedades, esperado
assert socket.gethostname() not in propriedades
assert build_app.numeros_versao("1.2") == (1, 2, 0, 0) and build_app.numeros_versao("0.1.0-rc1") == (0, 1, 0, 0)
try:
    from PyInstaller.utils.win32 import versioninfo
except ImportError:
    print("-- PyInstaller ausente: formato das propriedades não conferido")
else:
    with tempfile.TemporaryDirectory() as tmp:
        arquivo = Path(tmp) / "propriedades.txt"
        arquivo.write_text(propriedades, encoding="utf-8")
        carregado = versioninfo.load_version_info_from_text_file(str(arquivo))
        assert "RotaGuard" in str(carregado)
ok("APT-19 propriedades do .exe com empresa e produto RotaGuard, no formato do PyInstaller")

# APT-21 · privacidade, LGPD e termos numa seção do app, coerentes com o que o app faz, sem aceite obrigatório
import inspect  # noqa: E402

import textos_legais  # noqa: E402

pasta_exemplo = Path("/dados/RotaGuard/Teste")
secoes = textos_legais.secoes(pasta_exemplo, "AVISOS DE TERCEIROS DE EXEMPLO")
assert [titulo for titulo, _ in secoes] == ["Privacidade", "LGPD", "Termos de uso", "Licenças"]
tudo = "\n".join(conteudo for _, conteudo in secoes)
for esperado in ("Lei nº 13.709/2018", "art. 18", "art. 11", "não é diagnóstico", "eventos.db", app_teste.ARQUIVO_REGISTRO,
                 "não envia imagens", "Apagar dados deste computador", "Abrir pasta de dados", str(pasta_exemplo),
                 "Não é preciso aceitar nada", "AVISOS DE TERCEIROS DE EXEMPLO", "Apache 2.0", "MIT",
                 textos_legais.VERSAO_TEXTOS):
    assert esperado in tudo, esperado
assert "--sem-servidor" in app_teste.argumentos_monitor(app_teste.OpcoesTeste(), pasta_exemplo), "texto diz que nada sai"
assert "em preparação" in textos_legais.contato("") and textos_legais.contato(" privacidade@x ") == "privacidade@x"
assert "aceit" not in inspect.getsource(app_teste.TelaInicio._iniciar).lower(), "iniciar o teste não pode exigir aceite"
assert "Apache" in app_teste.avisos_de_terceiros() and "MIT" in app_teste.avisos_de_terceiros()
especificacao_pacote = (RAIZ / "implantacao" / "app-teste" / "rotaguard-teste.spec").read_text(encoding="utf-8")
assert "THIRD_PARTY_NOTICES.md" in especificacao_pacote
assert "copy_metadata" in especificacao_pacote and "opencv-contrib-python" in especificacao_pacote
assert "LGPL" in tudo and ".dist-info" in tudo
ok("APT-21 seção de privacidade, LGPD, termos e licenças coerente com o app e sem aceite para usar")

# APT-22 · apagar os dados do teste (eliminação, LGPD art. 18) só na pasta do app
with tempfile.TemporaryDirectory() as tmp:
    pasta_teste = Path(tmp) / "RotaGuard" / "Teste"
    (pasta_teste / "perfis").mkdir(parents=True)
    for nome in ("eventos.db", "registro-teste.log", "sirene.wav", "perfis/teste.json"):
        (pasta_teste / nome).write_text("x", encoding="utf-8")
    vizinho = Path(tmp) / "RotaGuard" / "outro-arquivo.txt"
    vizinho.write_text("fica", encoding="utf-8")
    assert app_teste.apagar_dados(pasta_teste) == 4
    assert pasta_teste.exists() and not any(pasta_teste.iterdir()) and vizinho.exists()
    assert app_teste.apagar_dados(pasta_teste) == 0
    for errada in (Path(tmp) / "RotaGuard", Path(tmp) / "outra" / "Teste"):
        try:
            app_teste.apagar_dados(errada)
        except ValueError:
            pass
        else:
            raise AssertionError(f"apagar_dados aceitou pasta errada: {errada}")
ok("APT-22 apagar dados: limpa a pasta do teste, mantém a pasta e recusa qualquer outra")

print(f"\n{checks} verificações OK")
