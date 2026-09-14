"""Registro de atividades do painel (spec 014, decisão 11): só acrescenta e cada linha leva o hash da anterior.

SHA-256 sobre um JSON canônico da linha junto do hash da anterior. Gatilhos do SQLite recusam UPDATE e DELETE; quem
apagar os gatilhos e mexer no arquivo é pego por `verificar()` (cadeia quebrada ou total/último hash diferentes do
guardado em `meta`).
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from dados import Banco, novo_uid

GENESE = "0" * 64
CHAVE_META = "atividades_ultimo"
LIMITE_PADRAO, LIMITE_MAXIMO = 500, 5000


def _hash(anterior: str, linha: dict) -> str:
    campos = [anterior, linha["uid"], linha["em"], linha["usuario_id"], linha["usuario"], linha["acao"], linha["alvo"],
              linha["detalhe"]]
    texto = json.dumps(campos, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _texto(valor, limite: int = 300) -> str | None:
    if valor is None:
        return None
    return str(valor)[:limite]


class Atividades:
    def __init__(self, banco: Banco):
        self.banco = banco

    def registrar(self, acao: str, usuario: dict | None = None, alvo=None, detalhe=None) -> dict:
        with self.banco.transacao():
            ultimo = self.banco.um("SELECT hash FROM atividades ORDER BY id DESC LIMIT 1")
            anterior = ultimo["hash"] if ultimo else GENESE
            em = self.banco.agora()
            linha = {"uid": novo_uid(), "em": em, "usuario_id": usuario["id"] if usuario else None,
                     "usuario": usuario["nome"] if usuario else None, "acao": acao, "alvo": _texto(alvo),
                     "detalhe": _texto(detalhe, 1000)}
            linha["hash"] = _hash(anterior, linha)
            novo_id = self.banco.inserir("atividades", {**linha, "criado_em": em, "alterado_em": em,
                                                        "hash_anterior": anterior})
            total = self.banco.um("SELECT COUNT(*) AS n FROM atividades")["n"]
            self.banco.meta_gravar(CHAVE_META, f"{total}:{linha['hash']}")
        return {"id": novo_id, "em": em, "usuario": linha["usuario"], "acao": acao, "alvo": linha["alvo"],
                "detalhe": linha["detalhe"]}

    def verificar(self) -> bool:
        anterior, total = GENESE, 0
        for linha in self.banco.todos("SELECT * FROM atividades ORDER BY id"):
            if linha["hash_anterior"] != anterior or _hash(anterior, dict(linha)) != linha["hash"]:
                return False
            anterior, total = linha["hash"], total + 1
        guardado = self.banco.meta_ler(CHAVE_META)
        if guardado is None:
            return total == 0
        return guardado == f"{total}:{anterior}"

    def listar(self, usuario_id=None, de=None, ate=None, limite=None) -> list[dict]:
        condicoes, parametros = [], []
        if usuario_id is not None:
            condicoes.append("usuario_id = ?")
            parametros.append(int(usuario_id))
        if de:
            condicoes.append("em >= ?")
            parametros.append(str(de) + ("T00:00:00Z" if len(str(de)) == 10 else ""))
        if ate:
            condicoes.append("em <= ?")
            parametros.append(str(ate) + ("T23:59:59Z" if len(str(ate)) == 10 else ""))
        limite = max(1, min(int(limite or LIMITE_PADRAO), LIMITE_MAXIMO))
        onde = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""
        linhas = self.banco.todos(f"SELECT * FROM atividades {onde} ORDER BY id DESC LIMIT ?", (*parametros, limite))
        return [{"id": l["id"], "em": l["em"], "usuario": l["usuario"], "acao": l["acao"], "alvo": l["alvo"],
                 "detalhe": l["detalhe"]} for l in linhas]

    def exportar_csv(self, destino: Path | str) -> int:
        """CSV com ; e BOM (abre direto no Excel em pt-BR). Devolve o número de linhas."""
        linhas = self.banco.todos("SELECT * FROM atividades ORDER BY id")
        destino = Path(destino)
        with destino.open("w", encoding="utf-8-sig", newline="") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")
            escritor.writerow(["id", "quando (UTC)", "quem", "o quê", "em quê", "detalhe", "hash"])
            for l in linhas:
                escritor.writerow([l["id"], l["em"], l["usuario"] or "", l["acao"], l["alvo"] or "", l["detalhe"] or "",
                                   l["hash"]])
        return len(linhas)
