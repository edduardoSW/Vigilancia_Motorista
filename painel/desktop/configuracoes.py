"""Configurações do painel (spec 016). Módulo puro: valores com validação e trava de lei.

Toda mudança vai para o registro de atividades com o valor antigo e o novo (CFG-02).
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta

from atividades import Atividades
from dados import Banco, ErroPainel

PADRAO = {
    "empresa": {"nome": "", "razao_social": "", "cnpj": "", "telefone": "", "endereco": ""},
    "regras": {"direcao_continua_min": 330},
    "guarda": {"videos_dias": 30, "registros_anos": 5, "desligados_anos": 5},
    "acesso": {"bloqueio_min": 15},
    "aparencia": {"texto_maior": False},
}
OPCOES_VIDEOS_DIAS = (7, 15, 30, 60, 90)
OPCOES_ANOS = (1, 2, 5)
DIRECAO_MINIMA_MIN, DIRECAO_MAXIMA_MIN = 60, 330
BLOQUEIO_MINIMO_MIN, BLOQUEIO_MAXIMO_MIN = 5, 60
MENSAGEM_LEI = "O máximo é 5 h 30, pela lei (CTB, art. 67-C)"


def _inteiro(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def formatar_minutos(minutos: int) -> str:
    horas, resto = divmod(int(minutos), 60)
    return f"{horas} h" if resto == 0 else f"{horas} h {resto:02d}"


def cnpj_valido(cnpj) -> bool:
    digitos = "".join(c for c in cnpj if c.isdigit()) if isinstance(cnpj, str) else ""
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False
    for tamanho in (12, 13):
        pesos = list(range(tamanho - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d) * p for d, p in zip(digitos[:tamanho], pesos))
        dv = 0 if soma % 11 < 2 else 11 - soma % 11
        if dv != int(digitos[tamanho]):
            return False
    return True


def _texto(valor, limite: int, campo: str, mensagem: str, obrigatorio: bool = False) -> str:
    if not isinstance(valor, str) or len(valor.strip()) > limite or (obrigatorio and not valor.strip()):
        raise ErroPainel(mensagem, "invalido", campo)
    return valor.strip()


def validar(secao: str, valores: dict) -> dict:
    if secao == "empresa":
        cnpj = _texto(valores["cnpj"], 20, "cnpj", "CNPJ inválido. Confira os números.")
        if cnpj:
            if not cnpj_valido(cnpj):
                raise ErroPainel("CNPJ inválido. Confira os números.", "invalido", "cnpj")
            d = "".join(c for c in cnpj if c.isdigit())
            cnpj = f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        return {"nome": _texto(valores["nome"], 120, "nome", "Informe o nome da empresa.", obrigatorio=True),
                "razao_social": _texto(valores["razao_social"], 160, "razao_social", "Razão social muito longa."),
                "cnpj": cnpj,
                "telefone": _texto(valores["telefone"], 30, "telefone", "Telefone inválido."),
                "endereco": _texto(valores["endereco"], 200, "endereco", "Endereço muito longo.")}
    if secao == "regras":
        minutos = valores["direcao_continua_min"]
        if not _inteiro(minutos):
            raise ErroPainel("Informe o limite em minutos.", "invalido", "direcao_continua_min")
        if minutos > DIRECAO_MAXIMA_MIN:
            raise ErroPainel(MENSAGEM_LEI, "invalido", "direcao_continua_min")
        if minutos < DIRECAO_MINIMA_MIN:
            raise ErroPainel("O mínimo é 1 h.", "invalido", "direcao_continua_min")
        return {"direcao_continua_min": minutos}
    if secao == "guarda":
        if valores["videos_dias"] not in OPCOES_VIDEOS_DIAS or not _inteiro(valores["videos_dias"]):
            raise ErroPainel("Escolha 7, 15, 30, 60 ou 90 dias.", "invalido", "videos_dias")
        for campo in ("registros_anos", "desligados_anos"):
            if valores[campo] not in OPCOES_ANOS or not _inteiro(valores[campo]):
                raise ErroPainel("Escolha 1, 2 ou 5 anos.", "invalido", campo)
        return {campo: valores[campo] for campo in PADRAO["guarda"]}
    if secao == "acesso":
        minutos = valores["bloqueio_min"]
        if not _inteiro(minutos) or not BLOQUEIO_MINIMO_MIN <= minutos <= BLOQUEIO_MAXIMO_MIN:
            raise ErroPainel("Escolha de 5 a 60 minutos.", "invalido", "bloqueio_min")
        return {"bloqueio_min": minutos}
    if secao == "aparencia":
        if not isinstance(valores["texto_maior"], bool):
            raise ErroPainel("Valor inválido.", "invalido", "texto_maior")
        return {"texto_maior": valores["texto_maior"]}
    raise ErroPainel("Seção de configurações desconhecida.", "invalido", "secao")


def videos_vencidos(videos, agora_iso: str, videos_dias: int) -> list[dict]:
    """CFG-06/07 (regra pura): vídeos coletados antes do prazo saem, menos os marcados "em apuração".

    Apagar o arquivo e registrar a contagem na abertura fica para quando os vídeos chegarem ao banco do painel.
    """
    limite = datetime.fromisoformat(agora_iso.replace("Z", "+00:00")) - timedelta(days=videos_dias)
    vencidos = []
    for video in videos:
        coletado = datetime.fromisoformat(video["coletado_em"].replace("Z", "+00:00"))
        if coletado < limite and not video.get("em_apuracao"):
            vencidos.append({"id": video["id"], "apagado_em": agora_iso, "motivo": f"prazo de {videos_dias} dias"})
    return vencidos


def _formatar(campo: str, valor) -> str:
    if campo == "direcao_continua_min":
        return formatar_minutos(valor)
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if valor == "":
        return "(vazio)"
    return str(valor)


class Configuracoes:
    def __init__(self, banco: Banco, atividades: Atividades):
        self.banco, self.atividades = banco, atividades

    def iniciar(self, nome_empresa: str) -> None:
        with self.banco.transacao():
            for secao, valores in PADRAO.items():
                if secao == "empresa":
                    valores = {**valores, "nome": nome_empresa}
                if not self.banco.um("SELECT 1 FROM configuracoes WHERE secao = ?", (secao,)):
                    self.banco.inserir("configuracoes", {"secao": secao, "valores": json.dumps(valores, ensure_ascii=False)})

    def ler(self) -> dict:
        resultado = copy.deepcopy(PADRAO)
        for linha in self.banco.todos("SELECT secao, valores FROM configuracoes"):
            if linha["secao"] in resultado:
                guardado = json.loads(linha["valores"])
                resultado[linha["secao"]].update({k: v for k, v in guardado.items() if k in resultado[linha["secao"]]})
        return resultado

    def bloqueio_min(self) -> int:
        try:
            return int(self.ler()["acesso"]["bloqueio_min"])
        except Exception:  # banco ilegível não pode desligar o bloqueio
            return PADRAO["acesso"]["bloqueio_min"]

    def regra_para_importacao(self) -> dict:
        """CFG-04: a viagem importada guarda uma cópia da regra; mudar a configuração depois não muda a cópia."""
        return {"direcao_continua_min": self.ler()["regras"]["direcao_continua_min"]}

    def salvar(self, secao, valores, quem: dict) -> dict:
        if secao not in PADRAO:
            raise ErroPainel("Seção de configurações desconhecida.", "invalido", "secao")
        if not isinstance(valores, dict) or not valores:
            raise ErroPainel("Nada para salvar.", "invalido")
        desconhecidos = [campo for campo in valores if campo not in PADRAO[secao]]
        if desconhecidos:
            raise ErroPainel("Campo desconhecido nesta seção.", "invalido", desconhecidos[0])
        atual = self.ler()[secao]
        novo = validar(secao, {**atual, **valores})
        mudancas = [(campo, atual[campo], novo[campo]) for campo in PADRAO[secao] if atual[campo] != novo[campo]]
        if mudancas:
            with self.banco.transacao():
                texto = json.dumps(novo, ensure_ascii=False)
                if self.banco.um("SELECT 1 FROM configuracoes WHERE secao = ?", (secao,)):
                    self.banco.atualizar("configuracoes", "secao", secao, {"valores": texto})
                else:
                    self.banco.inserir("configuracoes", {"secao": secao, "valores": texto})
                for campo, antigo, valor in mudancas:
                    self.atividades.registrar("mudou configuração", quem, alvo=f"{secao}.{campo}",
                                              detalhe=f"{_formatar(campo, antigo)} → {_formatar(campo, valor)}")
        return self.ler()
