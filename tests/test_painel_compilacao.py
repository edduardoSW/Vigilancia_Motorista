"""Linha de compilação do painel (pedido do Matheus em 20/10/2026: "o executável que está no site eu não acho que está
com a mesma versão que está nesse computador").

O build grava `versao.txt` ao lado do `RotaGuardPainel.exe` com uma linha como
"RotaGuard Painel 0.1.0 · compilação e94ca11 · 20/10/2026 13:10". A Ponte devolve essa linha em `estado().compilacao`
(None fora do pacote ou sem o arquivo) e a tela mostra em Configurações › Sobre e no rodapé da tela de entrada.
Rodar: python tests/test_painel_compilacao.py
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))

import ponte as ponte_mod  # noqa: E402

checks = 0
LINHA = "RotaGuard Painel 0.1.0 · compilação e94ca11 · 20/10/2026 13:10"


def ok(mensagem):
    global checks
    checks += 1
    print(f"OK {checks:02d} {mensagem}")


# CMP-01 · fora do pacote (python rotaguard_painel.py), nada a mostrar
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    exe = Path(tmp) / "RotaGuardPainel.exe"
    (Path(tmp) / "versao.txt").write_text(LINHA, encoding="utf-8")
    assert ponte_mod.compilacao_do_pacote(congelado=False, executavel=str(exe)) is None
ok("CMP-01 fora do pacote congelado: compilacao None, mesmo com versao.txt por perto")

# CMP-02 · no pacote, a primeira linha do versao.txt ao lado do executável (com BOM, CRLF e linhas a mais)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    exe = Path(tmp) / "RotaGuardPainel.exe"
    (Path(tmp) / "versao.txt").write_bytes(("﻿\r\n  " + LINHA + "  \r\noutra linha\r\n").encode("utf-8"))
    assert ponte_mod.compilacao_do_pacote(congelado=True, executavel=str(exe)) == LINHA
ok("CMP-02 no pacote: a linha do versao.txt ao lado do executável, sem BOM, espaços nem as linhas seguintes")

# CMP-03 · leitura segura: sem o arquivo, pasta no lugar do arquivo, bytes inválidos ou arquivo enorme não quebram
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    exe = Path(tmp) / "RotaGuardPainel.exe"
    assert ponte_mod.compilacao_do_pacote(congelado=True, executavel=str(exe)) is None
    (Path(tmp) / "versao.txt").mkdir()
    assert ponte_mod.compilacao_do_pacote(congelado=True, executavel=str(exe)) is None
    (Path(tmp) / "versao.txt").rmdir()
    (Path(tmp) / "versao.txt").write_bytes(b"\xff\xfe\x00RotaGuard\x07 Painel\x00")
    lida = ponte_mod.compilacao_do_pacote(congelado=True, executavel=str(exe))
    assert lida is None or (isinstance(lida, str) and all(c.isprintable() for c in lida)), repr(lida)
    (Path(tmp) / "versao.txt").write_text("x" * 5000, encoding="utf-8")
    assert len(ponte_mod.compilacao_do_pacote(congelado=True, executavel=str(exe))) <= 200
    (Path(tmp) / "versao.txt").write_text("\n\n   \n", encoding="utf-8")
    assert ponte_mod.compilacao_do_pacote(congelado=True, executavel=str(exe)) is None
ok("CMP-03 sem versao.txt, pasta no lugar, bytes inválidos, linha enorme ou vazio: None ou texto curto, sem exceção")

# CMP-04 · a Ponte devolve a linha no estado(), antes e depois de ativar
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ponte = ponte_mod.Ponte(pasta=str(Path(tmp) / "dados"), custo_scrypt=(2**14, 8, 1))
    estado = ponte.estado()
    assert estado["ok"] is True and "compilacao" in estado["dados"], estado
    assert estado["dados"]["compilacao"] is None, "nos testes o Python não está congelado"
    pacote = Path(tmp) / "pacote"
    pacote.mkdir()
    (pacote / "versao.txt").write_text(LINHA + "\n", encoding="utf-8")
    antes = (getattr(sys, "frozen", None), sys.executable)
    sys.frozen = True
    sys.executable = str(pacote / "RotaGuardPainel.exe")
    try:
        assert ponte.estado()["dados"]["compilacao"] == LINHA
        ponte.ativar_local("Viação Teste", {"nome": "Ana", "usuario": "ana", "senha": "uma-senha-longa-123"}, {})
        assert ponte.estado()["dados"]["compilacao"] == LINHA
    finally:
        if antes[0] is None:
            del sys.frozen
        else:
            sys.frozen = antes[0]
        sys.executable = antes[1]
ok("CMP-04 Ponte.estado() traz compilacao: None fora do pacote, a linha do versao.txt no pacote")

# CMP-05 · contrato e telas: tipo Estado, demonstração de teste, Configurações › Sobre e rodapé da entrada
app = RAIZ / "painel" / "app"
bridge = (app / "src" / "lib" / "bridge.ts").read_text(encoding="utf-8")
corpo = bridge[bridge.index("export interface Estado"):]
corpo = corpo[:corpo.index("\n}")]
assert "compilacao: string | null;" in corpo, "Estado.compilacao no bridge.ts"
demo = (app / "scripts" / "testes" / "fixtures" / "demo-backend.ts").read_text(encoding="utf-8")
assert "compilacao: null," in demo, "a demonstração de teste devolve compilacao"
sobre = (app / "src" / "components" / "settings" / "about-section.tsx").read_text(encoding="utf-8")
assert "estado?.compilacao" in sobre and "Compilação" in sobre, "Configurações › Sobre mostra a compilação"
entrada = (app / "src" / "components" / "auth-gate.tsx").read_text(encoding="utf-8")
assert "compilacao={estado?.compilacao ?? null}" in entrada and "compilacao ??" in entrada, "rodapé da entrada"
contrato = (RAIZ / "docs" / "painel" / "contrato-painel.md").read_text(encoding="utf-8")
assert "compilacao: string | null" in contrato and "versao.txt" in contrato
ok("CMP-05 bridge.ts, demonstração de teste, Sobre, rodapé da entrada e contrato-painel.md com a compilação")

print(f"\n{checks} verificações OK")
