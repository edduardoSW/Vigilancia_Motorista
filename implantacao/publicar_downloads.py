"""Copia os pacotes montados para o site e grava site/public/downloads/versoes.json (VER-01, 20/10/2026).

O descompasso entre o site e o computador que montou os apps ("o executável que está no site eu não acho que está com a
mesma versão que está nesse computador") vinha de cópia à mão. Este roteiro:
  1. confere que cada app tem o versao.txt no dist/ (gravado pelo build) e os pacotes em build/<app>/pacotes/;
  2. copia instalador (-setup.exe) e .zip de cada app para site/public/downloads/, apagando o que não é mais oferecido;
  3. grava versoes.json com a linha de compilação de cada app (o site mostra embaixo de cada download);
  4. imprime o SHA-256 de cada arquivo para conferir depois do deploy.

Rodar na raiz do repositório:  python implantacao/publicar_downloads.py
Depois: implantacao/vps/enviar.sh site  e  ./atualizar.sh site <tag> na VPS.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "site" / "public" / "downloads"
APPS = {
    # chave do site (src/content/downloads.ts) → pasta do dist, pasta de pacotes e prefixo dos arquivos
    "painel": (RAIZ / "build" / "painel" / "dist" / "RotaGuardPainel", RAIZ / "build" / "painel" / "pacotes",
               "RotaGuard-Painel-windows-x64"),
    "teste": (RAIZ / "build" / "app-teste" / "dist" / "RotaGuardScript", RAIZ / "build" / "app-teste" / "pacotes",
              "RotaGuard-Script-windows-x64"),
}


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def publicar(destino: Path = DESTINO, apps: dict = APPS) -> dict:
    destino.mkdir(parents=True, exist_ok=True)
    versoes, oferecidos = {}, set()
    for chave, (dist, pacotes, prefixo) in apps.items():
        carimbo = dist / "versao.txt"
        if not carimbo.exists():
            raise SystemExit(f"{chave}: falta {carimbo} (rode o build.py do app antes)")
        versoes[chave] = carimbo.read_text(encoding="utf-8").strip()
        arquivos = [pacotes / f"{prefixo}-setup.exe", pacotes / f"{prefixo}.zip"]
        if not arquivos[1].exists():
            raise SystemExit(f"{chave}: falta {arquivos[1]}")
        for arquivo in arquivos:
            if arquivo.exists():
                shutil.copy2(arquivo, destino / arquivo.name)
                oferecidos.add(arquivo.name)
    for velho in destino.iterdir():  # .zip antigo (RotaGuard-Teste-...) e o que não sai mais do build
        if velho.is_file() and velho.name not in oferecidos and velho.name != "versoes.json":
            velho.unlink()
            print(f"removido: {velho.name}")
    (destino / "versoes.json").write_text(json.dumps(versoes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for nome in sorted(oferecidos):
        print(f"{nome}  {sha256(destino / nome)}")
    for chave, linha in versoes.items():
        print(f"{chave}: {linha}")
    return versoes


if __name__ == "__main__":
    publicar()
    sys.exit(0)
