# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller do RotaGuard Script (specs 010 e 023). Não rodar direto: use python implantacao/app-teste/build.py."""
import importlib.util
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

# A tela nova (spec 023) abre na janela do pywebview (WebView2 no Windows). Sem ele no ambiente do build, o pacote
# abriria a tela no navegador: melhor falhar aqui do que distribuir assim sem perceber.
if importlib.util.find_spec("webview") is None:
    raise SystemExit("pywebview não instalado: python -m pip install -r caixa/requirements-app-teste.txt")

AQUI = Path(SPECPATH).resolve()  # noqa: F821 - definido pelo PyInstaller
RAIZ = AQUI.parents[1]
CAIXA = RAIZ / "caixa"
# Vem do build.py, no Windows: o arquivo com as propriedades do .exe (empresa e produto RotaGuard). Sem Mac (14/09/2026).
PROPRIEDADES_WINDOWS = os.environ.get("ROTAGUARD_VERSAO_WINDOWS") if sys.platform.startswith("win") else None

# Os modelos ficam em vision/models dentro do pacote, onde vision/face.py e vision/phone.py os procuram
# (Path(__file__).parent / "models"). Nada é baixado ao abrir.
datas = [
    (str(CAIXA / "vision" / "models"), "vision/models"),
    # Página da tela nova (HTML, CSS e JS sem build), onde tela_teste/__init__.py procura (Path(__file__).parent).
    (str(CAIXA / "tela_teste" / "web"), "tela_teste/web"),
    (str(AQUI / "rotaguard.png"), "."),
    # Licenças de terceiros (Apache 2.0 e MIT pedem o aviso junto do programa) e aba Licenças da seção legal.
    (str(RAIZ / "THIRD_PARTY_NOTICES.md"), "."),
]
binaries = []
# A tela importa o monitor e o pywebview dentro de funções; os DLLs do WebView2 (webview/lib) e do pythonnet entram
# pelos ganchos do pyinstaller-hooks-contrib, como no painel (implantacao/painel/rotaguard-painel.spec).
hiddenimports = ["run_monitor", "app_teste", "tela_teste.app", "tela_teste.servidor", "tela_teste.sessao", "webview"]
mp_datas, mp_binaries, mp_hidden = collect_all("mediapipe")
datas += mp_datas
binaries += mp_binaries
hiddenimports += mp_hidden
# Textos das licenças das bibliotecas redistribuídas (pastas *.dist-info). O LICENSE-3RD-PARTY.txt da OpenCV cobre a
# FFmpeg (LGPL 2.1) que vai junto em opencv_videoio_ffmpeg. O MediaPipe já vem com LICENSE e NOTICE pelo collect_all.
for pacote in ("opencv-contrib-python", "numpy", "matplotlib", "sounddevice", "absl-py", "flatbuffers",
               "pywebview", "bottle", "proxy_tools", "typing_extensions"):
    datas += copy_metadata(pacote)
if sys.platform.startswith("win"):
    for pacote in ("pythonnet", "clr_loader", "cffi", "pycparser"):
        datas += copy_metadata(pacote)

a = Analysis(  # noqa: F821
    [str(CAIXA / "app_teste.py")],
    pathex=[str(CAIXA)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest", "IPython", "notebook", "jupyter"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RotaGuardScript",
    console=False,
    icon=str(AQUI / "rotaguard.ico") if sys.platform.startswith("win") else None,
    version=PROPRIEDADES_WINDOWS,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="RotaGuardScript")  # noqa: F821
