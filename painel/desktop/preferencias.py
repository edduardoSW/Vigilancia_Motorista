"""Preferências por pessoa do painel (spec 019, decisões 3 e 4): tema e lista ou cards em cada tela.

Módulo puro (sem pywebview). Uma linha por pessoa na tabela `preferencias`, com os valores completos em JSON. O tema
salvo também fica na meta `tema_ultimo`, que vale na tela de entrar (antes de alguém entrar). Não gera linha no registro
de atividades: é gosto de cada pessoa, não ação sobre dados da empresa.
"""
from __future__ import annotations

import copy
import json

from dados import Banco, ErroPainel

TEMAS = ("claro", "escuro", "sistema")
VISOES = ("lista", "cards")
TELAS = ("viagens", "momentos", "motoristas", "veiculos", "caixas", "equipe")
PADRAO = {"tema": "claro", "visao": {tela: "cards" for tela in TELAS}}
CHAVE_TEMA_ULTIMO = "tema_ultimo"


def padrao() -> dict:
    return copy.deepcopy(PADRAO)


def _limpar(guardado) -> dict:
    """Valores lidos do banco: o que estiver fora do contrato volta ao padrão, sem derrubar o estado()."""
    resultado = padrao()
    if not isinstance(guardado, dict):
        return resultado
    if guardado.get("tema") in TEMAS:
        resultado["tema"] = guardado["tema"]
    visao = guardado.get("visao")
    if isinstance(visao, dict):
        for tela in TELAS:
            if visao.get(tela) in VISOES:
                resultado["visao"][tela] = visao[tela]
    return resultado


def validar(valores) -> dict:
    """Confere tudo antes de gravar. Devolve só as mudanças pedidas (tema e/ou visão parcial)."""
    if not isinstance(valores, dict):
        raise ErroPainel("Preferências inválidas.", "invalido")
    for chave in valores:
        if chave not in ("tema", "visao"):
            raise ErroPainel("Preferência desconhecida.", "invalido", str(chave))
    mudancas: dict = {}
    if "tema" in valores:
        if not isinstance(valores["tema"], str) or valores["tema"] not in TEMAS:
            raise ErroPainel("Escolha o tema claro, escuro ou igual ao Windows.", "invalido", "tema")
        mudancas["tema"] = valores["tema"]
    if "visao" in valores:
        visao = valores["visao"]
        if not isinstance(visao, dict):
            raise ErroPainel("Escolha lista ou cards.", "invalido", "visao")
        for tela, escolha in visao.items():
            if tela not in TELAS:
                raise ErroPainel("Esta tela não tem lista e cards.", "invalido", f"visao.{tela}")
            if not isinstance(escolha, str) or escolha not in VISOES:
                raise ErroPainel("Escolha lista ou cards.", "invalido", f"visao.{tela}")
        mudancas["visao"] = dict(visao)
    return mudancas


class Preferencias:
    def __init__(self, banco: Banco):
        self.banco = banco

    def ler(self, usuario_id: int) -> dict:
        linha = self.banco.um("SELECT valores FROM preferencias WHERE usuario_id = ?", (usuario_id,))
        if linha is None:
            return padrao()
        try:
            return _limpar(json.loads(linha["valores"]))
        except (TypeError, ValueError):
            return padrao()

    def tema_ultimo(self) -> str:
        tema = self.banco.meta_ler(CHAVE_TEMA_ULTIMO)
        return tema if tema in TEMAS else PADRAO["tema"]

    def salvar(self, usuario_id: int, valores) -> dict:
        mudancas = validar(valores)
        with self.banco.transacao():
            linha = self.banco.um("SELECT valores FROM preferencias WHERE usuario_id = ?", (usuario_id,))
            novo = self.ler(usuario_id)
            if "tema" in mudancas:
                novo["tema"] = mudancas["tema"]
            novo["visao"].update(mudancas.get("visao", {}))
            texto = json.dumps(novo, ensure_ascii=False)
            # Compara com o texto guardado (não com o lido e limpo): valor estragado no banco é regravado certo.
            if linha is None and mudancas:
                self.banco.inserir("preferencias", {"usuario_id": usuario_id, "valores": texto})
            elif linha is not None and linha["valores"] != texto:
                self.banco.atualizar("preferencias", "usuario_id", usuario_id, {"valores": texto})
            if "tema" in mudancas and self.banco.meta_ler(CHAVE_TEMA_ULTIMO) != mudancas["tema"]:
                self.banco.meta_gravar(CHAVE_TEMA_ULTIMO, mudancas["tema"])
        return self.ler(usuario_id)
