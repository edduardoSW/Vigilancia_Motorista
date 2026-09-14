"""Cadastros do painel (spec 015): motoristas, veículos e caixas; decisões de momento (spec 014, EQP-04).

Módulo puro (sem pywebview). Nada é apagado: desligado e fora de uso continuam no banco; termo de ciência só ganha
registro novo; trocar a caixa de veículo fecha o vínculo antigo e abre outro.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from atividades import Atividades
from dados import Banco, ErroPainel, novo_uid

CATEGORIAS = ("C", "D", "E")
SITUACOES_MOTORISTA = ("ativo", "afastado", "desligado")
TIPOS_VEICULO = ("onibus", "micro_onibus", "caminhao", "van")
TRANSPORTA = ("passageiros", "carga")
SITUACOES_VEICULO = ("em_uso", "oficina", "fora_de_uso")
RESULTADOS = ("confirmado", "alarme_falso")
AVISO_CNH_DIAS = 30
VERSAO_TERMO_PADRAO = "1"
MENSAGEM_TERMO = "Falta registrar o termo de ciência deste motorista."
MENSAGEM_CAIXA_BLOQUEADA = "Caixa bloqueada pela RotaGuard"
# RF-03: carga 30 min a cada 6 h; passageiros 30 min a cada 4 h.
REGRAS_DESCANSO = {"carga": {"descanso_min": 30, "a_cada_min": 360},
                   "passageiros": {"descanso_min": 30, "a_cada_min": 240}}


def _inteiro(valor, minimo=1) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= minimo


def so_digitos(valor) -> str:
    return re.sub(r"\D", "", valor) if isinstance(valor, str) else ""


# CNH, CPF, placa e nome --------------------------------------------------------------------------------------------------
def _dvs_cnh(nove: str) -> tuple[int, int]:
    soma = sum(int(d) * peso for d, peso in zip(nove, range(9, 0, -1)))
    dv1, desconto = soma % 11, 0
    if dv1 >= 10:
        dv1, desconto = 0, 2
    resto = sum(int(d) * peso for d, peso in zip(nove, range(1, 10))) % 11
    dv2 = 0 if resto >= 10 else resto - desconto
    return dv1, dv2


def cnh_valida(numero) -> bool:
    """11 dígitos com os dois dígitos verificadores (algoritmo do Denatran usado nas bibliotecas brasileiras)."""
    digitos = so_digitos(numero)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    dv1, dv2 = _dvs_cnh(digitos[:9])
    return dv2 >= 0 and digitos[9:] == f"{dv1}{dv2}"


def completar_cnh(nove: str) -> str | None:
    dv1, dv2 = _dvs_cnh(nove)
    return f"{nove}{dv1}{dv2}" if dv2 >= 0 else None


def cpf_valido(cpf) -> bool:
    digitos = so_digitos(cpf)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(digitos[i]) * (tamanho + 1 - i) for i in range(tamanho))
        if (soma * 10) % 11 % 10 != int(digitos[tamanho]):
            return False
    return True


def formatar_cpf(digitos: str) -> str:
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def mascarar_cpf(cpf) -> str | None:
    digitos = so_digitos(cpf)
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**" if len(digitos) == 11 else None


def nome_curto_sugerido(nome) -> str:
    partes = str(nome or "").split()
    if not partes:
        return ""
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[-1][0].upper()}."


_MERCOSUL = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")
_ANTIGA = re.compile(r"^([A-Z]{3})-?([0-9]{4})$")


def placa_normalizada(placa) -> str | None:
    texto = placa.strip().upper().replace(" ", "") if isinstance(placa, str) else ""
    if _MERCOSUL.match(texto):
        return texto
    antiga = _ANTIGA.match(texto)
    return f"{antiga.group(1)}-{antiga.group(2)}" if antiga else None


def data_valida(valor) -> bool:
    if not isinstance(valor, str) or len(valor) != 10:
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def aviso_cnh(validade, hoje: date) -> str | None:
    if not data_valida(validade):
        return None
    dia = date.fromisoformat(validade)
    if dia < hoje:
        return f"CNH vencida em {dia:%d/%m/%Y}"
    faltam = (dia - hoje).days
    if faltam == 0:
        return "CNH vence hoje"
    if faltam <= AVISO_CNH_DIAS:
        return f"CNH vence em {faltam} dia{'s' if faltam > 1 else ''}"
    return None


def regra_descanso(transporta: str) -> dict:
    if transporta not in REGRAS_DESCANSO:
        raise ErroPainel("Diga se o veículo leva passageiros ou carga.", "invalido", "transporta")
    return dict(REGRAS_DESCANSO[transporta])


# Demonstração ----------------------------------------------------------------------------------------------------------
DEMO_EMPRESA = "Viação Demonstração"
DEMO_MOTORISTAS = (
    ("m-01", "Carlos Menezes", "Carlos M.", "0412", "D", "2028-03-31", "2026-09-02"),
    ("m-02", "Juliana Prado", "Juliana P.", "0388", "D", "2027-11-30", "2026-09-02"),
    ("m-03", "Rogério Lima", "Rogério L.", "0291", "E", "2026-09-26", "2026-09-03"),
    ("m-04", "Aline Costa", "Aline C.", "0455", "D", "2029-06-30", "2026-09-02"),
    ("m-05", "Marcos Teixeira", "Marcos T.", "0467", "D", "2030-01-15", None),
)
DEMO_VEICULOS = (  # número, tipo, transporta, placa, caixa, modelo (descrição do demo.json)
    ("3302", "caminhao", "carga", "BRA2E19", "RG-0129", "Cavalo mecânico"),
    ("2258", "onibus", "passageiros", "BRA3F27", "RG-0139", "Rodoviário executivo"),
    ("2240", "onibus", "passageiros", "BRA1C84", "RG-0142", "Rodoviário 2 andares"),
    ("3310", "caminhao", "carga", "BRA5H02", "RG-0133", "Cavalo mecânico"),
    ("2251", "onibus", "passageiros", "BRA4D66", "RG-0150", "Rodoviário 2 andares"),
    ("2263", "onibus", "passageiros", "BRA7B31", "RG-0147", "Rodoviário leito"),
    ("1187", "onibus", "passageiros", "BRA8A12", "RG-0118", "Rodoviário executivo"),
)
DEMO_CAIXA_LIVRE = "RG-0155"
DEMO_DETALHE_RG_0129 = "A caixa esquentou demais na última viagem (passou de 70 °C). Vale conferir a instalação."


def cnh_demo(indice: int) -> str:
    """Número fictício e determinístico, válido pelo dígito verificador."""
    base = 40_000_000 + indice * 7919
    while True:
        numero = completar_cnh(f"{base:09d}")
        if numero and len(set(numero)) > 1:
            return numero
        base += 1


def carregar_demonstracao(banco: Banco) -> None:
    with banco.transacao():
        for indice, (ref, nome, curto, matricula, categoria, validade, termo) in enumerate(DEMO_MOTORISTAS, 1):
            motorista_id = banco.inserir("motoristas", {
                "ref": ref, "nome": nome, "nome_curto": curto, "matricula": matricula, "cpf": None, "telefone": None,
                "cnh_numero": cnh_demo(indice), "cnh_categoria": categoria, "cnh_validade": validade,
                "situacao": "ativo", "observacoes": None})
            if termo:
                banco.inserir("termos", {"motorista_id": motorista_id, "assinado": 1, "data": termo,
                                         "versao": VERSAO_TERMO_PADRAO, "registrado_por": "Demonstração"})
        for numero, tipo, transporta, placa, codigo, modelo in DEMO_VEICULOS:
            veiculo_id = banco.inserir("veiculos", {"numero": numero, "placa": placa, "tipo": tipo,
                                                    "transporta": transporta, "modelo": modelo, "ano": None,
                                                    "situacao": "em_uso"})
            atencao = codigo == "RG-0129"
            caixa_id = banco.inserir("caixas", {"codigo": codigo, "veiculo_id": veiculo_id,
                                                "situacao": "atencao" if atencao else "ok",
                                                "detalhe": DEMO_DETALHE_RG_0129 if atencao else None})
            banco.inserir("caixa_vinculos", {"caixa_id": caixa_id, "veiculo_id": veiculo_id, "de": banco.agora(),
                                             "ate": None, "por": "Demonstração"})
        banco.inserir("caixas", {"codigo": DEMO_CAIXA_LIVRE, "veiculo_id": None, "situacao": "ok", "detalhe": None})


def carregar_caixas_do_arquivo(banco: Banco, caixas: list[dict]) -> None:
    """CXA-01: as caixas só nascem aqui, a partir do arquivo da empresa."""
    with banco.transacao():
        for caixa in caixas:
            bloqueada = caixa["revogada_em"] is not None
            banco.inserir("caixas", {"codigo": caixa["codigo"], "veiculo_id": None,
                                     "situacao": "bloqueada" if bloqueada else "ok",
                                     "detalhe": MENSAGEM_CAIXA_BLOQUEADA if bloqueada else None,
                                     "dispositivo_id": caixa["dispositivo_id"], "geracao": caixa["geracao"],
                                     "revogada_em": caixa["revogada_em"]})


# Cadastros -------------------------------------------------------------------------------------------------------------
def _texto_opcional(valor, limite: int, campo: str, mensagem: str) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ErroPainel(mensagem, "invalido", campo)
    texto = valor.strip()
    if len(texto) > limite:
        raise ErroPainel(mensagem, "invalido", campo)
    return texto or None


class Cadastros:
    def __init__(self, banco: Banco, atividades: Atividades, hoje=date.today):
        self.banco, self.atividades, self.hoje = banco, atividades, hoje

    # Motoristas ----------------------------------------------------------------------------------------------------
    def termo_atual(self, motorista_id: int) -> dict:
        linha = self.banco.um("SELECT * FROM termos WHERE motorista_id = ? ORDER BY id DESC LIMIT 1", (motorista_id,))
        if linha is None or not linha["assinado"]:
            return {"assinado": False, "data": None, "versao": None}
        return {"assinado": True, "data": linha["data"], "versao": linha["versao"]}

    def termos_historico(self, motorista_id: int) -> list[dict]:
        return [{"assinado": bool(l["assinado"]), "data": l["data"], "versao": l["versao"],
                 "registrado_por": l["registrado_por"], "registrado_em": l["criado_em"]}
                for l in self.banco.todos("SELECT * FROM termos WHERE motorista_id = ? ORDER BY id", (motorista_id,))]

    def _motorista(self, linha, mascarar: bool = True) -> dict:
        return {"id": linha["id"], "ref": linha["ref"], "nome": linha["nome"], "nome_curto": linha["nome_curto"],
                "matricula": linha["matricula"], "cpf": mascarar_cpf(linha["cpf"]) if mascarar else linha["cpf"],
                "telefone": linha["telefone"], "cnh_numero": linha["cnh_numero"],
                "cnh_categoria": linha["cnh_categoria"], "cnh_validade": linha["cnh_validade"],
                "situacao": linha["situacao"], "termo": self.termo_atual(linha["id"]),
                "observacoes": linha["observacoes"], "viagens_30d": 0, "confirmados_30d": 0,
                "aviso_cnh": aviso_cnh(linha["cnh_validade"], self.hoje())}

    def motoristas_listar(self) -> list[dict]:
        return [self._motorista(l) for l in self.banco.todos("SELECT * FROM motoristas ORDER BY nome COLLATE NOCASE")]

    def motorista_salvar(self, dados, quem: dict) -> dict:
        if not isinstance(dados, dict):
            raise ErroPainel("Preencha os dados do motorista.", "invalido", "nome")
        atual = None
        if dados.get("id") is not None:
            atual = self.banco.um("SELECT * FROM motoristas WHERE id = ?", (dados["id"],)) \
                if _inteiro(dados["id"]) else None
            if atual is None:
                raise ErroPainel("Motorista não encontrado.", "nao_encontrado")
        nome = " ".join(dados.get("nome").split()) if isinstance(dados.get("nome"), str) else ""
        if not 3 <= len(nome) <= 120:
            raise ErroPainel("Informe o nome completo.", "invalido", "nome")
        curto = dados.get("nome_curto")
        curto = " ".join(curto.split()) if isinstance(curto, str) and curto.strip() else nome_curto_sugerido(nome)
        if len(curto) > 40:
            raise ErroPainel("O nome nos relatórios pode ter até 40 letras.", "invalido", "nome_curto")
        matricula = dados.get("matricula").strip() if isinstance(dados.get("matricula"), str) else ""
        if not 1 <= len(matricula) <= 20:
            raise ErroPainel("Informe a matrícula.", "invalido", "matricula")
        cnh = so_digitos(dados.get("cnh_numero"))
        if not cnh_valida(cnh):
            raise ErroPainel("Número da CNH inválido. Confira os 11 dígitos.", "invalido", "cnh_numero")
        if dados.get("cnh_categoria") not in CATEGORIAS:
            raise ErroPainel("Escolha a categoria da CNH: C, D ou E.", "invalido", "cnh_categoria")
        if not data_valida(dados.get("cnh_validade")):
            raise ErroPainel("Informe a validade da CNH.", "invalido", "cnh_validade")
        cpf_bruto = dados.get("cpf")
        if isinstance(cpf_bruto, str) and "*" in cpf_bruto and atual is not None:
            cpf = atual["cpf"]  # a lista devolve o CPF mascarado; salvar sem mexer mantém o guardado
        elif cpf_bruto is None or (isinstance(cpf_bruto, str) and not cpf_bruto.strip()):
            cpf = None
        elif cpf_valido(cpf_bruto):
            cpf = formatar_cpf(so_digitos(cpf_bruto))
        else:
            raise ErroPainel("CPF inválido. Confira os números.", "invalido", "cpf")
        telefone = _texto_opcional(dados.get("telefone"), 30, "telefone", "Telefone inválido.")
        situacao = dados.get("situacao", "ativo")
        if situacao not in SITUACOES_MOTORISTA:
            raise ErroPainel("Escolha a situação: ativo, afastado ou desligado.", "invalido", "situacao")
        observacoes = _texto_opcional(dados.get("observacoes"), 500, "observacoes",
                                      "Observações podem ter até 500 letras.")
        termo = dados.get("termo") if dados.get("termo") is not None else {"assinado": False}
        if not isinstance(termo, dict):
            raise ErroPainel("Informe se o termo de ciência foi assinado.", "invalido", "termo")
        assinado = termo.get("assinado") is True
        if assinado and not data_valida(termo.get("data")):
            raise ErroPainel("Informe a data em que o termo foi assinado.", "invalido", "termo")
        novo_termo = {"assinado": assinado, "data": termo.get("data") if assinado else None,
                      "versao": str(termo.get("versao") or VERSAO_TERMO_PADRAO)[:20] if assinado else None}
        excluir = atual["id"] if atual is not None else -1
        if self.banco.um("SELECT 1 FROM motoristas WHERE matricula = ? AND id <> ?", (matricula, excluir)):
            raise ErroPainel("Já existe um motorista com esta matrícula.", "conflito", "matricula")
        if self.banco.um("SELECT 1 FROM motoristas WHERE cnh_numero = ? AND id <> ?", (cnh, excluir)):
            raise ErroPainel("Já existe um motorista com esta CNH.", "conflito", "cnh_numero")
        valores = {"nome": nome, "nome_curto": curto, "matricula": matricula, "cpf": cpf, "telefone": telefone,
                   "cnh_numero": cnh, "cnh_categoria": dados["cnh_categoria"], "cnh_validade": dados["cnh_validade"],
                   "situacao": situacao, "observacoes": observacoes}
        alvo = f"{curto} (matrícula {matricula})"
        with self.banco.transacao():
            if atual is None:
                motorista_id = self.banco.inserir("motoristas", {**valores, "ref": None})
                ref = f"m-{motorista_id:02d}"
                if self.banco.um("SELECT 1 FROM motoristas WHERE ref = ?", (ref,)):
                    ref = f"m-{novo_uid()[:8]}"
                self.banco.atualizar("motoristas", "id", motorista_id, {"ref": ref})
                self.atividades.registrar("cadastrou motorista", quem, alvo=alvo)
            else:
                motorista_id = atual["id"]
                mudou = [coluna for coluna, valor in valores.items() if valor != atual[coluna]]
                if mudou:
                    self.banco.atualizar("motoristas", "id", motorista_id, valores)
                    self.atividades.registrar("editou motorista", quem, alvo=alvo, detalhe="campos: " + ", ".join(mudou))
            if novo_termo != self.termo_atual(motorista_id) and (atual is not None or assinado):
                self.banco.inserir("termos", {"motorista_id": motorista_id, "assinado": int(assinado),
                                              "data": novo_termo["data"], "versao": novo_termo["versao"],
                                              "registrado_por": quem["nome"]})
                if assinado:
                    self.atividades.registrar("registrou termo de ciência", quem, alvo=alvo,
                                              detalhe=f"versão {novo_termo['versao']}, assinado em {novo_termo['data']}")
                else:
                    self.atividades.registrar("revogou termo de ciência", quem, alvo=alvo)
        return self._motorista(self.banco.um("SELECT * FROM motoristas WHERE id = ?", (motorista_id,)))

    def motorista_exportar(self, motorista_id, destino, quem: dict) -> dict:
        """LGPD, direito de acesso: cadastro, termos, viagens e momentos confirmados num arquivo JSON."""
        linha = self.banco.um("SELECT * FROM motoristas WHERE id = ?", (motorista_id,)) \
            if _inteiro(motorista_id) else None
        if linha is None:
            raise ErroPainel("Motorista não encontrado.", "nao_encontrado")
        conteudo = {"formato": "rotaguard-dados-motorista/1", "gerado_em": self.banco.agora(),
                    "motorista": self._motorista(linha, mascarar=False), "termos": self.termos_historico(linha["id"]),
                    "viagens": [], "momentos_confirmados": []}  # viagens ainda não ficam no banco do painel
        destino = Path(destino)
        destino.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")
        self.atividades.registrar("exportou dados do motorista", quem, alvo=linha["nome_curto"], detalhe=destino.name)
        return {"caminho": str(destino)}

    def video_liberado(self, motorista_ref) -> dict:
        """MOT-04: sem termo registrado, o vídeo do motorista fica trancado."""
        linha = self.banco.um("SELECT id FROM motoristas WHERE ref = ?", (motorista_ref,)) \
            if isinstance(motorista_ref, str) else None
        if linha is None:
            return {"liberado": False, "motivo": "Não sabemos quem dirigiu. Confirme o motorista antes de ver o vídeo."}
        if not self.termo_atual(linha["id"])["assinado"]:
            return {"liberado": False, "motivo": MENSAGEM_TERMO}
        return {"liberado": True}

    # Veículos ------------------------------------------------------------------------------------------------------
    def _veiculo(self, linha) -> dict:
        caixa = self.banco.um("SELECT id FROM caixas WHERE veiculo_id = ?", (linha["id"],))
        return {"id": linha["id"], "numero": linha["numero"], "placa": linha["placa"], "tipo": linha["tipo"],
                "transporta": linha["transporta"], "modelo": linha["modelo"], "ano": linha["ano"],
                "situacao": linha["situacao"], "caixa_id": caixa["id"] if caixa else None}

    def veiculos_listar(self) -> list[dict]:
        return [self._veiculo(l) for l in self.banco.todos("SELECT * FROM veiculos ORDER BY numero")]

    def veiculo_salvar(self, dados, quem: dict) -> dict:
        if not isinstance(dados, dict):
            raise ErroPainel("Preencha os dados do veículo.", "invalido", "numero")
        atual = None
        if dados.get("id") is not None:
            atual = self.banco.um("SELECT * FROM veiculos WHERE id = ?", (dados["id"],)) \
                if _inteiro(dados["id"]) else None
            if atual is None:
                raise ErroPainel("Veículo não encontrado.", "nao_encontrado")
        numero = dados.get("numero").strip() if isinstance(dados.get("numero"), str) else ""
        if not re.fullmatch(r"[A-Za-z0-9-]{1,10}", numero):
            raise ErroPainel("Informe o número do veículo (até 10 letras ou números).", "invalido", "numero")
        placa = placa_normalizada(dados.get("placa"))
        if placa is None:
            raise ErroPainel("Placa inválida. Use o formato ABC1D23 ou ABC-1234.", "invalido", "placa")
        if dados.get("tipo") not in TIPOS_VEICULO:
            raise ErroPainel("Escolha o tipo do veículo.", "invalido", "tipo")
        if dados.get("transporta") not in TRANSPORTA:
            raise ErroPainel("Diga se o veículo leva passageiros ou carga.", "invalido", "transporta")
        modelo = _texto_opcional(dados.get("modelo"), 80, "modelo", "Marca e modelo podem ter até 80 letras.")
        ano = dados.get("ano")
        if ano == "":
            ano = None
        if ano is not None and not (_inteiro(ano) and 1950 <= ano <= self.hoje().year + 1):
            raise ErroPainel("Ano inválido.", "invalido", "ano")
        situacao = dados.get("situacao", "em_uso")
        if situacao not in SITUACOES_VEICULO:
            raise ErroPainel("Escolha a situação do veículo.", "invalido", "situacao")
        excluir = atual["id"] if atual is not None else -1
        if self.banco.um("SELECT 1 FROM veiculos WHERE numero = ? AND id <> ?", (numero, excluir)):
            raise ErroPainel("Já existe um veículo com este número.", "conflito", "numero")
        valores = {"numero": numero, "placa": placa, "tipo": dados["tipo"], "transporta": dados["transporta"],
                   "modelo": modelo, "ano": ano, "situacao": situacao}
        with self.banco.transacao():
            if atual is None:
                veiculo_id = self.banco.inserir("veiculos", valores)
                self.atividades.registrar("cadastrou veículo", quem, alvo=f"Veículo {numero}")
            else:
                veiculo_id = atual["id"]
                mudou = [coluna for coluna, valor in valores.items() if valor != atual[coluna]]
                if mudou:
                    self.banco.atualizar("veiculos", "id", veiculo_id, valores)
                    self.atividades.registrar("editou veículo", quem, alvo=f"Veículo {numero}",
                                              detalhe="campos: " + ", ".join(mudou))
            if "caixa_id" in dados:
                instalada = self.banco.um("SELECT id FROM caixas WHERE veiculo_id = ?", (veiculo_id,))
                instalada_id = instalada["id"] if instalada else None
                if dados["caixa_id"] != instalada_id:
                    if instalada_id is not None:
                        self.caixa_vincular(instalada_id, None, quem)
                    if dados["caixa_id"] is not None:
                        self.caixa_vincular(dados["caixa_id"], veiculo_id, quem)
        return self._veiculo(self.banco.um("SELECT * FROM veiculos WHERE id = ?", (veiculo_id,)))

    # Caixas --------------------------------------------------------------------------------------------------------
    def _caixa(self, linha) -> dict:
        return {"id": linha["id"], "codigo": linha["codigo"], "veiculo_id": linha["veiculo_id"],
                "situacao": linha["situacao"], "detalhe": linha["detalhe"], "ultima_coleta": linha["ultima_coleta"],
                "versao": linha["versao"]}

    def caixas_listar(self) -> list[dict]:
        return [self._caixa(l) for l in self.banco.todos("SELECT * FROM caixas ORDER BY codigo")]

    def caixa_vincular(self, caixa_id, veiculo_id, quem: dict) -> dict:
        caixa = self.banco.um("SELECT * FROM caixas WHERE id = ?", (caixa_id,)) if _inteiro(caixa_id) else None
        if caixa is None:
            raise ErroPainel("Caixa não encontrada.", "nao_encontrado", "caixa_id")
        veiculo = None
        if veiculo_id is not None:
            veiculo = self.banco.um("SELECT * FROM veiculos WHERE id = ?", (veiculo_id,)) \
                if _inteiro(veiculo_id) else None
            if veiculo is None:
                raise ErroPainel("Veículo não encontrado.", "nao_encontrado", "veiculo_id")
            if caixa["situacao"] == "bloqueada":
                raise ErroPainel(f"{MENSAGEM_CAIXA_BLOQUEADA}: ela não pode ser instalada.", "conflito", "caixa_id")
            outra = self.banco.um("SELECT codigo FROM caixas WHERE veiculo_id = ? AND id <> ?",
                                  (veiculo_id, caixa["id"]))
            if outra:
                raise ErroPainel(f"O veículo {veiculo['numero']} já tem a caixa {outra['codigo']}. Retire essa caixa "
                                 "antes.", "conflito", "caixa_id")
        if caixa["veiculo_id"] == veiculo_id:
            return self._caixa(caixa)
        anterior = self.banco.um("SELECT numero FROM veiculos WHERE id = ?", (caixa["veiculo_id"],)) \
            if caixa["veiculo_id"] is not None else None
        agora = self.banco.agora()
        with self.banco.transacao():
            self.banco.executar("UPDATE caixa_vinculos SET ate = ?, alterado_em = ? WHERE caixa_id = ? AND ate IS NULL",
                                (agora, agora, caixa["id"]))
            self.banco.atualizar("caixas", "id", caixa["id"], {"veiculo_id": veiculo_id})
            if veiculo is not None:
                self.banco.inserir("caixa_vinculos", {"caixa_id": caixa["id"], "veiculo_id": veiculo["id"], "de": agora,
                                                      "ate": None, "por": quem["nome"]})
            if veiculo is None:
                acao, detalhe = "retirou caixa do veículo", f"Veículo {anterior['numero']}" if anterior else None
            elif anterior is None:
                acao, detalhe = "instalou caixa", f"Veículo {veiculo['numero']}"
            else:
                acao, detalhe = "trocou caixa de veículo", f"Veículo {anterior['numero']} → Veículo {veiculo['numero']}"
            self.atividades.registrar(acao, quem, alvo=caixa["codigo"], detalhe=detalhe)
        return self._caixa(self.banco.um("SELECT * FROM caixas WHERE id = ?", (caixa["id"],)))

    def veiculo_da_caixa_em(self, codigo: str, instante: str) -> int | None:
        """CXA-02: em qual veículo a caixa estava num instante (viagens antigas não mudam com a troca)."""
        linha = self.banco.um(
            "SELECT v.veiculo_id FROM caixa_vinculos v JOIN caixas c ON c.id = v.caixa_id WHERE c.codigo = ? "
            "AND v.de <= ? AND (v.ate IS NULL OR v.ate > ?) ORDER BY v.id DESC LIMIT 1", (codigo, instante, instante))
        return linha["veiculo_id"] if linha else None

    def caixa_pode_importar(self, codigo: str) -> bool:
        """CXA-03: caixa revogada pela RotaGuard não importa viagem."""
        linha = self.banco.um("SELECT situacao FROM caixas WHERE codigo = ?", (codigo,))
        return linha is not None and linha["situacao"] != "bloqueada"


# Decisões de momento -----------------------------------------------------------------------------------------------------
_MOMENTO = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")


class Decisoes:
    def __init__(self, banco: Banco, atividades: Atividades):
        self.banco, self.atividades = banco, atividades

    @staticmethod
    def _decisao(linha) -> dict:
        return {"momento_id": linha["momento_id"], "resultado": linha["resultado"], "orientado": bool(linha["orientado"]),
                "por": linha["por"], "funcao": linha["funcao"], "em": linha["em"]}

    @staticmethod
    def _validar_momento(momento_id) -> str:
        if not isinstance(momento_id, str) or not _MOMENTO.match(momento_id):
            raise ErroPainel("Momento inválido.", "invalido", "momento_id")
        return momento_id

    def _ativa(self, momento_id: str):
        return self.banco.um("SELECT * FROM decisoes WHERE momento_id = ? AND ativa = 1 ORDER BY id DESC LIMIT 1",
                             (momento_id,))

    def listar(self) -> list[dict]:
        return [self._decisao(l) for l in self.banco.todos("SELECT * FROM decisoes WHERE ativa = 1 ORDER BY id")]

    def _gravar(self, momento_id: str, resultado: str, orientado: bool, quem: dict) -> None:
        atual = self._ativa(momento_id)
        if atual is not None:
            self.banco.atualizar("decisoes", "id", atual["id"], {"ativa": 0})
        self.banco.inserir("decisoes", {"momento_id": momento_id, "resultado": resultado, "orientado": int(orientado),
                                        "por": quem["nome"], "funcao": quem["funcao"], "em": self.banco.agora(),
                                        "ativa": 1})

    def registrar(self, momento_id, resultado, quem: dict) -> dict:
        momento_id = self._validar_momento(momento_id)
        if resultado not in RESULTADOS:
            raise ErroPainel("Escolha confirmado ou alarme falso.", "invalido", "resultado")
        with self.banco.transacao():
            atual = self._ativa(momento_id)
            self._gravar(momento_id, resultado, bool(atual["orientado"]) if atual else False, quem)
            self.atividades.registrar("confirmou momento" if resultado == "confirmado" else "marcou alarme falso", quem,
                                      alvo=momento_id)
        return self._decisao(self._ativa(momento_id))

    def desfazer(self, momento_id, quem: dict) -> dict:
        momento_id = self._validar_momento(momento_id)
        with self.banco.transacao():
            atual = self._ativa(momento_id)
            if atual is None:
                raise ErroPainel("Este momento não tem decisão para desfazer.", "nao_encontrado")
            self.banco.atualizar("decisoes", "id", atual["id"], {"ativa": 0})
            self.atividades.registrar("desfez decisão", quem, alvo=momento_id, detalhe=atual["resultado"])
        return {}

    def orientado(self, momento_id, orientado, quem: dict) -> dict:
        momento_id = self._validar_momento(momento_id)
        if not isinstance(orientado, bool):
            raise ErroPainel("Valor inválido para orientação.", "invalido", "orientado")
        with self.banco.transacao():
            atual = self._ativa(momento_id)
            if atual is None:
                raise ErroPainel("Decida o momento antes de registrar a orientação.", "nao_encontrado")
            self._gravar(momento_id, atual["resultado"], orientado, quem)
            self.atividades.registrar("registrou orientação" if orientado else "tirou orientação", quem, alvo=momento_id)
        return self._decisao(self._ativa(momento_id))
