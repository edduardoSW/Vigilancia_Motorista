# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller do RotaGuard Teste (spec 010). Não rodar direto: use python implantacao/app-teste/build.py."""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

AQUI = Path(SPECPATH).resolve()  # noqa: F821 - definido pelo PyInstaller
RAIZ = AQUI.parents[1]
CAIXA = RAIZ / "caixa"
# Vem do build.py, no Windows: o arquivo com as propriedades do .exe (empresa e produto RotaGuard). Sem Mac (14/09/2026).
PROPRIEDADES_WINDOWS = os.environ.get("ROTAGUARD_VERSAO_WINDOWS") if sys.platform.startswith("win") else None

# Os modelos ficam em vision/models dentro do pacote, onde vision/face.py e vision/phone.py os procuram
# (Path(__file__).parent / "models"). Nada é baixado ao abrir.
datas = [
    (str(CAIXA / "vision" / "models"), "vision/models"),
    (str(AQUI / "rotaguard.png"), "."),
    # Licenças de terceiros (Apache 2.0 e MIT pedem o aviso junto do programa) e aba Licenças da seção legal.
    (str(RAIZ / "THIRD_PARTY_NOTICES.md"), "."),
]
binaries = []
hiddenimports = ["run_monitor"]
mp_datas, mp_binaries, mp_hidden = collect_all("mediapipe")
datas += mp_datas
binaries += mp_binaries
hiddenimports += mp_hidden
# Textos das licenças das bibliotecas redistribuídas (pastas *.dist-info). O LICENSE-3RD-PARTY.txt da OpenCV cobre a
# FFmpeg (LGPL 2.1) que vai junto em opencv_videoio_ffmpeg. O MediaPipe já vem com LICENSE e NOTICE pelo collect_all.
for pacote in ("opencv-contrib-python", "numpy", "matplotlib", "sounddevice", "absl-py", "flatbuffers"):
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
    name="RotaGuardTeste",
    console=False,
    icon=str(AQUI / "rotaguard.ico") if sys.platform.startswith("win") else None,
    version=PROPRIEDADES_WINDOWS,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="RotaGuardTeste")  # noqa: F821
