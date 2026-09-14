"""Monta o RotaGuard Painel (spec 013): interface → PyInstaller → verificação oculta do .exe → pacotes para download.

Uso, no Windows, com painel/desktop/requirements.txt instalado no .venv (e o Node.js para gerar a interface):
  python implantacao/painel/build.py                        interface + pacote + verificação + .zip
  python implantacao/painel/build.py --sem-build-interface  não roda npm run build: empacota o painel/app/out atual
  python implantacao/painel/build.py --sem-fumaca           pula a verificação do .exe (não usar em entrega)
  python implantacao/painel/build.py --so-empacotar         reaproveita o build/painel/dist e só gera os pacotes

Saída em build/painel/pacotes/: RotaGuard-Painel-windows-x64.zip e, com o Inno Setup instalado,
RotaGuard-Painel-windows-x64-setup.exe. Só Windows por enquanto (Linux fora do escopo da spec 013).
Versão: variável ROTAGUARD_VERSAO (tag painel-vX.Y.Z) ou "version" de painel/app/package.json.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
APP = RAIZ / "painel" / "app"
INTERFACE = APP / "out"
SAIDA = RAIZ / "build" / "painel"
DIST = SAIDA / "dist"
TRABALHO = SAIDA / "work"
PACOTES = SAIDA / "pacotes"
NOME = "RotaGuard-Painel"
PASTA_APP = "RotaGuardPainel"
PRODUTO = "RotaGuard Painel"
PORTA_DEV = 3001  # next dev --port 3001 (painel/app/package.json)
TEMPO_FUMACA_S = 120  # o próprio .exe desiste em 60 s; isto só segura um processo que nem chegou a iniciar


def _carregar_build_app_teste():
    caminho = RAIZ / "implantacao" / "app-teste" / "build.py"
    especificacao = importlib.util.spec_from_file_location("build_app_teste", caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


# Reaproveita do RotaGuard Teste (spec 010): propriedades do .exe, alvo, Inno Setup e SHA-256.
APP_TESTE = _carregar_build_app_teste()


def versao() -> str:
    bruta = os.environ.get("ROTAGUARD_VERSAO", "").strip()
    if bruta:
        return re.sub(r"^painel-v", "", bruta)
    return json.loads((APP / "package.json").read_text(encoding="utf-8"))["version"]


def alvo() -> str:
    return APP_TESTE.alvo()


def nome_zip() -> str:
    return f"{NOME}-{alvo()}.zip"


def nome_instalador() -> str:
    return f"{NOME}-{alvo()}-setup.exe"


def executavel() -> Path:
    return DIST / PASTA_APP / f"{PASTA_APP}.exe"


def propriedades_windows(numero: str) -> str:
    """Propriedades do RotaGuardPainel.exe: empresa RotaGuard, produto RotaGuard Painel, nada do computador do build."""
    return APP_TESTE.texto_versao_windows(numero, produto=PRODUTO, executavel=PASTA_APP)


def porta_ocupada(porta: int, hosts=("127.0.0.1", "::1"), espera_s: float = 1.0) -> bool:
    """True se algo aceita conexão na porta. O next dev escuta em :: e responde nos dois endereços."""
    for host in hosts:
        try:
            with socket.create_connection((host, porta), timeout=espera_s):
                return True
        except OSError:
            continue
    return False


def construir_interface() -> None:
    if porta_ocupada(PORTA_DEV):
        raise SystemExit(f"A porta {PORTA_DEV} está em uso (next dev do painel?). Buildar com ele rodando corrompe o "
                         ".next: pare o next dev ou use --sem-build-interface para empacotar o painel/app/out atual.")
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm não encontrado: instale o Node.js ou use --sem-build-interface.")
    subprocess.run([npm, "run", "build"], cwd=APP, check=True)


def conferir_interface() -> None:
    if not (INTERFACE / "index.html").is_file():
        raise SystemExit(f"Interface não encontrada em {INTERFACE}: rode npm run build em painel/app.")


def rodar_pyinstaller() -> None:
    shutil.rmtree(DIST, ignore_errors=True)
    SAIDA.mkdir(parents=True, exist_ok=True)
    propriedades = SAIDA / "propriedades-windows.txt"
    propriedades.write_text(propriedades_windows(versao()), encoding="utf-8")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST), "--workpath",
         str(TRABALHO), str(AQUI / "rotaguard-painel.spec")],
        check=True,
        env=dict(os.environ, ROTAGUARD_VERSAO_WINDOWS=str(propriedades)),
    )
    if not executavel().exists():
        raise SystemExit(f"PyInstaller terminou sem gerar {executavel()}")


def conferir_pacote() -> None:
    """PAC-14: interface, ícone e licenças do pywebview dentro do pacote."""
    internos = DIST / PASTA_APP / "_internal"
    for obrigatorio in (executavel(), internos / "interface" / "index.html", internos / "rotaguard.ico"):
        if not obrigatorio.is_file():
            raise SystemExit(f"O pacote saiu sem {obrigatorio.relative_to(DIST)}: confira o rotaguard-painel.spec.")
    if not list(internos.glob("pywebview-*.dist-info")):
        raise SystemExit("O pacote saiu sem o pywebview-*.dist-info (licença): confira copy_metadata no .spec.")
    arquivos = sum(1 for item in (internos / "interface").rglob("*") if item.is_file())
    print(f"Pacote conferido: interface com {arquivos} arquivos.")


def teste_de_fumaca() -> dict:
    """PAC-14: o .exe abre a janela oculta, carrega a interface e sai com 0 e "ok": true numa linha JSON."""
    inicio = time.monotonic()
    resultado = subprocess.run([str(executavel()), "--verificar"], capture_output=True, text=True, errors="replace",
                               timeout=TEMPO_FUMACA_S)
    duracao = time.monotonic() - inicio
    linhas = [linha.strip() for linha in resultado.stdout.splitlines() if linha.strip().startswith("{")]
    dados = json.loads(linhas[-1]) if linhas else {}
    print(f"Verificação do .exe: {duracao:.1f} s, código {resultado.returncode}.")
    print(linhas[-1] if linhas else "(nenhuma linha JSON na saída)")
    falhas = []
    if resultado.returncode != 0:
        falhas.append(f"código de saída {resultado.returncode}")
    if dados.get("ok") is not True:
        falhas.append('a linha JSON não tem "ok": true')
    if "Traceback" in resultado.stderr:
        falhas.append("houve Traceback")
    if falhas:
        print(resultado.stdout[-2000:], resultado.stderr[-2000:])
        raise SystemExit("Verificação do pacote falhou: " + "; ".join(falhas))
    print("Verificação do pacote OK.")
    return dados


def empacotar(sem_instalador: bool) -> list[Path]:
    PACOTES.mkdir(parents=True, exist_ok=True)
    zip_caminho = PACOTES / nome_zip()
    with zipfile.ZipFile(zip_caminho, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as arquivo:
        for item in sorted((DIST / PASTA_APP).rglob("*")):
            arquivo.write(item, Path(PRODUTO) / item.relative_to(DIST / PASTA_APP))
    gerados = [zip_caminho]
    if sem_instalador:
        return gerados
    compilador = APP_TESTE.iscc()
    if compilador is None:
        print("Inno Setup (ISCC.exe) não encontrado: instalador não gerado (só o .zip).")
    else:
        subprocess.run([str(compilador), f"/DVersao={versao()}", f"/DOrigem={DIST / PASTA_APP}", f"/DSaida={PACOTES}",
                        str(AQUI / "rotaguard-painel.iss")], check=True)
        gerados.append(PACOTES / nome_instalador())
    return gerados


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Monta o RotaGuard Painel (janela nativa) para download.")
    parser.add_argument("--sem-build-interface", action="store_true",
                        help="não roda npm run build: empacota o painel/app/out que já existe")
    parser.add_argument("--sem-fumaca", action="store_true", help="pula a verificação oculta do .exe")
    parser.add_argument("--sem-instalador", action="store_true", help="gera só o .zip")
    parser.add_argument("--so-empacotar", action="store_true", help="reaproveita o build/painel/dist existente")
    args = parser.parse_args(argv)
    if not sys.platform.startswith("win"):
        raise SystemExit("O RotaGuard Painel só é montado no Windows por enquanto (Linux fora do escopo da spec 013).")
    print(f"RotaGuard Painel {versao()} · {alvo()} · Python {platform.python_version()}")
    if not args.so_empacotar:
        if not args.sem_build_interface:
            construir_interface()
        conferir_interface()
        rodar_pyinstaller()
    conferir_pacote()
    if not args.sem_fumaca:
        teste_de_fumaca()
    for pacote in empacotar(args.sem_instalador):
        print(f"{pacote.name}  {pacote.stat().st_size / 1_048_576:.1f} MB  sha256 {APP_TESTE.sha256(pacote)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
