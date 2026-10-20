"""Contrato entre as telas (painel/app/src/lib/bridge.ts) e a ponte Python (painel/desktop/ponte.py).

ATV-01 (20/10/2026): no computador de outra pessoa, "Ativar o painel" mostrava "Algo deu errado". A tela chamava
`ativar_local(empresa, admin, opcoes)` com 3 argumentos e a Ponte aceitava 2: o pywebview repassava os 3, o Python dava
TypeError e o erro virava a mensagem genérica. Os testes antigos chamavam a Ponte direto, com 2 argumentos.

Este teste lê a interface `Api` do bridge.ts e confere, para todo método, que a Ponte aceita o número de argumentos
que a tela pode mandar. Rodar: python tests/test_painel_contrato.py
"""
import inspect
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))

import ponte as ponte_mod  # noqa: E402

checks = 0


def ok(mensagem):
    global checks
    checks += 1
    print(f"OK {checks:02d} {mensagem}")


def metodos_da_api(texto: str) -> dict[str, int]:
    """nome → número máximo de argumentos, lido do `export interface Api { ... }` do bridge.ts."""
    inicio = texto.index("export interface Api")
    corpo = texto[texto.index("{", inicio) + 1:]
    nivel, fim = 1, 0
    for i, letra in enumerate(corpo):
        nivel += {"{": 1, "}": -1}.get(letra, 0)
        if nivel == 0:
            fim = i
            break
    corpo = corpo[:fim]
    metodos = {}
    for casamento in re.finditer(r"^\s*([a-z_]+)\((.*?)\)\s*:", corpo, re.MULTILINE | re.DOTALL):
        nome, parametros = casamento.group(1), casamento.group(2)
        nivel, partes, atual = 0, [], ""
        for letra in parametros:
            nivel += {"<": 1, "{": 1, "(": 1, "[": 1, ">": -1, "}": -1, ")": -1, "]": -1}.get(letra, 0)
            if letra == "," and nivel == 0:
                partes.append(atual)
                atual = ""
            else:
                atual += letra
        if atual.strip():
            partes.append(atual)
        metodos[nome] = len(partes)
    return metodos


api = metodos_da_api((RAIZ / "painel" / "app" / "src" / "lib" / "bridge.ts").read_text(encoding="utf-8"))
assert len(api) >= 30, f"interface Api lida pela metade: {sorted(api)}"
assert api.get("ativar_local") == 3 and api.get("ativar_com_arquivo") == 3, api

faltando, curtos = [], []
for nome, quantos in sorted(api.items()):
    metodo = getattr(ponte_mod.Ponte, nome, None)
    if metodo is None:
        faltando.append(nome)
        continue
    parametros = [p for p in inspect.signature(metodo).parameters.values() if p.name != "self"]
    if any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in parametros):
        continue
    if len(parametros) < quantos:
        curtos.append(f"{nome}: a tela manda até {quantos}, a Ponte aceita {len(parametros)}")
assert not faltando, f"métodos do contrato sem Ponte: {faltando}"
assert not curtos, "ATV-01 a Ponte recusa argumentos que a tela manda: " + "; ".join(curtos)
ok(f"ATV-01 os {len(api)} métodos do contrato aceitam todos os argumentos que a tela pode mandar")

# ATV-02 · o caso real: ativar como a tela do app instalado chama, com as opções de ativação no 3º argumento.
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ponte = ponte_mod.Ponte(pasta=tmp, custo_scrypt=(2**14, 8, 1))
    admin = {"nome": "Eduardo", "usuario": "edu7", "senha": "uma-senha-longa-123"}
    resposta = ponte.ativar_local("Eduardo's", admin, {})
    assert resposta["ok"] is True and resposta["dados"]["codigo_recuperacao"], resposta
    assert ponte.estado()["dados"]["ativado"] is True and not ponte._falhas, ponte._falhas
ok("ATV-02 ativar_local com o 3º argumento (opções) ativa o painel, sem erro genérico")

# ATV-03 · falha inesperada fica registrada em arquivo, com um código que a tela mostra, e nunca com a senha.
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ponte = ponte_mod.Ponte(pasta=tmp, custo_scrypt=(2**14, 8, 1))
    senha = "senha-que-nao-pode-vazar-987"

    def explodir(*_args, **_kwargs):
        raise RuntimeError("falha de teste no disco")

    ponte._n().contas.criar_admin_inicial = explodir
    resposta = ponte.ativar_local("Empresa X", {"nome": "Ana", "usuario": "ana", "senha": senha})
    assert resposta["ok"] is False, resposta
    codigo = re.search(r"código (E-[0-9A-F]{6})", resposta["erro"])
    assert codigo, resposta["erro"]
    registro = (Path(tmp) / "registro-painel.log").read_text(encoding="utf-8")
    assert codigo.group(1) in registro and "ativar_local" in registro and "RuntimeError" in registro, registro
    assert "Traceback" in registro and "falha de teste no disco" in registro, registro
    assert senha not in registro and "Empresa X" not in registro, "o registro não pode levar os argumentos"
ok("ATV-03 falha inesperada: código na tela, erro completo em registro-painel.log, sem senha nem argumentos")

print(f"\n{checks} verificações OK")
