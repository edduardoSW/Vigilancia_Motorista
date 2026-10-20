"""Monta o RotaGuard Script (specs 010 e 023): PyInstaller → testes do pacote → pacotes para download.

Uso (com caixa/requirements-app-teste.txt e o PyInstaller 6.22.3 instalados):
  python implantacao/app-teste/build.py              pacote do sistema atual
  python implantacao/app-teste/build.py --sem-fumaca pula o teste de fumaça (não usar na release)

Saída em build/app-teste/pacotes/:
  Windows: RotaGuard-Script-windows-x64-setup.exe (Inno Setup) e RotaGuard-Script-windows-x64.zip
  Linux:   RotaGuard-Script-linux-x86_64.tar.gz
Sem Mac (decisão de 14/09/2026): no macOS o build recusa.
Versão: variável ROTAGUARD_VERSAO (tag teste-vX.Y.Z) ou __version__ de caixa/vision.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
SAIDA = RAIZ / "build" / "app-teste"
DIST = SAIDA / "dist"
TRABALHO = SAIDA / "work"
PACOTES = SAIDA / "pacotes"
NOME = "RotaGuard-Script"
PASTA_APP = "RotaGuardScript"


def versao() -> str:
    bruta = os.environ.get("ROTAGUARD_VERSAO", "").strip()
    if bruta:
        return re.sub(r"^teste-v", "", bruta)
    texto = (RAIZ / "caixa" / "vision" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', texto).group(1)


def alvo() -> str:
    maquina = platform.machine().lower()
    if sys.platform.startswith("win"):
        return "windows-x64" if maquina in ("amd64", "x86_64") else f"windows-{maquina}"
    return "linux-x86_64" if maquina in ("x86_64", "amd64") else f"linux-{maquina}"


def executavel() -> Path:
    nome = f"{PASTA_APP}.exe" if sys.platform.startswith("win") else PASTA_APP
    return DIST / PASTA_APP / nome


def numeros_versao(texto: str) -> tuple[int, int, int, int]:
    partes = [int(parte) if parte.isdigit() else 0 for parte in re.split(r"[.+-]", texto)[:4]]
    return tuple(partes + [0] * (4 - len(partes)))


def texto_versao_windows(numero: str, produto: str = "RotaGuard Script", executavel: str = PASTA_APP) -> str:
    """Propriedades do .exe (Detalhes no Windows): empresa RotaGuard e o produto, nada do computador do build.

    O padrão é o RotaGuardScript.exe. O painel (implantacao/painel/build.py, spec 013) usa produto "RotaGuard Painel"."""
    versao_tupla = numeros_versao(numero)
    campos = (("CompanyName", "RotaGuard"), ("FileDescription", produto), ("FileVersion", numero),
              ("InternalName", executavel), ("LegalCopyright", "© 2026 RotaGuard"),
              ("OriginalFilename", f"{executavel}.exe"), ("ProductName", produto), ("ProductVersion", numero))
    tabela = ",\n".join(f"        StringStruct({chave!r}, {valor!r})" for chave, valor in campos)
    return (
        "VSVersionInfo(\n"
        f"  ffi=FixedFileInfo(filevers={versao_tupla}, prodvers={versao_tupla}, mask=0x3f, flags=0x0, OS=0x40004,\n"
        "                    fileType=0x1, subtype=0x0, date=(0, 0)),\n"
        "  kids=[\n"
        f"    StringFileInfo([StringTable('041604B0', [\n{tabela}])]),\n"
        "    VarFileInfo([VarStruct('Translation', [0x0416, 1200])])\n"
        "  ]\n"
        ")\n"
    )


def rodar_pyinstaller() -> None:
    shutil.rmtree(DIST, ignore_errors=True)
    ambiente = dict(os.environ)
    if sys.platform.startswith("win"):
        SAIDA.mkdir(parents=True, exist_ok=True)
        propriedades = SAIDA / "propriedades-windows.txt"
        propriedades.write_text(texto_versao_windows(versao()), encoding="utf-8")
        ambiente["ROTAGUARD_VERSAO_WINDOWS"] = str(propriedades)
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST), "--workpath",
         str(TRABALHO), str(AQUI / "rotaguard-script.spec")],
        check=True,
        env=ambiente,
    )
    if not executavel().exists():
        raise SystemExit(f"PyInstaller terminou sem gerar {executavel()}")
    avisos = DIST / PASTA_APP / "_internal" / "THIRD_PARTY_NOTICES.md"
    if not avisos.exists():
        raise SystemExit(f"O pacote saiu sem {avisos.name}: as licenças de terceiros precisam ir junto (APT-21).")
    if not list((DIST / PASTA_APP / "_internal").glob("opencv_contrib_python-*.dist-info/**/LICENSE-3RD-PARTY.txt")):
        raise SystemExit("O pacote saiu sem o LICENSE-3RD-PARTY.txt da OpenCV (FFmpeg, LGPL): confira copy_metadata no .spec.")
    web = DIST / PASTA_APP / "_internal" / "tela_teste" / "web"
    faltando = [nome for nome in ("index.html", "app.css", "app.js") if not (web / nome).is_file()]
    if faltando:
        raise SystemExit(f"O pacote saiu sem a tela nova em {web} ({', '.join(faltando)}): confira datas no .spec (TEL-16).")


def video_sintetico(pasta: Path) -> Path:
    import cv2
    import numpy as np

    caminho = pasta / "fumaca.avi"
    escritor = cv2.VideoWriter(str(caminho), cv2.VideoWriter_fourcc(*"MJPG"), 15, (320, 240))
    for i in range(45):
        quadro = np.zeros((240, 320, 3), dtype=np.uint8)
        quadro[:, :, 1] = (np.arange(320) + i * 7) % 256
        cv2.circle(quadro, (40 + i * 5, 120), 30, (200, 200, 200), -1)
        escritor.write(quadro)
    escritor.release()
    return caminho


def teste_de_fumaca() -> None:
    """APT-10: o executável empacotado roda um vídeo sem janela e sem servidor, carrega os modelos e sai com 0."""
    # Como no .zip baixado do site: Python.Runtime.dll com a marca "baixado da internet". O gancho
    # rthook_desbloquear.py (o mesmo do painel) tem de tirar a marca na abertura (spec 031, qualquer computador).
    dll = DIST / PASTA_APP / "_internal" / "pythonnet" / "runtime" / "Python.Runtime.dll"
    marca = Path(f"{dll}:Zone.Identifier")
    if sys.platform.startswith("win") and dll.exists():
        marca.write_text("[ZoneTransfer]\nZoneId=3\n", encoding="ascii")
    with tempfile.TemporaryDirectory() as tmp:
        video = video_sintetico(Path(tmp))
        dados = Path(tmp) / "dados"
        comando = [str(executavel()), "--monitor", "--camera", str(video), "--no-window", "--sem-servidor",
                   "--data-dir", str(dados), "--calibration-min", "1", "--calibration-max", "2"]
        inicio = time.monotonic()
        resultado = subprocess.run(comando, timeout=600, capture_output=True, text=True, errors="replace")
        duracao = time.monotonic() - inicio
        registro_caminho = dados / "registro-teste.log"
        registro = registro_caminho.read_text(encoding="utf-8", errors="replace") if registro_caminho.exists() else ""
        falhas = []
        if resultado.returncode != 0:
            falhas.append(f"código de saída {resultado.returncode}")
        if "Monitoramento finalizado" not in registro:
            falhas.append('o registro não tem "Monitoramento finalizado"')
        if "Traceback" in registro or "Traceback" in resultado.stderr:
            falhas.append("houve Traceback")
        if "Detecção de celular desligada" in registro:
            falhas.append("o modelo do celular ou das mãos não carregou no pacote")
        if "Servidor inacess" in registro:
            falhas.append("tentou falar com servidor mesmo com --sem-servidor")
        if sys.platform.startswith("win") and dll.exists() and marca.exists():
            falhas.append("o Python.Runtime.dll continuou marcado como baixado da internet")
        print(f"Teste de fumaça: {duracao:.1f} s, {len(registro.splitlines())} linhas de registro.")
        if falhas:
            print("\n".join(registro.splitlines()[-40:]))
            print(resultado.stdout[-2000:], resultado.stderr[-2000:])
            raise SystemExit("Teste de fumaça falhou: " + "; ".join(falhas))
        print("Teste de fumaça OK.")


def teste_sem_camera() -> None:
    """APT-20: câmera que não existe → código 3 e aviso no registro, sem esperar a espera inteira nem Traceback."""
    with tempfile.TemporaryDirectory() as tmp:
        dados = Path(tmp) / "dados"
        comando = [str(executavel()), "--monitor", "--camera", "9", "--espera-camera", "60", "--no-window",
                   "--sem-servidor", "--sem-celular", "--mute", "--data-dir", str(dados)]
        inicio = time.monotonic()
        resultado = subprocess.run(comando, timeout=300, capture_output=True, text=True, errors="replace")
        duracao = time.monotonic() - inicio
        registro_caminho = dados / "registro-teste.log"
        registro = registro_caminho.read_text(encoding="utf-8", errors="replace") if registro_caminho.exists() else ""
        falhas = []
        if resultado.returncode != 3:
            falhas.append(f"código de saída {resultado.returncode} (esperado 3)")
        if "não abriu" not in registro:
            falhas.append('o registro não explica que a câmera "não abriu"')
        if "Traceback" in registro or "Traceback" in resultado.stderr:
            falhas.append("houve Traceback")
        if duracao >= 60:
            falhas.append(f"demorou {duracao:.0f} s: esperou a espera inteira")
        print(f"Teste sem câmera: {duracao:.1f} s, código {resultado.returncode}.")
        if falhas:
            print("\n".join(registro.splitlines()[-40:]))
            raise SystemExit("Teste sem câmera falhou: " + "; ".join(falhas))
        print("Teste sem câmera OK.")


def teste_da_tela() -> None:
    """TEL-16: a tela nova (spec 023) sobe no pacote. O executável roda --verificar-tela: servidor em 127.0.0.1 sem
    janela, página, CSS, JS e /estado respondendo, e 403 sem o token. Não abre câmera."""
    with tempfile.TemporaryDirectory() as tmp:
        dados = Path(tmp) / "RotaGuard" / "Teste"
        comando = [str(executavel()), "--verificar-tela", "--data-dir", str(dados)]
        inicio = time.monotonic()
        resultado = subprocess.run(comando, timeout=300, capture_output=True, text=True, errors="replace")
        duracao = time.monotonic() - inicio
        registro_caminho = dados / "registro-teste.log"
        registro = registro_caminho.read_text(encoding="utf-8", errors="replace") if registro_caminho.exists() else ""
        falhas = []
        if resultado.returncode != 0:
            falhas.append(f"código de saída {resultado.returncode}")
        if "Verificação da tela OK" not in registro:
            falhas.append('o registro não tem "Verificação da tela OK"')
        if "Traceback" in registro or "Traceback" in resultado.stderr:
            falhas.append("houve Traceback")
        print(f"Teste da tela (tela_teste): {duracao:.1f} s, código {resultado.returncode}.")
        if falhas:
            print("\n".join(registro.splitlines()[-40:]))
            print(resultado.stdout[-2000:], resultado.stderr[-2000:])
            raise SystemExit("Teste da tela falhou: " + "; ".join(falhas))
        print("Teste da tela OK.")


def iscc() -> Path | None:
    candidatos = [os.environ.get("ISCC"), shutil.which("iscc"), r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                  r"C:\Program Files\Inno Setup 6\ISCC.exe",
                  # winget install JRSoftware.InnoSetup --scope user (sem administrador) instala aqui
                  str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe")]
    for candidato in candidatos:
        if candidato and Path(candidato).exists():
            return Path(candidato)
    return None


def empacotar(sem_instalador: bool) -> list[Path]:
    PACOTES.mkdir(parents=True, exist_ok=True)
    gerados: list[Path] = []
    destino = alvo()
    if sys.platform.startswith("win"):
        zip_caminho = PACOTES / f"{NOME}-{destino}.zip"
        with zipfile.ZipFile(zip_caminho, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as arquivo:
            for item in sorted((DIST / PASTA_APP).rglob("*")):
                arquivo.write(item, Path("RotaGuard Script") / item.relative_to(DIST / PASTA_APP))
        gerados.append(zip_caminho)
        compilador = iscc()
        if compilador is None:
            if os.environ.get("CI") and not sem_instalador:
                raise SystemExit("Inno Setup (ISCC.exe) não encontrado no CI.")
            print("Inno Setup não encontrado: instalador .exe não gerado (só o .zip).")
        elif not sem_instalador:
            subprocess.run([str(compilador), f"/DVersao={versao()}", f"/DOrigem={DIST / PASTA_APP}",
                            f"/DSaida={PACOTES}", str(AQUI / "rotaguard-script.iss")], check=True)
            gerados.append(PACOTES / f"{NOME}-{destino}-setup.exe")
    else:
        tar_caminho = PACOTES / f"{NOME}-{destino}.tar.gz"
        with tarfile.open(tar_caminho, "w:gz") as arquivo:
            arquivo.add(DIST / PASTA_APP, arcname=PASTA_APP)
        gerados.append(tar_caminho)
    return gerados


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def carimbo(produto: str, numero: str) -> str:
    """Identificação única do build (20/10/2026: "o executável que está no site eu não acho que está com a mesma versão
    que está nesse computador"): versão, commit e hora. "+local" quando havia mudança sem commit no código empacotado."""
    try:
        commit = subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, check=False).stdout.strip()
        mudancas = subprocess.run(["git", "-C", str(RAIZ), "status", "--porcelain", "--", "caixa", "painel",
                                   "implantacao"], capture_output=True, text=True, check=False).stdout.strip()
    except OSError:
        commit, mudancas = "", ""
    identificacao = (commit or "sem-git") + ("+local" if mudancas else "")
    return f"{produto} {numero} · compilação {identificacao} · {time.strftime('%d/%m/%Y %H:%M')}"


def gravar_carimbo(pasta: Path, produto: str, numero: str) -> str:
    """versao.txt ao lado do executável: o app mostra a linha e o site publica a mesma, para comparar."""
    texto = carimbo(produto, numero)
    (Path(pasta) / "versao.txt").write_text(texto + "\n", encoding="utf-8")
    print(f"Carimbo: {texto}")
    return texto


def main() -> int:
    parser = argparse.ArgumentParser(description="Monta o RotaGuard Script para download.")
    parser.add_argument("--sem-fumaca", action="store_true", help="não roda o teste de fumaça")
    parser.add_argument("--sem-instalador", action="store_true", help="no Windows, gera só o .zip")
    parser.add_argument("--so-empacotar", action="store_true", help="reaproveita o dist/ existente")
    args = parser.parse_args()
    if sys.platform == "darwin":
        raise SystemExit("Sem versão para Mac: o RotaGuard Script é só para Windows e Linux (decisão de 14/09/2026).")
    print(f"RotaGuard Script {versao()} · {alvo()} · Python {platform.python_version()}")
    if not args.so_empacotar:
        rodar_pyinstaller()
    gravar_carimbo(DIST / PASTA_APP, "RotaGuard Script", versao())
    if not args.sem_fumaca:
        teste_de_fumaca()
        teste_sem_camera()
        teste_da_tela()
    for pacote in empacotar(args.sem_instalador):
        print(f"{pacote.name}  {pacote.stat().st_size / 1_048_576:.0f} MB  sha256 {sha256(pacote)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
