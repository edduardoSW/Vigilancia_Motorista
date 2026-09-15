"""Contas, sessão e permissões do painel (spec 014). Módulo puro: sem pywebview.

- Senha: mínimo 10 caracteres, lista local de senhas comuns, hash scrypt (N 2^17, r 8, p 1, sal 16 bytes) com os
  parâmetros gravados junto, conferida com hmac.compare_digest.
- 5 erros seguidos: espera de 30 s, dobrando a cada erro até 15 min. Usuário desativado: mesma resposta com senha
  certa ou errada.
- Sessão só na memória do processo; bloqueio por tempo sem uso; senha temporária com troca obrigatória.
- Código de recuperação mostrado uma vez, guardado só como hash, uso único.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import math
import re
import secrets
import threading
import time
from datetime import datetime

from atividades import Atividades
from dados import Banco, ErroPainel

CUSTO_PRODUCAO = (2**17, 8, 1)
TAMANHO_SAL = 16
MEMORIA_MAXIMA = 256 * 1024 * 1024
TAMANHO_MINIMO_SENHA = 10
TAMANHO_MAXIMO_SENHA = 200
ERROS_ANTES_DE_ESPERAR = 5
ESPERA_INICIAL_S = 30
ESPERA_MAXIMA_S = 15 * 60

FUNCOES = ("administrador", "supervisor", "consulta")
ACOES = ("ver_viagens", "ver_video", "importar", "decidir", "cadastrar", "equipe", "configuracoes", "atividades")
PERMISSOES = {
    "administrador": frozenset(ACOES),
    "supervisor": frozenset({"ver_viagens", "ver_video", "importar", "decidir", "cadastrar"}),
    "consulta": frozenset({"ver_viagens"}),
}

MENSAGEM_SENHA_CURTA = "A senha precisa ter pelo menos 10 caracteres."
MENSAGEM_SENHA_COMUM = "Esta senha é muito comum. Escolha outra."
MENSAGEM_CREDENCIAIS = "Usuário ou senha incorretos."
MENSAGEM_DESATIVADO = "Este acesso foi desativado. Fale com o administrador."
MENSAGEM_ARQUIVO_INVALIDO = "Este arquivo não é válido. Peça um novo à RotaGuard."
MENSAGEM_ULTIMO_ADMIN = ("Esta é a última pessoa administradora ativa. Dê a função de administrador a outra pessoa "
                         "antes.")

# Senhas com 10 caracteres ou mais que aparecem nas listas de vazamento (pt-BR e inglês). Conferidas sem maiúsculas.
SENHAS_COMUNS = frozenset("""
1234567890 0123456789 12345678910 123456789a 123456789012 1234554321 1122334455 1111111111 0000000000 9876543210
1q2w3e4r5t 1q2w3e4r5t6y qwertyuiop qwerty1234 qwerty12345 asdfghjkl1 zxcvbnm123 abcdefghij abc1234567 abcd123456
password12 password123 password1234 passw0rd12 iloveyou12 senha12345 senha123456 senhasenha minhasenha1 mudar12345
trocar1234 administrador admin12345 admin123456 brasil1234 brasil12345 flamengo123 corinthians palmeiras1 saopaulo123
rotaguard1 rotaguard12 rotaguard123 motorista1 motorista123 garagem123 onibus1234 caminhao123 viacao1234 empresa123
""".split())

_USUARIO_VALIDO = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")
_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_ALFABETO_TEMPORARIA = "abcdefghjkmnpqrstuvwxyz23456789"


def pode(funcao: str, acao: str) -> bool:
    return acao in PERMISSOES.get(funcao, frozenset())


# Senha -----------------------------------------------------------------------------------------------------------------
def hash_senha(senha: str, custo=CUSTO_PRODUCAO, sal: bytes | None = None) -> str:
    n, r, p = custo
    sal = sal if sal is not None else secrets.token_bytes(TAMANHO_SAL)
    chave = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=n, r=r, p=p, maxmem=MEMORIA_MAXIMA, dklen=32)
    return f"scrypt${n}${r}${p}${sal.hex()}${chave.hex()}"


def ler_hash(guardado: str) -> dict | None:
    try:
        nome, n, r, p, sal, chave = guardado.split("$")
        if nome != "scrypt":
            return None
        return {"n": int(n), "r": int(r), "p": int(p), "sal": bytes.fromhex(sal), "chave": bytes.fromhex(chave)}
    except (AttributeError, ValueError):
        return None


def conferir_senha(senha, guardado: str) -> bool:
    partes = ler_hash(guardado)
    if partes is None or not isinstance(senha, str) or partes["n"] > 2**20:
        return False
    calculada = hashlib.scrypt(senha.encode("utf-8"), salt=partes["sal"], n=partes["n"], r=partes["r"],
                               p=partes["p"], maxmem=MEMORIA_MAXIMA, dklen=len(partes["chave"]))
    return hmac.compare_digest(calculada, partes["chave"])


def validar_senha(senha, campo: str = "senha", usuario: str | None = None) -> str:
    if not isinstance(senha, str) or len(senha) < TAMANHO_MINIMO_SENHA:
        raise ErroPainel(MENSAGEM_SENHA_CURTA, "invalido", campo)
    if len(senha) > TAMANHO_MAXIMO_SENHA:
        raise ErroPainel("A senha pode ter no máximo 200 caracteres.", "invalido", campo)
    dobrada = senha.casefold()
    if dobrada in SENHAS_COMUNS or len(set(dobrada)) <= 2 or (usuario and usuario.casefold() in dobrada):
        raise ErroPainel(MENSAGEM_SENHA_COMUM, "invalido", campo)
    return senha


def espera_para(erros: int) -> int:
    if erros < ERROS_ANTES_DE_ESPERAR:
        return 0
    return min(ESPERA_INICIAL_S * 2 ** (erros - ERROS_ANTES_DE_ESPERAR), ESPERA_MAXIMA_S)


def gerar_codigo_recuperacao() -> str:
    letras = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(20))
    return "-".join(letras[i:i + 5] for i in range(0, 20, 5))


def normalizar_codigo(codigo) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(codigo or "").upper())


def gerar_senha_temporaria() -> str:
    letras = "".join(secrets.choice(_ALFABETO_TEMPORARIA) for _ in range(12))
    return "-".join(letras[i:i + 4] for i in range(0, 12, 4))


# Arquivo da empresa (spec 003, chaveiro de coleta) -----------------------------------------------------------------------
_ID_CAIXA = re.compile(r"^rg-[a-z2-7]{12}$")
_KID = re.compile(r"^[0-9a-f]{16}$")


def _data_iso(valor) -> bool:
    if not isinstance(valor, str):
        return False
    try:
        datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _base64(valor) -> bool:
    if not isinstance(valor, str) or not valor:
        return False
    try:
        return len(base64.b64decode(valor, validate=True)) > 0
    except (binascii.Error, ValueError):
        return False


def _inteiro(valor, minimo=1) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= minimo


def ler_chaveiro(conteudo) -> dict:
    """Confere a estrutura do `rotaguard-chaveiro-coleta/1`. O formato da spec 003 não traz assinatura da RotaGuard:
    aqui só dá para conferir formato e campos (arquivo alterado com estrutura válida passa)."""
    def invalido():
        return ErroPainel(MENSAGEM_ARQUIVO_INVALIDO, "invalido", "arquivo")

    if not isinstance(conteudo, str) or len(conteudo) > 5 * 1024 * 1024:
        raise invalido()
    try:
        dados = json.loads(conteudo)
    except ValueError:
        raise invalido() from None
    if not isinstance(dados, dict) or dados.get("formato") != "rotaguard-chaveiro-coleta/1":
        raise invalido()
    if not _inteiro(dados.get("empresa_id")) or not _data_iso(dados.get("gerado_em")):
        raise invalido()
    caixas = dados.get("caixas")
    if not isinstance(caixas, list) or not caixas:
        raise invalido()
    vistas, saida = set(), []
    for caixa in caixas:
        if not isinstance(caixa, dict):
            raise invalido()
        id_caixa, geracao = caixa.get("id_caixa"), caixa.get("geracao_atual")
        chaves, publicas = caixa.get("chaves_coleta"), caixa.get("chaves_publicas")
        if not isinstance(id_caixa, str) or not _ID_CAIXA.match(id_caixa) or id_caixa in vistas:
            raise invalido()
        if not _inteiro(caixa.get("dispositivo_id")) or not _inteiro(geracao):
            raise invalido()
        if not isinstance(caixa.get("nome"), str) or not isinstance(chaves, dict) or str(geracao) not in chaves:
            raise invalido()
        if not all(isinstance(k, str) and k.isdigit() and _base64(v) for k, v in chaves.items()):
            raise invalido()
        if not isinstance(publicas, list) or not publicas:
            raise invalido()
        for publica in publicas:
            if not (isinstance(publica, dict) and _inteiro(publica.get("geracao")) and isinstance(publica.get("kid"), str)
                    and _KID.match(publica["kid"]) and _base64(publica.get("publica"))):
                raise invalido()
        revogada = caixa.get("revogada_em")
        if revogada is not None and not _data_iso(revogada):
            raise invalido()
        vistas.add(id_caixa)
        saida.append({"codigo": id_caixa.upper(), "nome": caixa["nome"], "dispositivo_id": caixa["dispositivo_id"],
                      "geracao": geracao, "revogada_em": revogada})
    nome = dados.get("empresa_nome")
    nome = nome.strip() if isinstance(nome, str) and nome.strip() else f"Empresa {dados['empresa_id']}"
    return {"empresa_id": dados["empresa_id"], "empresa_nome": nome[:120], "caixas": saida}


# Contas -----------------------------------------------------------------------------------------------------------------
def usuario_publico(linha) -> dict:
    return {"id": linha["id"], "nome": linha["nome"], "usuario": linha["usuario"], "funcao": linha["funcao"],
            "ativo": bool(linha["ativo"]), "ultimo_acesso": linha["ultimo_acesso"],
            "trocar_senha": bool(linha["trocar_senha"])}


def validar_nome(nome, campo="nome") -> str:
    nome = " ".join(str(nome or "").split()) if isinstance(nome, str) else ""
    if len(nome) < 2 or len(nome) > 120:
        raise ErroPainel("Informe o nome da pessoa.", "invalido", campo)
    return nome


def validar_usuario(usuario, campo="usuario") -> str:
    usuario = usuario.strip().lower() if isinstance(usuario, str) else ""
    if not _USUARIO_VALIDO.match(usuario):
        raise ErroPainel("Use de 3 a 40 letras sem acento, números, ponto ou traço (ex.: marina.lopes).", "invalido",
                         campo)
    return usuario


class Contas:
    def __init__(self, banco: Banco, atividades: Atividades, relogio=time.time, custo=CUSTO_PRODUCAO,
                 bloqueio_min=lambda: 15):
        self.banco, self.atividades, self.relogio, self.custo = banco, atividades, relogio, custo
        self.bloqueio_min = bloqueio_min
        self._sessao: dict | None = None
        self._erros: dict[str, dict] = {}
        self._trava = threading.RLock()
        self._hash_falso = hash_senha(secrets.token_hex(16), custo)  # mesmo custo para usuário que não existe

    # Ativação ------------------------------------------------------------------------------------------------------
    def ativado(self) -> bool:
        return self.banco.meta_ler("ativado") == "1"

    def validar_admin(self, admin) -> dict:
        if not isinstance(admin, dict):
            raise ErroPainel("Preencha nome, usuário e senha.", "invalido", "nome")
        nome, usuario = validar_nome(admin.get("nome")), validar_usuario(admin.get("usuario"))
        return {"nome": nome, "usuario": usuario, "senha": validar_senha(admin.get("senha"), "senha", usuario)}

    def criar_admin_inicial(self, admin: dict) -> tuple[dict, str]:
        """Dentro da transação da ativação. Devolve o usuário e o código de recuperação (mostrado uma vez só)."""
        dados = self.validar_admin(admin)
        codigo = gerar_codigo_recuperacao()
        novo_id = self.banco.inserir("usuarios", {"nome": dados["nome"], "usuario": dados["usuario"],
                                                  "funcao": "administrador", "ativo": 1, "trocar_senha": 0,
                                                  "senha_hash": hash_senha(dados["senha"], self.custo)})
        self.banco.meta_gravar("recuperacao_hash", hash_senha(normalizar_codigo(codigo), self.custo))
        return self._linha(novo_id), codigo

    # Sessão --------------------------------------------------------------------------------------------------------
    def _linha(self, usuario_id):
        return self.banco.um("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))

    def _conferir_espera(self, chave: str) -> None:
        registro = self._erros.get(chave)
        if registro and registro["ate"] > self.relogio():
            segundos = math.ceil(registro["ate"] - self.relogio())
            raise ErroPainel(f"Espere {segundos} segundos para tentar de novo.", "espera", esperar_s=segundos)

    def _contar_erro(self, chave: str, linha, acao: str) -> ErroPainel:
        registro = self._erros.get(chave, {"n": 0, "ate": 0.0})
        registro = {"n": registro["n"] + 1, "ate": 0.0}
        espera = espera_para(registro["n"])
        if espera:
            registro["ate"] = self.relogio() + espera
        self._erros[chave] = registro
        # Usuário que não existe fica sem "em quê": o texto digitado pode ser a própria senha, no campo errado (ENT-03).
        self.atividades.registrar(acao, dict(linha) if linha else None, alvo=linha["usuario"] if linha else None,
                                  detalhe=("" if linha else "usuário não cadastrado, ") + f"{registro['n']}º erro seguido"
                                  + (f", espera de {espera} s" if espera else ""))
        if espera:
            return ErroPainel(f"Senha errada. Espere {espera} segundos para tentar de novo.", "espera", "senha", espera)
        return ErroPainel(MENSAGEM_CREDENCIAIS, "invalido", "senha")

    def abrir_sessao(self, usuario_id: int) -> dict:
        agora = self.relogio()
        self.banco.atualizar("usuarios", "id", usuario_id, {"ultimo_acesso": self.banco.agora()})
        self._sessao = {"id": usuario_id, "ultimo_uso": agora, "bloqueado": False}
        return usuario_publico(self._linha(usuario_id))

    def entrar(self, usuario, senha) -> dict:
        with self._trava:
            chave = usuario.strip().casefold()[:80] if isinstance(usuario, str) else ""
            self._conferir_espera(chave)
            linha = self.banco.um("SELECT * FROM usuarios WHERE usuario = ?", (chave,)) if chave else None
            certa = conferir_senha(senha, linha["senha_hash"] if linha else self._hash_falso)
            if linha is not None and not linha["ativo"]:
                self.atividades.registrar("tentou entrar com acesso desativado", dict(linha), alvo=linha["usuario"])
                raise ErroPainel(MENSAGEM_DESATIVADO, "sem_permissao")
            if linha is None or not certa:
                raise self._contar_erro(chave, linha, "errou a senha")
            self._erros.pop(chave, None)
            usuario_dict = self.abrir_sessao(linha["id"])
            self.atividades.registrar("entrou", usuario_dict)
            return usuario_dict

    def _conferir_tempo(self) -> None:
        sessao = self._sessao
        if sessao and not sessao["bloqueado"] and self.relogio() - sessao["ultimo_uso"] >= self.bloqueio_min() * 60:
            sessao["bloqueado"] = True
            linha = self._linha(sessao["id"])
            self.atividades.registrar("bloqueou por tempo sem uso", dict(linha) if linha else None)

    def estado_sessao(self) -> tuple[dict | None, bool]:
        with self._trava:
            if not self._sessao:
                return None, False
            self._conferir_tempo()
            linha = self._linha(self._sessao["id"])
            if linha is None or not linha["ativo"]:
                self._sessao = None
                return None, False
            return usuario_publico(linha), self._sessao["bloqueado"]

    def exigir(self, acao: str | None = None, permitir_bloqueado=False, permitir_troca=False) -> dict:
        with self._trava:
            usuario, bloqueado = self.estado_sessao()
            if usuario is None:
                raise ErroPainel("Entre de novo para continuar.", "sem_sessao")
            if bloqueado and not permitir_bloqueado:
                raise ErroPainel("A tela está bloqueada. Digite sua senha para continuar.", "bloqueado")
            if usuario["trocar_senha"] and not permitir_troca:
                raise ErroPainel("Troque a senha temporária antes de continuar.", "sem_permissao", "nova")
            if acao is not None and not pode(usuario["funcao"], acao):
                self.atividades.registrar("tentou sem permissão", usuario, alvo=acao)
                raise ErroPainel("Sua função não permite fazer isso.", "sem_permissao")
            return usuario

    def tocar(self) -> dict:
        with self._trava:
            self.exigir(permitir_bloqueado=True, permitir_troca=True)
            if not self._sessao["bloqueado"]:
                self._sessao["ultimo_uso"] = self.relogio()
            return {"bloqueado": self._sessao["bloqueado"]}

    def bloquear(self) -> dict:
        with self._trava:
            usuario = self.exigir(permitir_bloqueado=True, permitir_troca=True)
            if not self._sessao["bloqueado"]:
                self._sessao["bloqueado"] = True
                self.atividades.registrar("bloqueou a tela", usuario)
            return {}

    def desbloquear(self, senha) -> dict:
        with self._trava:
            usuario = self.exigir(permitir_bloqueado=True, permitir_troca=True)
            chave = usuario["usuario"]
            self._conferir_espera(chave)
            linha = self._linha(usuario["id"])
            if not conferir_senha(senha, linha["senha_hash"]):
                raise self._contar_erro(chave, linha, "errou a senha ao desbloquear")
            self._erros.pop(chave, None)
            self._sessao.update(bloqueado=False, ultimo_uso=self.relogio())
            self.atividades.registrar("desbloqueou a tela", usuario)
            return usuario

    def sair(self) -> dict:
        with self._trava:
            if self._sessao:
                linha = self._linha(self._sessao["id"])
                self.atividades.registrar("saiu", dict(linha) if linha else None)
            self._sessao = None
            return {}

    def trocar_senha(self, atual, nova) -> dict:
        with self._trava:
            usuario = self.exigir(permitir_troca=True)
            chave = usuario["usuario"]
            self._conferir_espera(chave)
            linha = self._linha(usuario["id"])
            if not conferir_senha(atual, linha["senha_hash"]):
                erro = self._contar_erro(chave, linha, "errou a senha ao trocar")
                erro.campo = "atual"
                raise erro
            validar_senha(nova, "nova", chave)
            if nova == atual:
                raise ErroPainel("A senha nova precisa ser diferente da atual.", "invalido", "nova")
            self._erros.pop(chave, None)
            self.banco.atualizar("usuarios", "id", usuario["id"], {"senha_hash": hash_senha(nova, self.custo),
                                                                   "trocar_senha": 0})
            self.atividades.registrar("trocou a senha", usuario)
            return {}

    def recuperar_acesso(self, usuario, codigo, nova_senha) -> dict:
        with self._trava:
            chave = usuario.strip().casefold()[:80] if isinstance(usuario, str) else ""
            self._conferir_espera(chave)
            validar_senha(nova_senha, "nova_senha", chave)
            linha = self.banco.um("SELECT * FROM usuarios WHERE usuario = ?", (chave,)) if chave else None
            guardado = self.banco.meta_ler("recuperacao_hash") or ""
            certo = conferir_senha(normalizar_codigo(codigo), guardado or self._hash_falso)
            if not (linha and linha["ativo"] and linha["funcao"] == "administrador" and guardado and certo):
                erro = self._contar_erro(chave, linha, "errou o código de recuperação")
                if erro.codigo == "invalido":
                    erro.erro, erro.campo = "Usuário ou código de recuperação incorretos.", "codigo"
                raise erro
            with self.banco.transacao():
                self.banco.atualizar("usuarios", "id", linha["id"],
                                     {"senha_hash": hash_senha(nova_senha, self.custo), "trocar_senha": 0})
                self.banco.meta_gravar("recuperacao_hash", "")
                self.banco.meta_gravar("recuperacao_usada_em", self.banco.agora())
                self.atividades.registrar("usou o código de recuperação", dict(linha))
            self._erros.pop(chave, None)
            return {}

    # Equipe --------------------------------------------------------------------------------------------------------
    def equipe_listar(self) -> list[dict]:
        return [usuario_publico(l) for l in self.banco.todos("SELECT * FROM usuarios ORDER BY nome COLLATE NOCASE")]

    def equipe_adicionar(self, dados, quem: dict) -> dict:
        if not isinstance(dados, dict):
            raise ErroPainel("Preencha nome, usuário e função.", "invalido", "nome")
        nome, usuario = validar_nome(dados.get("nome")), validar_usuario(dados.get("usuario"))
        funcao = dados.get("funcao")
        if funcao not in FUNCOES:
            raise ErroPainel("Escolha a função: administrador, supervisor ou consulta.", "invalido", "funcao")
        if self.banco.um("SELECT 1 FROM usuarios WHERE usuario = ?", (usuario,)):
            raise ErroPainel("Já existe alguém com este usuário.", "conflito", "usuario")
        temporaria = gerar_senha_temporaria()
        with self.banco.transacao():
            novo_id = self.banco.inserir("usuarios", {"nome": nome, "usuario": usuario, "funcao": funcao, "ativo": 1,
                                                      "trocar_senha": 1,
                                                      "senha_hash": hash_senha(temporaria, self.custo)})
            self.atividades.registrar("adicionou pessoa à equipe", quem, alvo=usuario, detalhe=f"função {funcao}")
        return {"usuario": usuario_publico(self._linha(novo_id)), "senha_temporaria": temporaria}

    def _admins_ativos(self) -> int:
        return self.banco.um("SELECT COUNT(*) AS n FROM usuarios WHERE funcao = 'administrador' AND ativo = 1")["n"]

    def equipe_alterar(self, usuario_id, mudancas, quem: dict) -> dict:
        linha = self._linha(usuario_id) if _inteiro(usuario_id) else None
        if linha is None:
            raise ErroPainel("Pessoa não encontrada.", "nao_encontrado")
        if not isinstance(mudancas, dict) or not set(mudancas) <= {"funcao", "ativo"}:
            raise ErroPainel("Só dá para mudar a função ou se o acesso está ativo.", "invalido")
        funcao = mudancas.get("funcao", linha["funcao"])
        ativo = mudancas.get("ativo", bool(linha["ativo"]))
        if funcao not in FUNCOES:
            raise ErroPainel("Escolha a função: administrador, supervisor ou consulta.", "invalido", "funcao")
        if not isinstance(ativo, bool):
            raise ErroPainel("Valor inválido para ativo.", "invalido", "ativo")
        era_admin_ativo = linha["funcao"] == "administrador" and linha["ativo"]
        if era_admin_ativo and (funcao != "administrador" or not ativo) and self._admins_ativos() <= 1:
            raise ErroPainel(MENSAGEM_ULTIMO_ADMIN, "conflito", "funcao" if funcao != "administrador" else "ativo")
        with self.banco.transacao():
            self.banco.atualizar("usuarios", "id", linha["id"], {"funcao": funcao, "ativo": int(ativo)})
            if funcao != linha["funcao"]:
                self.atividades.registrar("mudou a função", quem, alvo=linha["usuario"],
                                          detalhe=f"{linha['funcao']} → {funcao}")
            if ativo != bool(linha["ativo"]):
                self.atividades.registrar("desativou acesso" if not ativo else "reativou acesso", quem,
                                          alvo=linha["usuario"])
        return usuario_publico(self._linha(linha["id"]))

    def equipe_nova_senha(self, usuario_id, quem: dict) -> dict:
        linha = self._linha(usuario_id) if _inteiro(usuario_id) else None
        if linha is None:
            raise ErroPainel("Pessoa não encontrada.", "nao_encontrado")
        temporaria = gerar_senha_temporaria()
        with self.banco.transacao():
            self.banco.atualizar("usuarios", "id", linha["id"], {"senha_hash": hash_senha(temporaria, self.custo),
                                                                 "trocar_senha": 1})
            self.atividades.registrar("criou senha temporária", quem, alvo=linha["usuario"])
        self._erros.pop(linha["usuario"], None)
        return {"senha_temporaria": temporaria}
