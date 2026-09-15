# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller do RotaGuard Painel (spec 013). Não rodar direto: use python implantacao/painel/build.py."""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

AQUI = Path(SPECPATH).resolve()  # noqa: F821 - definido pelo PyInstaller
RAIZ = AQUI.parents[1]
DESKTOP = RAIZ / "painel" / "desktop"
INTERFACE = RAIZ / "painel" / "app" / "out"
ICONE = RAIZ / "implantacao" / "app-teste" / "rotaguard.ico"
# Vem do build.py: o arquivo com as propriedades do .exe (empresa RotaGuard, produto RotaGuard Painel).
PROPRIEDADES_WINDOWS = os.environ.get("ROTAGUARD_VERSAO_WINDOWS") if sys.platform.startswith("win") else None

if not (INTERFACE / "index.html").is_file():
    raise SystemExit(f"Interface não encontrada em {INTERFACE}: rode npm run build em painel/app.")

# A exportação estática vai para _internal/interface, onde rotaguard_painel.pasta_interface() procura (sys._MEIPASS).
# Os DLLs do WebView2 (webview/lib) e do pythonnet (Python.Runtime.dll, clr_loader) entram pelos ganchos do
# pyinstaller-hooks-contrib.
datas = [
    (str(INTERFACE), "interface"),
    (str(ICONE), "."),
]
# Textos das licenças das bibliotecas redistribuídas (pastas *.dist-info).
for pacote in ("pywebview", "pythonnet", "clr_loader", "cffi", "pycparser", "bottle", "proxy_tools",
               "typing_extensions", "cryptography"):
    datas += copy_metadata(pacote)

a = Analysis(  # noqa: F821
    [str(DESKTOP / "rotaguard_painel.py")],
    pathex=[str(DESKTOP)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    # Bibliotecas da caixa que estão no mesmo .venv e o painel não usa.
    excludes=["numpy", "cv2", "mediapipe", "matplotlib", "pytest", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RotaGuardPainel",
    console=False,
    icon=str(ICONE),
    version=PROPRIEDADES_WINDOWS,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="RotaGuardPainel")  # noqa: F821
